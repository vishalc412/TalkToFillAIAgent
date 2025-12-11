"""
Speech processing: Speech-to-Text (STT) and Text-to-Speech (TTS).
"""

from abc import ABC, abstractmethod
from typing import Optional
import logging
import io
import base64

from openai import OpenAI
from gtts import gTTS

from src.config import Settings

logger = logging.getLogger(__name__)


# ==================== Speech-to-Text ====================


class STTProvider(ABC):
    """Abstract base class for Speech-to-Text providers."""

    @abstractmethod
    async def transcribe(self, audio_data: bytes, language: str = "en-US") -> str:
        """
        Transcribe audio to text.

        Args:
            audio_data: Audio file bytes
            language: Language code

        Returns:
            Transcribed text
        """
        pass


class OpenAISTTProvider(STTProvider):
    """OpenAI Whisper STT provider."""

    def __init__(self, settings: Settings):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.settings = settings

    async def transcribe(self, audio_data: bytes, language: str = "en-US") -> str:
        """Transcribe using OpenAI Whisper API."""
        try:
            # Convert language code (en-US -> en)
            language_code = language.split("-")[0] if "-" in language else language

            # Create a file-like object
            audio_file = io.BytesIO(audio_data)
            audio_file.name = "audio.wav"  # Whisper needs a filename

            transcription = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language_code,
            )

            return transcription.text

        except Exception as e:
            logger.error(f"OpenAI STT error: {e}")
            raise


class GoogleSTTProvider(STTProvider):
    """Google Cloud Speech-to-Text provider."""

    def __init__(self, settings: Settings):
        try:
            from google.cloud import speech
            self.client = speech.SpeechClient()
            self.settings = settings
        except ImportError:
            raise ImportError(
                "google-cloud-speech is required for Google STT. "
                "Install it with: pip install google-cloud-speech"
            )

    async def transcribe(self, audio_data: bytes, language: str = "en-US") -> str:
        """Transcribe using Google Cloud Speech-to-Text."""
        try:
            from google.cloud import speech

            audio = speech.RecognitionAudio(content=audio_data)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                language_code=language,
                enable_automatic_punctuation=True,
            )

            response = self.client.recognize(config=config, audio=audio)

            # Get the first result
            if response.results:
                return response.results[0].alternatives[0].transcript

            return ""

        except Exception as e:
            logger.error(f"Google STT error: {e}")
            raise


class WhisperLocalSTTProvider(STTProvider):
    """Local Whisper model STT provider."""

    def __init__(self, settings: Settings):
        try:
            import whisper
            self.model = whisper.load_model("base")
            self.settings = settings
        except ImportError:
            raise ImportError(
                "openai-whisper is required for local Whisper. "
                "Install it with: pip install openai-whisper"
            )

    async def transcribe(self, audio_data: bytes, language: str = "en-US") -> str:
        """Transcribe using local Whisper model."""
        try:
            import whisper
            import tempfile

            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_data)
                temp_path = f.name

            # Transcribe
            result = self.model.transcribe(temp_path, language=language.split("-")[0])

            return result["text"]

        except Exception as e:
            logger.error(f"Local Whisper STT error: {e}")
            raise


class STTProviderFactory:
    """Factory for creating STT provider instances."""

    @staticmethod
    def create(settings: Settings) -> STTProvider:
        """Create STT provider based on settings."""
        providers = {
            "openai": OpenAISTTProvider,
            "google": GoogleSTTProvider,
            "whisper-local": WhisperLocalSTTProvider,
        }

        provider_class = providers.get(settings.stt_provider)
        if not provider_class:
            raise ValueError(f"Unknown STT provider: {settings.stt_provider}")

        return provider_class(settings)


# ==================== Text-to-Speech ====================


class TTSProvider(ABC):
    """Abstract base class for Text-to-Speech providers."""

    @abstractmethod
    async def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:
        """
        Synthesize text to speech audio.

        Args:
            text: Text to synthesize
            voice: Voice identifier

        Returns:
            Audio file bytes (MP3 or WAV)
        """
        pass


class OpenAITTSProvider(TTSProvider):
    """OpenAI TTS provider."""

    def __init__(self, settings: Settings):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.settings = settings

    async def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:
        """Synthesize using OpenAI TTS."""
        try:
            voice_id = voice or self.settings.tts_voice

            response = self.client.audio.speech.create(
                model="tts-1",
                voice=voice_id,
                input=text,
            )

            # Return audio bytes
            return response.content

        except Exception as e:
            logger.error(f"OpenAI TTS error: {e}")
            raise


class GoogleTTSProvider(TTSProvider):
    """Google Cloud Text-to-Speech provider."""

    def __init__(self, settings: Settings):
        try:
            from google.cloud import texttospeech
            self.client = texttospeech.TextToSpeechClient()
            self.settings = settings
        except ImportError:
            raise ImportError(
                "google-cloud-texttospeech is required for Google TTS. "
                "Install it with: pip install google-cloud-texttospeech"
            )

    async def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:
        """Synthesize using Google Cloud TTS."""
        try:
            from google.cloud import texttospeech

            synthesis_input = texttospeech.SynthesisInput(text=text)

            voice_params = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name=voice or "en-US-Neural2-F",
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )

            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice_params,
                audio_config=audio_config,
            )

            return response.audio_content

        except Exception as e:
            logger.error(f"Google TTS error: {e}")
            raise


class GTTSProvider(TTSProvider):
    """gTTS (Google Text-to-Speech) simple provider."""

    def __init__(self, settings: Settings):
        self.settings = settings

    async def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:
        """Synthesize using gTTS."""
        try:
            tts = gTTS(text=text, lang="en", slow=False)

            # Save to bytes buffer
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)

            return audio_buffer.read()

        except Exception as e:
            logger.error(f"gTTS error: {e}")
            raise


class TTSProviderFactory:
    """Factory for creating TTS provider instances."""

    @staticmethod
    def create(settings: Settings) -> TTSProvider:
        """Create TTS provider based on settings."""
        providers = {
            "openai": OpenAITTSProvider,
            "google": GoogleTTSProvider,
            "gtts": GTTSProvider,
        }

        provider_class = providers.get(settings.tts_provider)
        if not provider_class:
            raise ValueError(f"Unknown TTS provider: {settings.tts_provider}")

        return provider_class(settings)


# ==================== Unified Speech Processor ====================


class SpeechProcessor:
    """Unified speech processor for STT and TTS."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.stt_provider = STTProviderFactory.create(settings)
        self.tts_provider = TTSProviderFactory.create(settings)

    async def speech_to_text(
        self, audio_data: bytes, language: Optional[str] = None
    ) -> str:
        """
        Convert speech audio to text.

        Args:
            audio_data: Audio file bytes
            language: Language code (defaults to settings)

        Returns:
            Transcribed text
        """
        language = language or self.settings.stt_language
        return await self.stt_provider.transcribe(audio_data, language)

    async def text_to_speech(
        self, text: str, voice: Optional[str] = None
    ) -> bytes:
        """
        Convert text to speech audio.

        Args:
            text: Text to synthesize
            voice: Voice identifier (optional)

        Returns:
            Audio file bytes
        """
        return await self.tts_provider.synthesize(text, voice)

    def audio_to_base64(self, audio_data: bytes) -> str:
        """Convert audio bytes to base64 string for API responses."""
        return base64.b64encode(audio_data).decode("utf-8")

    def base64_to_audio(self, base64_string: str) -> bytes:
        """Convert base64 string to audio bytes."""
        return base64.b64decode(base64_string)
