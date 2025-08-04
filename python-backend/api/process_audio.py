from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from google import genai
from google.genai import types
import os
import tempfile
import base64
import io
import wave
import json
import logging
from typing import List, Dict, Optional, Any
from pydantic import BaseModel

from .chat_history import save_history # Use the new save_history function
from utils.model_utils import process_content_with_tools, client as genai_client
from google.genai import types as genai_types # Import types for history reconstruction

router = APIRouter()
logger = logging.getLogger(__name__)

class ImageResponse(BaseModel):
    text: str
    audio_base64: str

@router.post("/api/processImage", response_model=ImageResponse)
async def process_image(
    prompt: str = Form(...),
    image: UploadFile = File(...),
    history: str = Form('[]'),
    chat_id: Optional[str] = Form(None)
):
    """
    Process an image with a text prompt and conversation history, with tool-calling.
    """
    try:
        image_bytes = await image.read()
        
        # Build the conversation history from the client request
        conversation_history = []

        # Reconstruct history from the rich JSON format
        for message in json.loads(history):
            role = message.get("role")
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

        # Add the new user message (with image) to the history
        conversation_history.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(prompt),
                    types.Part(inline_data=types.Blob(mime_type=image.content_type, data=image_bytes))
                ]
            )
        )
        
        # Generate the response and get the updated history
        logger.debug(f"Image chat history sent to model: {conversation_history}")
        text_response, updated_history = process_content_with_tools(conversation_history)
        logger.info(f"AI Response for Image: '{text_response}'")


        # Save the complete, updated history to the file
        if chat_id:
            save_history(chat_id, updated_history)
        
        # Generate TTS audio for the final response (non-critical)
        audio_base64 = ""
        try:
            if text_response:
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
                    contents=text_response,
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
        
        return ImageResponse(text=text_response, audio_base64=audio_base64)
        
    except Exception as e:
        import traceback
        logger.error(f"Error processing image: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")
