from transformers import VitsModel, AutoTokenizer
import torch
import io
import base64
import scipy.io.wavfile
import logging

logger = logging.getLogger(__name__)

class TTSService:
    """
    A service for converting text to speech using Facebook's MMS model for Indonesian.
    """
    def __init__(self, model_id="facebook/mms-tts-ind"):
        """
        Initializes the TTS service by loading the VITS model and tokenizer.
        """
        logger.info(f"Loading TTS model '{model_id}'...")
        try:
            self.model = VitsModel.from_pretrained(model_id)
            self.tokenizer = AutoTokenizer.from_pretrained(model_id)
            self.model.to("cpu") # Ensure model is on CPU
            logger.info("TTS model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load TTS model: {e}", exc_info=True)
            raise

    def text_to_audio_base64(self, text: str) -> str:
        """
        Converts a text phrase to a base64 encoded WAV audio string.
        """
        if not text:
            return ""
            
        try:
            logger.info(f"Generating audio for text: '{text}'")
            inputs = self.tokenizer(text, return_tensors="pt").to("cpu")
            
            with torch.no_grad():
                output = self.model(**inputs).waveform

            # The output is a float tensor. We need to convert it to a 16-bit PCM WAV file.
            # Squeeze to remove the batch dimension.
            waveform = output.cpu().numpy().squeeze()

            # Normalize to 16-bit range if it's in [-1, 1]
            if waveform.max() <= 1.0 and waveform.min() >= -1.0:
                 waveform = (waveform * 32767).astype("int16")

            buf = io.BytesIO()
            scipy.io.wavfile.write(buf, rate=self.model.config.sampling_rate, data=waveform)
            
            buf.seek(0)
            audio_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            logger.info(f"Audio generated successfully for text: '{text}'")
            return audio_base64
        except Exception as e:
            logger.error(f"Error during TTS generation for text '{text}': {e}", exc_info=True)
            return ""