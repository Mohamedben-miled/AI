"""
Speech-to-Text Service using OpenAI Whisper API
"""
import os
from openai import OpenAI
from dotenv import load_dotenv
import tempfile

load_dotenv()

class STTService:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = OpenAI(api_key=self.api_key)
    
    def transcribe(self, audio_file):
        """
        Convert audio to text using OpenAI Whisper API
        
        Args:
            audio_file: File object from Flask request
            
        Returns:
            str: Transcribed text
        """
        try:
            # Read audio file content
            audio_content = audio_file.read()
            
            # Save to temporary file (Whisper API needs a file)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as tmp_file:
                tmp_file.write(audio_content)
                tmp_path = tmp_file.name
            
            try:
                # Open the file for transcription
                with open(tmp_path, 'rb') as audio:
                    # Use Whisper API
                    transcript = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio,
                        language="en"  # Optional: specify language
                    )
                    
                    text = transcript.text
                    print(f"[STT] Transcribed: {text}")
                    return text
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                
        except Exception as e:
            print(f"STT Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

