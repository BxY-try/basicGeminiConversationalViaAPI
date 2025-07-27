import tempfile
import os
from pydub import AudioSegment

def convert_to_wav(input_path: str, output_path: str) -> None:
    """
    Convert an audio file to WAV format with 16kHz sample rate, mono channel, and 32-bit float format.
    
    Args:
        input_path (str): Path to the input audio file
        output_path (str): Path where the output WAV file will be saved
    """
    # Load the audio file
    audio = AudioSegment.from_file(input_path)
    
    # Convert to mono and set frame rate to 16kHz
    audio = audio.set_channels(1)
    audio = audio.set_frame_rate(16000)
    
    # Set sample width to 32-bit float (4 bytes)
    audio = audio.set_sample_width(4)
    
    # Export as WAV with floating point format (PCM 32-bit)
    audio.export(output_path, format="wav", parameters=["-f", "32"])

def save_base64_audio(base64_data: str, output_path: str) -> None:
    """
    Save base64 encoded audio data to a file.
    
    Args:
        base64_data (str): Base64 encoded audio data
        output_path (str): Path where the audio file will be saved
    """
    import base64
    
    # Decode base64 data
    audio_bytes = base64.b64decode(base64_data)
    
    # Write to file
    with open(output_path, "wb") as f:
        f.write(audio_bytes)
