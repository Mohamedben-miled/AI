"""
ElevenLabs Text-to-Speech Service
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

class TTSService:
    def __init__(self):
        self.api_key = os.getenv('ELEVENLABS_API_KEY')
        self.voice_id = os.getenv('ELEVENLABS_VOICE_ID', 'aEO01A4wXwd1O8GPgGlF')  # Arabella voice
        
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY not found in environment variables")
        
        self.api_url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
    
    def synthesize(self, text):
        """
        Convert text to speech using ElevenLabs TTS
        
        Args:
            text: str - Text to convert to speech
            
        Returns:
            bytes: Audio file bytes (MP3)
        """
        try:
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_turbo_v2_5",  # Faster model optimized for low latency
                "voice_settings": {
                    "stability": 0.4,  # Lower stability for faster generation
                    "similarity_boost": 0.4,  # Lower similarity for faster generation
                    "style": 0.0,  # Neutral style for speed
                    "use_speaker_boost": False  # Disable speaker boost for speed
                },
                "optimize_streaming_latency": 3  # Optimize for low latency (0-4, 3 is balanced)
            }
            
            response = requests.post(
                self.api_url,
                json=data,
                headers=headers,
                timeout=15  # Reduced timeout since faster model should respond quicker
            )
            
            if response.status_code == 200:
                return response.content
            else:
                print(f"TTS API Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"TTS Error: {str(e)}")
            return None

