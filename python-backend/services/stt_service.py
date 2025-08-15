from faster_whisper import WhisperModel
import logging
import io

logger = logging.getLogger(__name__)

class STTService:
    """
    A service for transcribing audio using the faster-whisper model.
    """
    def __init__(self, model_size="small", device="cpu", compute_type="int8"):
        """
        Initializes the STT service by loading the Whisper model.
        """
        logger.info(f"Loading Whisper model '{model_size}' on device '{device}' with compute type '{compute_type}'...")
        try:
            self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
            logger.info("Whisper model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}", exc_info=True)
            raise

    def transcribe_turn(self, audio_bytes: bytes) -> str:
        """
        Transcribes a single turn of speech from audio bytes.
        Uses VAD to detect the end of speech.
        """
        try:
            # The model expects a file-like object. Since the frontend now sends a complete
            # audio file blob, we can pass the bytes directly to BytesIO.
            audio_file = io.BytesIO(audio_bytes)
            
            segments, _ = self.model.transcribe(
                audio_file,
                beam_size=5,
                initial_prompt="Halo, Bayu, Jakarta, Jawa Barat, tolong, jawab, aku, ya.",
                vad_filter=False # Disabled as frontend controls audio chunking
            )
            
            # Concatenate segments to form the full transcript
            transcript = "".join(s.text for s in segments).strip()
            if transcript:
                logger.info(f"Transcription result: '{transcript}'")
            else:
                logger.info("Transcription result is empty.")
            return transcript
        except Exception as e:
            logger.error(f"Error during transcription: {e}", exc_info=True)
            return ""