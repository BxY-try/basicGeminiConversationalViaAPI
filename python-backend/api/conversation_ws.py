# python-backend/api/conversation_ws.py

import base64
import asyncio
import re
import requests
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google.genai import types as genai_types
from TTS.utils.synthesizer import Synthesizer
import numpy as np
import io
import os
import wave
from g2p_id import G2P
from utils.model_utils import client as genai_client, load_system_prompt
from piper import PiperVoice
import soundfile as sf


# --- TTS Engine Configurations ---
VOICEVOX_BASE_URL = "http://127.0.0.1:50021"
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(script_dir, '..'))

# --- Piper TTS Initialization for English ---
PIPER_MODEL_EN_ONNX = os.path.join(backend_dir, "datasetsANDmodels/piper-en/en_US-lessac-high.onnx")
PIPER_MODEL_EN_JSON = os.path.join(backend_dir, "datasetsANDmodels/piper-en/en_US-lessac-high.onnx.json")
piper_voice_en = None

# --- Detailed Debugging for Piper Model Loading ---
print("\n--- Piper TTS Debug Information ---")
abs_model_path = os.path.abspath(PIPER_MODEL_EN_ONNX)
abs_config_path = os.path.abspath(PIPER_MODEL_EN_JSON)
print(f"Attempting to load model from: {abs_model_path}")
print(f"Attempting to load config from: {abs_config_path}")

model_exists = os.path.exists(abs_model_path)
config_exists = os.path.exists(abs_config_path)
print(f"Model file exists? {'YES' if model_exists else 'NO'}")
print(f"Config file exists? {'YES' if config_exists else 'NO'}")

if model_exists and config_exists:
    print("Both files found. Proceeding to load...")
    try:
        # According to the documentation (API_PYTHON.md), the correct method is PiperVoice.load()
        piper_voice_en = PiperVoice.load(abs_model_path, config_path=abs_config_path)
        print("Piper TTS model for English loaded successfully.")
    except Exception as e:
        print(f"CRITICAL ERROR during Piper model loading: {e}")
else:
    print("One or both Piper files are missing. English TTS will not work.")
print("--- End of Piper TTS Debug ---\n")


# --- G2P and Coqui TTS Initialization for Indonesian ---
print("Initializing G2P for Indonesian...")
g2p = G2P()
print("G2P Initialized.")

MODEL_DIR_ID = os.path.join(backend_dir, "datasetsANDmodels/indonesian-tts")

# --- Restore Global Coqui TTS Initialization with chdir ---
print("Loading Coqui TTS model for Indonesian...")
synthesizer_id = None
if os.path.exists(MODEL_DIR_ID):
    original_cwd = os.getcwd()
    try:
        # Temporarily change to the model directory for robust initialization
        os.chdir(MODEL_DIR_ID)
        print(f"Temporarily changed CWD to: {os.getcwd()} for Coqui TTS loading")
        
        synthesizer_id = Synthesizer(
            tts_checkpoint="checkpoint_1260000-inference.pth",
            tts_config_path="config.json",
            # The 'speakers_file_path' argument is removed as it's not supported by the user's TTS lib version
            use_cuda=False,
        )
        print("Coqui TTS model for Indonesian loaded successfully.")
    except Exception as e:
        print(f"Failed to load Coqui TTS model: {e}")
    finally:
        # Always change back to the original directory
        os.chdir(original_cwd)
        print(f"Restored CWD to: {os.getcwd()}")
else:
    print(f"Indonesian model directory not found at {MODEL_DIR_ID}. Indonesian TTS will not work.")


def clean_ruby_tags(text: str) -> str:
    """Removes <ruby> tags and their furigana annotations."""
    # Remove <ruby> and </ruby> tags
    text = re.sub(r'</?ruby>', '', text)
    # Remove furigana annotations like （にほんご）
    text = re.sub(r'（[^）]+）', '', text)
    return text

def sanitize_text_for_tts(text: str) -> str:
    text = text.lower()
    allowed_chars = "abcdefghijklmnopqrstuvwxyz0123456789 .,?!"
    return ''.join(filter(lambda char: char in allowed_chars, text))

def clean_asterisks(text: str) -> str:
    """Removes asterisks from the text."""
    return text.replace('*', '')

def text_to_audio_coqui(text: str) -> str:
    """Uses the globally initialized Coqui TTS model for Indonesian text-to-speech."""
    if not synthesizer_id:
        print("Indonesian synthesizer not initialized, skipping TTS.")
        return ""
    
    sanitized_text = sanitize_text_for_tts(text)
    if not sanitized_text.strip():
        return ""

    try:
        phonemes = g2p(sanitized_text)
        print(f"Coqui TTS (ID) - Sanitized: '{sanitized_text}' -> Phonemes: '{phonemes}'")
        
        # Use the global synthesizer instance
        wav = synthesizer_id.tts(phonemes, speaker_name="wibowo", language="id")
        
        if wav is None:
            raise RuntimeError("Coqui TTS synthesis failed to produce audio.")

        buffer = io.BytesIO()
        wav_norm = np.int16(np.array(wav) * 32767)
        
        with wave.open(buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(synthesizer_id.tts_config.audio['sample_rate'])
            wf.writeframes(wav_norm.tobytes())
            
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"CRITICAL ERROR in Coqui TTS for text '{text}': {e}")
        # Return a silent audio chunk to prevent the frontend from getting stuck
        return "UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABgAAABkYXRhAAAAA"

