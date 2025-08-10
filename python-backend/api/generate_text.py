from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from google import genai
import os
import base64
from google.genai import types
import io
import wave

import logging
from typing import List, Dict, Optional, Any
#from api.chat_history import add_message_to_history
from database import get_db_connection
from supabase import Client
from fastapi import Depends
from utils.model_utils import process_content_with_tools, load_system_prompt, client as genai_client
from google.genai import types as genai_types # Import types for history reconstruction
from api.chat_history import insert_message

router = APIRouter()
logger = logging.getLogger(__name__)

class TextRequest(BaseModel):
    text: str
    history: List[Dict[str, Any]] # History is now more complex
    chat_id: Optional[str] = None
    enable_tts: bool = False

class TextResponse(BaseModel):
    text: str
    audio_base64: str

@router.post("/api/generateText", response_model=TextResponse)
async def generate_text(request: TextRequest, db: Client = Depends(get_db_connection)):
    """
    Generate text and TTS audio using Gemini models, with conversation history
    and tool-calling capabilities.
    """
    try:
        # 1. Build conversation history from the client request
        conversation_history = []

        # Reconstruct history from the rich JSON format
        for message in request.history:
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

        # 2. Add the new user message to the history
        conversation_history.append(
            genai_types.Content(role="user", parts=[genai_types.Part.from_text(request.text)])
        )
        # Insert user message to Supabase
        if request.chat_id:
            insert_message(request.chat_id, "user", request.text, db)

        # 3. Generate the response and get the updated history
        logger.debug(f"Text chat history sent to model: {conversation_history}")
        # 3. Load persona and generate the response
        aria_prompt = load_system_prompt("aria")
        text_response, updated_history = process_content_with_tools(conversation_history, system_prompt=aria_prompt)
        logger.info(f"AI Response for Text: '{text_response}'")
        # Insert AI message to Supabase
        if request.chat_id and text_response:
            insert_message(request.chat_id, "model", text_response, db)

        # 4. Generate TTS audio for the final response (non-critical)
        audio_base64 = ""
        if request.enable_tts:
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
        
        return TextResponse(text=text_response, audio_base64=audio_base64)
        
    except Exception as e:
        import traceback
        logger.error(f"Error in generateText: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
