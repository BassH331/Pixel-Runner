import os
import asyncio
import edge_tts

class TTSManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TTSManager, cls).__new__(cls)
            # Default configuration
            cls._instance.voice = 'en-US-ChristopherNeural' # Male voice
            cls._instance.rate = '+0%'
            cls._instance.pitch = '+0Hz'
            cls._instance.volume = '+0%'
        return cls._instance
    
    def configure(self, voice='en-GB-RyanNeural', rate='+20%', pitch='+0Hz', volume='+0%'):
        """
        Configure the Text-to-Speech settings using Edge TTS.

        Args:
            voice (str): The voice to use. Examples:
                         - 'en-US-ChristopherNeural' (Male, US)
                         - 'en-US-AriaNeural' (Female, US)
                         - 'en-GB-RyanNeural' (Male, UK)
                         - 'en-GB-SoniaNeural' (Female, UK)
            rate (str): Speaking rate adjustment. Examples: '+10%', '-20%'. Default '+0%'.
            pitch (str): Pitch adjustment. Examples: '+5Hz', '-2Hz'. Default '+0Hz'.
            volume (str): Volume adjustment. Examples: '+10%', '-10%'. Default '+0%'.
        """
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self.volume = volume
        
    def generate_audio(self, text, output_path):
        """
        Generate audio from text using Edge TTS and save to a file.

        Args:
            text (str): The text to be converted to speech.
            output_path (str): The file path where the generated audio (MP3) will be saved.

        Returns:
            bool: True if generation was successful or file already exists, False otherwise.
        """
        if os.path.exists(output_path):
            return True
            
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            async def _gen():
                communicate = edge_tts.Communicate(
                    text, 
                    self.voice, 
                    rate=self.rate, 
                    pitch=self.pitch, 
                    volume=self.volume
                )
                await communicate.save(output_path)

            asyncio.run(_gen())
            
            print(f"[TTS] Generated audio for: {output_path} (voice={self.voice}, rate={self.rate}, pitch={self.pitch})")
            return True
        except Exception as e:
            print(f"[TTS] Error generating audio: {e}")
            return False
