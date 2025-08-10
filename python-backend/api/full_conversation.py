from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from supabase import Client
from database import get_db_connection
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

from .chat_history import insert_message
from utils.model_utils import process_content_with_tools, client as genai_client
from google.genai import types as genai_types # Import types for history reconstruction

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
    chat_id: Optional[str] = Form(None),
    db: Client = Depends(get_db_connection)
):
    """
    Refactored audio-to-audio pipeline with proper history management and tool-calling.
    """
    temp_input_path = None
    temp_wav_path = None
    audio_file_obj = None
    
    try:
        # Save and convert audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio.filename)[1]) as tmp_file:
            tmp_file.write(await audio.read())
            temp_input_path = tmp_file.name
        
        temp_wav_path = temp_input_path + ".wav"
        convert_to_wav(temp_input_path, temp_wav_path)
        
        # 1. Transcribe Audio to Text (STT)
        audio_file_obj = genai_client.files.upload(path=temp_wav_path)
        stt_result = genai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                "Transcribe this audio.",
                types.Part(file_data=types.FileData(mime_type=audio_file_obj.mime_type, file_uri=audio_file_obj.uri))
            ]
        )
        user_transcript = stt_result.text.strip()
        logger.info(f"User transcript: '{user_transcript}'")

        if not user_transcript:
            raise HTTPException(status_code=400, detail="Audio could not be transcribed or is empty.")

        # 2. Build conversation history
        conversation_history = []

        # Reconstruct history from the rich JSON format
        for message in json.loads(history):
            # CRITICAL FIX: Map 'assistant' role to 'model' for the API
            role = message.get("role")
            if role == "assistant":
                role = "model"

            parts = []
            for part_data in message.get("parts", []):
                if 'text' in part_data:
                    parts.append(genai_types.Part.from_text(part_data['text']))
                elif 'function_call' in part_data:
                    fc = part_data['function_call']
                    parts.append(genai_types.Part.from_function_call(name=fc['name'], args=fc['args']))
                elif 'function_response' in part_data:
                    fr = part_data['function_response']
                    parts.append(genai_types.Part.from_function_response(name=fr['name'], response=fr['response']))
            if parts:
                conversation_history.append(genai_types.Content(role=role, parts=parts))

        # Add the new user transcript to the history
        conversation_history.append(
            genai_types.Content(role="user", parts=[genai_types.Part.from_text(user_transcript)])
        )
        # Insert user message to Supabase
        if chat_id:
            insert_message(chat_id, "user", user_transcript, db)

        # 3. Generate AI response and get the updated history
        # Log the exact history being sent to the model for debugging
        logger.debug(f"Full conversation history sent to model: {conversation_history}")
        ai_response_text, updated_history = process_content_with_tools(conversation_history)
        logger.info(f"AI response: '{ai_response_text}'")
        # Insert AI message to Supabase
        if chat_id and ai_response_text:
            insert_message(chat_id, "model", ai_response_text, db)

        # 4. Generate TTS for the final AI response (non-critical)
        audio_base64 = "" # Default to empty string
        try:
            if ai_response_text: # Only generate TTS if there is text
                tts_config = types.GenerateContentConfig(
                    response_modalities=["audio"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr")
                        )
                    )
                )
                
                tts_result = genai_client.models.generate_content(
                    model="gemini-2.5-flash-preview-tts",
                    contents=ai_response_text,
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
        except Exception as tts_error:
            logger.error(f"TTS generation failed, but proceeding without audio. Error: {tts_error}")

        # 6. Return the structured response
        return JSONResponse(content={
            "user_transcript": user_transcript,
            "ai_response": ai_response_text,
            "audio_base64": audio_base64
        })
        
    except Exception as e:
        import traceback
        logger.error(f"Pipeline error details:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error in pipeline: {str(e)}")
    
    finally:
        # Cleanup
        if audio_file_obj:
            logger.info(f"Deleting uploaded file: {audio_file_obj.name}")
            genai_client.files.delete(name=audio_file_obj.name)
        if temp_input_path and os.path.exists(temp_input_path):
            os.unlink(temp_input_path)
        if temp_wav_path and os.path.exists(temp_wav_path):
            os.unlink(temp_wav_path)
