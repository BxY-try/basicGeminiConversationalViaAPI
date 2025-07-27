from fastapi import APIRouter, HTTPException, UploadFile, File, Response
from google import genai
from google.genai import types
import os
import tempfile
import base64
from utils.audio_utils import convert_to_wav
import io
import wave
import logging

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/api/full-conversation")
async def full_conversation(audio: UploadFile = File(...)):
    """
    Complete audio-to-audio pipeline:
    1. Convert audio to WAV format
    2. Use Gemini 2.5 Flash for audio processing (STT and as the "brain")
    3. Use gemini-2.5-flash-preview-tts to convert response text to audio
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
        
        # TAHAP 2: AUDIO -> TEXT RESPONSE (GEMINI 2.5 FLASH)
        # Upload the audio file to Gemini API
        audio_file = client.files.upload(path=temp_wav_path)

        audio_processing_prompt = "Anda adalah asisten AI yang ramah. Tanggapi pertanyaan atau pernyataan dalam audio ini secara langsung dalam bahasa Indonesia."

        # FINAL CORRECTION: Explicitly create a Part from the audio file's URI and MIME type
        result = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_text(audio_processing_prompt),
                        types.Part(
                            file_data=types.FileData(
                                # Get the mime_type and uri from the uploaded file object
                                mime_type=audio_file.mime_type,
                                file_uri=audio_file.uri
                            )
                        )
                    ]
                )
            ]
        )        
        transcribed_response = result.text
        
        # Log the actual transcribed text for debugging
        logger.debug(f"STT Result: '{transcribed_response}'")
        
        if not transcribed_response:
            logger.error("Empty response from STT model")
            raise Exception("Model tidak menghasilkan konten atau respons tidak valid.")
        
        # TAHAP 3: TEXT -> AUDIO (Using Google's TTS capabilities)
        # Configure TTS with proper audio format
        generate_content_config = types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Zephyr"
                    )
                )
            )
        )
        
        # Generate TTS response - CORRECTED FORMAT (direct string content)
        logger.debug(f"Generating TTS for text: '{transcribed_response}'")
        tts_response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=transcribed_response,  # DIRECT STRING CONTENT (FIXED)
            config=generate_content_config
        )
        
        # Extract audio data from response
        if (tts_response.candidates and 
            tts_response.candidates[0].content.parts and 
            tts_response.candidates[0].content.parts[0].inline_data):
            
            pcm_data = tts_response.candidates[0].content.parts[0].inline_data.data
            sample_rate = 24000  # Standard TTS sample rate
            
            # Create WAV container in memory
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wf:
                wf.setnchannels(1)      # Mono
                wf.setsampwidth(2)      # 16-bit
                wf.setframerate(sample_rate)
                wf.writeframes(pcm_data)
            
            # Log successful audio generation
            logger.info(f"Successfully generated {len(pcm_data)} byte audio response")
            
            # Return the complete WAV file
            return Response(
                content=wav_buffer.getvalue(),
                media_type="audio/wav"
            )
        
        logger.error("TTS generation failed - no audio data in response")
        raise Exception("TTS generation failed or returned no audio data.")
        
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
