from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from google.genai import types
import base64
import io
import wave
import logging
from utils.model_utils import client as genai_client

router = APIRouter()
logger = logging.getLogger(__name__)

class TTSRequest(BaseModel):
    text: str

class TTSResponse(BaseModel):
    audio_base64: str

@router.post("/api/text-to-speech", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest):
    """
    Generate TTS audio from text.
    """
    try:
        audio_base64 = ""
        if request.text:
            tts_config = types.GenerateContentConfig(
                response_modalities=["audio"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Leda")
                    )
                )
            )
            
            tts_result = genai_client.models.generate_content(
                model="gemini-2.5-flash-preview-tts",
                contents=request.text,
                config=tts_config
            )
            
            if tts_result.candidates and tts_result.candidates[0].content.parts and tts_result.candidates[0].content.parts[0].inline_data:
                pcm_data = tts_result.candidates[0].content.parts[0].inline_data.data
                wav_buffer = io.BytesIO()
                with wave.open(wav_buffer, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(24000)
                    wf.writeframes(pcm_data)
                audio_base64 = base64.b64encode(wav_buffer.getvalue()).decode('utf-8')
            else:
                logger.warning("TTS generation succeeded but returned no audio data.")
        
        if not audio_base64:
            raise HTTPException(status_code=500, detail="Failed to generate audio.")

        return TTSResponse(audio_base64=audio_base64)
        
    except Exception as e:
        import traceback
        logger.error(f"Error in text_to_speech: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")