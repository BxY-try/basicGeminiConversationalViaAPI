from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from google import genai
from google.genai import types
import os
import tempfile
import base64
import io
import wave

router = APIRouter()

@router.post("/api/processAudio")
async def process_image_and_text(
    prompt: str = Form(...),
    image: UploadFile = File(...)
):
    """
    Process an image with a text prompt using the Gemini model and return text with audio response.
    """
    try:
        # Initialize Google Generative AI client
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        
        # Read image bytes directly
        image_bytes = await image.read()
        
        # Create multimodal prompt with both text and image
        model_input = types.Content(
            parts=[
                # Text part
                types.Part.from_text(prompt),
                # Image part (inline data)
                types.Part(
                    inline_data=types.Blob(
                        mime_type=image.content_type,  # e.g., 'image/jpeg'
                        data=image_bytes
                    )
                )
            ]
        )
        
        # Generate content using the correct API method
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[model_input]
        )
        
        # Get the generated text
        text_response = response.text
        
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
