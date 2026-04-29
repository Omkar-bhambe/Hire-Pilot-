import openai
from config import Config
import io
import base64
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class OpenAITTSClient:
    def __init__(self):
        if not Config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured in Config")
        self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)

    def synthesize_speech(self, text: str, voice: str = "alloy", model: str = "tts-1") -> bytes:
        """
        Generate speech audio using OpenAI TTS API.
        
        Args:
            text: Text to synthesize
            voice: OpenAI voice ('alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer')
            model: 'tts-1' or 'tts-1-hd'
        
        Returns:
            MP3 audio bytes
        """
        try:
            logger.info(f"Generating TTS for voice={voice}, model={model}, text_len={len(text)}")
            
            response = self.client.audio.speech.create(
                model=model,
                voice=voice,
                input=text
            )
            
            # response.content is bytes (MP3)
            audio_bytes = response.content
            logger.info(f"TTS generated successfully: {len(audio_bytes)} bytes")
            return audio_bytes
            
        except Exception as e:
            logger.error(f"TTS synthesis failed: {str(e)}")
            raise

    def get_audio_base64(self, text: str, voice: str = "alloy") -> str:
        """Return audio as base64 for easy frontend embedding."""
        audio_bytes = self.synthesize_speech(text, voice)
        return base64.b64encode(audio_bytes).decode('utf-8')

# Singleton instance
tts_client = OpenAITTSClient()