def text_to_audio_voicevox(text: str, speaker_id: int = 47) -> str:
    """Uses VOICEVOX engine for Japanese text-to-speech."""
    try:
        # Step 1: Get audio query
        query_params = {"text": text, "speaker": speaker_id}
        response_query = requests.post(f"{VOICEVOX_BASE_URL}/audio_query", params=query_params)
        response_query.raise_for_status()
        audio_query = response_query.json()
        
        # Step 2: Synthesize audio
        synth_params = {"speaker": speaker_id}
        response_synth = requests.post(f"{VOICEVOX_BASE_URL}/synthesis", params=synth_params, json=audio_query)
        response_synth.raise_for_status()
        
        audio_data = response_synth.content
        print(f"VOICEVOX TTS (JA) - Generated audio for text: '{text}'.")
        return base64.b64encode(audio_data).decode('utf-8')
    except requests.exceptions.RequestException as e:
        print(f"CRITICAL ERROR communicating with VOICEVOX engine: {e}")
        return ""
    except Exception as e:
        print(f"CRITICAL ERROR in VOICEVOX TTS for text '{text}': {e}")
        return ""

def text_to_audio_piper(text: str) -> str:
    """Uses Piper TTS for English text-to-speech using the correct WAV synthesis method."""
    if not piper_voice_en:
        print("Piper (EN) synthesizer not initialized, skipping TTS.")
        return ""
    try:
        print(f"Piper TTS (EN) - Synthesizing to WAV: '{text}'")
        
        wav_buffer = io.BytesIO()
        # The synthesize_wav method requires a wave file object, not a raw BytesIO object.
        # We need to wrap the BytesIO buffer with wave.open().
        with wave.open(wav_buffer, 'wb') as wav_file:
            piper_voice_en.synthesize_wav(text, wav_file)
        
        wav_buffer.seek(0)
        audio_data = wav_buffer.getvalue()
        
        print(f"Piper TTS (EN) - Successfully synthesized WAV, {len(audio_data)} bytes.")
        return base64.b64encode(audio_data).decode('utf-8')
        
    except Exception as e:
        print(f"CRITICAL ERROR in Piper TTS for text '{text}': {e}")
        import traceback
        traceback.print_exc()
        return ""

# --- WebSocket Endpoint ---
router = APIRouter()

@router.websocket("/ws/conversation")
async def conversation_ws(websocket: WebSocket):
    await websocket.accept() 
    
    aria_prompt = load_system_prompt("aria")
    chat_history = []

    try:
        while True:
            data = await websocket.receive_json()
            if data.get('type') == 'user_transcript':
                user_text = data['text']
                user_lang = data.get('lang', 'id')
                if not user_text.strip():
                    continue

                chat_history.append(genai_types.Content(role="user", parts=[genai_types.Part.from_text(user_text)]))

                # Dynamically create model_config with language instruction for each turn
                lang_map = {'id': 'Indonesian', 'en': 'English', 'ja': 'Japanese'}
                lang_name = lang_map.get(user_lang, 'Indonesian')
                
                # Add a clear, forceful instruction in the persona's primary language.
                lang_instruction = f"\n\nSANGAT PENTING: Pengguna berbicara dalam Bahasa {lang_name}. Balas HANYA dalam Bahasa {lang_name}."
                
                # Combine with the base prompt
                dynamic_prompt = aria_prompt + lang_instruction
                
                model_config = genai_types.GenerateContentConfig(system_instruction=dynamic_prompt)

                llm_stream = genai_client.models.generate_content_stream(
                    model="gemini-2.5-flash",
                    contents=chat_history,
                    config=model_config
                )
                
                text_buffer = ""
                full_response_text = ""
                detected_lang = user_lang
                sentence_end_pattern = re.compile(r'(?<=[.?!,。？！、])\s*')
                
                for chunk in llm_stream:
                    if chunk.text:
                        text_buffer += chunk.text
                        full_response_text += chunk.text
                        
                        # Process sentences as they are formed
                        sentences = sentence_end_pattern.split(text_buffer)
                        
                        # The last part might be an incomplete sentence, so we keep it in the buffer
                        text_buffer = sentences[-1]
                        sentences_to_process = sentences[:-1]
                        
                        for sentence in sentences_to_process:
                            if sentence:
                                
                                text_for_tts = clean_asterisks(clean_ruby_tags(sentence))
                                audio_b64 = None
                                
                                if detected_lang == 'ja':
                                    audio_b64 = text_to_audio_voicevox(text_for_tts)
                                elif detected_lang == 'id':
                                    audio_b64 = text_to_audio_coqui(text_for_tts)
                                elif detected_lang == 'en':
                                    audio_b64 = text_to_audio_piper(text_for_tts)
                                
                                if audio_b64:
                                    await websocket.send_json({
                                        "type": "ai_audio_chunk",
                                        "audio_base64": audio_b64,
                                        "transcript": text_for_tts
                                    })

                # After the loop, process any remaining text in the buffer
                remaining_text = text_buffer.strip()
                if remaining_text:
                    # Use the last detected language, or default to 'id'

                    text_for_tts = clean_asterisks(clean_ruby_tags(remaining_text))
                    audio_b64 = None
                    
                    if detected_lang == 'ja':
                        audio_b64 = text_to_audio_voicevox(text_for_tts)
                    elif detected_lang == 'id':
                        audio_b64 = text_to_audio_coqui(text_for_tts)
                    elif detected_lang == 'en':
                        audio_b64 = text_to_audio_piper(text_for_tts)

                    if audio_b64:
                        await websocket.send_json({
                            "type": "ai_audio_chunk",
                            "audio_base64": audio_b64,
                            "transcript": text_for_tts
                        })
                
                await websocket.send_json({"type": "ai_turn_end"})

                if full_response_text.strip():
                    chat_history.append(genai_types.Content(role="model", parts=[genai_types.Part.from_text(full_response_text)]))

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"An error occurred in conversation_ws: {e}")
        import traceback
        traceback.print_exc()
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception as send_e:
            print(f"Failed to send error to client: {send_e}")
