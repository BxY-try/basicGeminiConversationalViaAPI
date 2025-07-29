from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from google import genai
from google.genai import types
import os
import tempfile
import base64
import io
import wave
import json
from typing import List, Dict, Optional
from .chat_history import save_message_to_history

router = APIRouter()

@router.post("/api/processAudio")
async def process_image_and_text(
    prompt: str = Form(...),
    image: UploadFile = File(...),
    history: str = Form('[]'),
    chat_id: Optional[str] = Form(None)
):
    """
    Process an image with a text prompt and conversation history using the Gemini model
    and return text with audio response.
    """
    try:
        # Initialize Google Generative AI client
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        
        # Read image bytes directly
        image_bytes = await image.read()
        
        # Build conversation history
        try:
            parsed_history: List[Dict[str, str]] = json.loads(history)
        except json.JSONDecodeError:
            parsed_history = []

        conversation_contents = []
        for message in parsed_history:
            role = message.get("role")
            content = message.get("content")
            if role and content:
                gemini_role = "model" if role == "ai" else "user"
                conversation_contents.append(
                    types.Content(role=gemini_role, parts=[types.Part.from_text(content)])
                )

        # Add the new user message with image
        conversation_contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(prompt),
                    types.Part(
                        inline_data=types.Blob(
                            mime_type=image.content_type,
                            data=image_bytes
                        )
                    )
                ]
            )
        )
        
        # Generate content using the correct API method
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=conversation_contents
        )
        
        # Get the generated text
        text_response = response.text

        # Save messages to history if chat_id is provided
        if chat_id:
            save_message_to_history(chat_id, {"role": "user", "content": prompt})
            save_message_to_history(chat_id, {"role": "ai", "content": text_response})
        
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
        
        # Return the generated text and audio
        return {"text": text_response, "audio_base64": audio_data}
        
    except Exception as e:
        # Log the full error for debugging
        import traceback
        print(f"Error processing image: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")
