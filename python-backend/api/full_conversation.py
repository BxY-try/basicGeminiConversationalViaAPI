from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from google import genai
from google.genai import types
import os
import tempfile
import base64
from utils.audio_utils import convert_to_wav
import io
import wave
import logging
import json
from typing import Optional, List, Dict
from pydantic import BaseModel

from .chat_history import save_message_to_history

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

router = APIRouter()

class ConversationResponse(BaseModel):
    user_transcript: str
    ai_response: str
    audio_base64: str

@router.post("/api/full-conversation", response_model=ConversationResponse)
async def full_conversation(
    audio: UploadFile = File(...),
    history: str = Form('[]'), # Default to an empty JSON array string
    chat_id: Optional[str] = Form(None)
):
    """
    Refactored audio-to-audio pipeline with proper history management:
    1. Transcribe audio to text (STT).
    2. Save user's transcribed text to history.
    3. Generate AI text response based on the full, updated history.
    4. Save AI's response to history.
    5. Convert AI's text response to audio (TTS).
    6. Return user transcript, AI response, and AI audio.
    """
    temp_input_path = None
    temp_wav_path = None
    
    try:
        # Save the uploaded audio to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio.filename)[1]) as tmp_file:
            tmp_file.write(await audio.read())
            temp_input_path = tmp_file.name
        
        # Convert audio to WAV format
        temp_wav_path = temp_input_path + ".wav"
        convert_to_wav(temp_input_path, temp_wav_path)
        
        # Initialize Google Generative AI client
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        
        # === TAHAP 1: Transkripsi Audio (STT) ===
        audio_file = client.files.upload(path=temp_wav_path)
        stt_prompt = "Transcribe this audio."
        stt_result = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[stt_prompt, types.Part(file_data=types.FileData(mime_type=audio_file.mime_type, file_uri=audio_file.uri))]
        )
        user_transcript = stt_result.text.strip()
        logger.info(f"User transcript: '{user_transcript}'")

        if not user_transcript:
            raise HTTPException(status_code=400, detail="Audio could not be transcribed or is empty.")

        # === TAHAP 2: Simpan Transkripsi Pengguna ke Riwayat ===
        if chat_id:
            save_message_to_history(chat_id, {"role": "user", "content": user_transcript})

        # === TAHAP 3: Hasilkan Respons AI berdasarkan Riwayat Lengkap ===
        # Muat riwayat yang sudah diperbarui
        try:
            # Re-parse history after saving the user's transcript
            current_history: List[Dict[str, str]] = json.loads(history)
            current_history.append({"role": "user", "content": user_transcript})
        except json.JSONDecodeError:
            logger.error("Failed to parse conversation history JSON for AI response")
            current_history = [{"role": "user", "content": user_transcript}]

        conversation_contents = []
        for message in current_history:
            role = message.get("role")
            content = message.get("content")
            if role and content:
                gemini_role = "model" if role == "ai" else "user"
                conversation_contents.append(
                    types.Content(role=gemini_role, parts=[types.Part.from_text(content)])
                )
        
        ai_response_result = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=conversation_contents
        )
        ai_response_text = ai_response_result.text
        logger.info(f"AI response: '{ai_response_text}'")

        # === TAHAP 4: Simpan Respons AI ke Riwayat ===
        if chat_id:
            save_message_to_history(chat_id, {"role": "ai", "content": ai_response_text})

        # === TAHAP 5: Konversi Respons AI ke Audio (TTS) ===
        tts_config = types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr")
                )
            )
        )
        
        tts_result = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=ai_response_text,
            config=tts_config
        )
        
        if not (tts_result.candidates and tts_result.candidates[0].content.parts and tts_result.candidates[0].content.parts[0].inline_data):
            raise Exception("TTS generation failed or returned no audio data.")

        pcm_data = tts_result.candidates[0].content.parts[0].inline_data.data
        sample_rate = 24000

        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_data)
        
        audio_base64 = base64.b64encode(wav_buffer.getvalue()).decode('utf-8')

        # === TAHAP 6: Kembalikan Respons Terstruktur ===
        return JSONResponse(content={
            "user_transcript": user_transcript,
            "ai_response": ai_response_text,
            "audio_base64": audio_base64
        })
        
    except Exception as e:
        # Enhanced error logging with full traceback
        import traceback
        logger.error(f"Pipeline error details:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error in pipeline: {str(e)}")
    
    finally:
        # TAHAP PEMBERSIHAN
        # Hapus file yang diupload dari server
        if 'audio_file' in locals():
            logger.info(f"Deleting uploaded file: {audio_file.name}")
            client.files.delete(name=audio_file.name)
        # Hapus file temp dari server
        if temp_input_path and os.path.exists(temp_input_path):
            os.unlink(temp_input_path)
        if temp_wav_path and os.path.exists(temp_wav_path):
            os.unlink(temp_wav_path)
        # Hapus file temp dari server
        if temp_input_path and os.path.exists(temp_input_path):
            os.unlink(temp_input_path)
        if temp_wav_path and os.path.exists(temp_wav_path):
            os.unlink(temp_wav_path)
