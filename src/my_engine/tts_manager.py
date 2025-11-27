import os
from gtts import gTTS

class TTSManager:
    _instance = None
    
    @classmethod
    def generate_audio(cls, text, output_path, lang='en'):
        """
        Generate audio from text using gTTS and save to output_path.
        If the file already exists, it skips generation.
        """
        if os.path.exists(output_path):
            return True
            
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            tts = gTTS(text=text, lang=lang)
            tts.save(output_path)
            print(f"[TTS] Generated audio for: {output_path}")
            return True
        except Exception as e:
            print(f"[TTS] Error generating audio: {e}")
            return False
