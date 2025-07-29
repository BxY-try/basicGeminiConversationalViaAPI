from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from google import genai
import os
import base64
from google.genai import types
import io
import wave

router = APIRouter()

from typing import List, Dict

from .chat_history import save_message_to_history
from typing import Optional

class TextRequest(BaseModel):
    text: str
    history: List[Dict[str, str]]
    chat_id: Optional[str] = None

class TextResponse(BaseModel):
    text: str
    audio_base64: str

@router.post("/api/generateText", response_model=TextResponse)
async def generate_text(request: TextRequest):
    """
    Generate text and TTS audio using Gemini models, with conversation history.
    """
    try:
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

        # Build the conversation history
        conversation_history = []
        for message in request.history:
            role = message.get("role")
            content = message.get("content")
            if role and content:
                gemini_role = "model" if role == "ai" else "user"
                conversation_history.append(
                    types.Content(role=gemini_role, parts=[types.Part.from_text(content)])
                )

        # Add the new user message
        conversation_history.append(
            types.Content(role="user", parts=[types.Part.from_text(request.text)])
        )
        
        # Generate text response
        text_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=conversation_history
        ).text

        # Save messages to history if chat_id is provided
        if request.chat_id:
            save_message_to_history(request.chat_id, {"role": "user", "content": request.text})
            save_message_to_history(request.chat_id, {"role": "ai", "content": text_response})
        
        # Generate TTS audio
        tts_config = types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Leda"  # Example voice, change as needed
                    )
                )
            )
        )
        
        tts_result = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=text_response,
            config=tts_config
        )
        
        # Convert PCM to WAV container
        pcm_data = tts_result.candidates[0].content.parts[0].inline_data.data
        sample_rate = 24000  # Standard TTS sample rate
        
        # Create WAV in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(1)      # Mono
            wf.setsampwidth(2)      # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_data)
        
        # Encode complete WAV file as base64
        audio_data = base64.b64encode(wav_buffer.getvalue()).decode('utf-8')
        
        return TextResponse(text=text_response, audio_base64=audio_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
