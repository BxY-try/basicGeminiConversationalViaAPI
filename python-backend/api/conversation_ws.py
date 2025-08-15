# python-backend/api/conversation_ws.py

import base64
import asyncio
import re
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google.genai import types as genai_types
from transformers import VitsModel, AutoTokenizer
import torch
import scipy.io.wavfile
import io

from utils.model_utils import client as genai_client, load_system_prompt

# Inisialisasi di luar agar tidak loading model setiap ada koneksi baru
print("Memuat model TTS datasetsANDmodels/indonesian-tts...")
tts_model = VitsModel.from_pretrained("datasetsANDmodels/indonesian-tts")
tts_tokenizer = AutoTokenizer.from_pretrained("datasetsANDmodels/indonesian-tts")
print("Model TTS berhasil dimuat.")

def text_to_audio_base64(text: str) -> str:
    """Menggunakan model VITS yang sudah di-load untuk mengubah teks menjadi audio base64."""
    # Proteksi: Pastikan teks tidak kosong dan mengandung setidaknya satu huruf.
    if not text or not text.strip() or not any(c.isalpha() for c in text):
        print(f"Skipping TTS for non-prose text: '{text}'")
        return ""

    try:
        inputs = tts_tokenizer(text, return_tensors="pt")
        # Proteksi: Cek jika hasil tokenisasi kosong, yang bisa menyebabkan error di model
        if inputs.input_ids.shape[1] == 0:
            print(f"Skipping TTS for text that tokenized to empty: '{text}'")
            return ""
            
        inputs['input_ids'] = inputs['input_ids'].to(torch.long)
        
        with torch.no_grad():
            output = tts_model(**inputs).waveform
        
        speech = output.squeeze().cpu().numpy()
        buffer = io.BytesIO()
        # Pastikan rate adalah integer
        rate = int(tts_model.config.sampling_rate)
        scipy.io.wavfile.write(buffer, rate=rate, data=speech)
        
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"Error in text_to_audio_base64 for text '{text}': {e}")
        return ""


# --- WebSocket Endpoint ---
router = APIRouter()

@router.websocket("/ws/conversation")
async def conversation_ws(websocket: WebSocket):
    await websocket.accept()
    
    aria_prompt = load_system_prompt("aria")
    chat_history = []

    model_config = genai_types.GenerateContentConfig(system_instruction=aria_prompt) if aria_prompt else None

    try:
        while True:
            data = await websocket.receive_json()
            if data.get('type') == 'user_transcript':
                user_text = data['text']
                
                if not user_text.strip():
                    continue

                chat_history.append(genai_types.Content(role="user", parts=[genai_types.Part.from_text(user_text)]))

                llm_stream = genai_client.models.generate_content_stream(
                    model="gemini-2.5-flash", # Menggunakan model yang lebih baru jika tersedia
                    contents=chat_history,
                    config=model_config
                )
                
                sentence_buffer = ""
                full_response_text = ""
                # Pola untuk menemukan kalimat atau baris yang berakhir dengan tanda baca atau newline
                sentence_end_pattern = re.compile(r'([^.!?\n]+[.!?\n]*)')

                # Iterasi stream secara sinkron
                for chunk in llm_stream:
                    if chunk.text:
                        sentence_buffer += chunk.text
                        full_response_text += chunk.text
                        
                        processed_until = 0
                        # Cari semua kalimat/baris yang sudah lengkap di dalam buffer
                        for match in sentence_end_pattern.finditer(sentence_buffer):
                            sentence = match.group(0).strip()
                            if sentence:
                                audio_b64 = text_to_audio_base64(sentence)
                                if audio_b64:
                                    await websocket.send_json({
                                        "type": "ai_audio_chunk",
                                        "audio_base64": audio_b64
                                    })
                                    await asyncio.sleep(0.01) # Memberi jeda singkat
                            processed_until = match.end(0)
                        
                        # Sisakan bagian yang belum diproses di buffer
                        sentence_buffer = sentence_buffer[processed_until:]
                
                # Proses sisa teks di buffer setelah stream selesai
                remaining_text = sentence_buffer.strip()
                if remaining_text:
                    audio_b64 = text_to_audio_base64(remaining_text)
                    if audio_b64:
                        await websocket.send_json({
                            "type": "ai_audio_chunk",
                            "audio_base64": audio_b64
                        })
                
                # Kirim sinyal bahwa giliran AI telah selesai
                await websocket.send_json({"type": "ai_turn_end"})

                # Tambahkan respons AI lengkap ke history
                if full_response_text.strip():
                    chat_history.append(genai_types.Content(role="model", parts=[genai_types.Part.from_text(full_response_text)]))

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"An error occurred in conversation_ws: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception as send_e:
            print(f"Failed to send error to client: {send_e}")