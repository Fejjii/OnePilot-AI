from __future__ import annotations

import io

from openai import OpenAI

from onepilot.core.errors import ProviderUnavailableError
from onepilot.providers.speech.base import SpeechProvider, TranscriptionResponse


class OpenAISpeechProvider(SpeechProvider):
    """OpenAI Whisper-based speech transcription provider."""
    
    # Max file size: 25MB (OpenAI limit)
    MAX_FILE_SIZE = 25 * 1024 * 1024
    
    # MIME type to file extension mapping
    MIME_TO_EXT = {
        "audio/webm": "webm",
        "audio/wav": "wav",
        "audio/mpeg": "mp3",
        "audio/mp4": "mp4",
        "audio/ogg": "ogg",
    }
    
    def __init__(self, api_key: str, model: str = "whisper-1") -> None:
        """Initialize OpenAI speech provider.
        
        Args:
            api_key: OpenAI API key
            model: Model to use for transcription (default: whisper-1)
            
        Raises:
            ProviderUnavailableError: If API key is not configured
        """
        if not api_key:
            raise ProviderUnavailableError("OpenAI API key not configured")
        self._api_key = api_key
        self._model = model
        self._client = OpenAI(api_key=api_key)
    
    def transcribe(self, audio_bytes: bytes, mime_type: str) -> TranscriptionResponse:
        """Transcribe audio using OpenAI Whisper API.
        
        Args:
            audio_bytes: Raw audio bytes
            mime_type: MIME type of the audio
            
        Returns:
            TranscriptionResponse with transcript and metadata
            
        Raises:
            ProviderUnavailableError: If validation fails or API call fails
        """
        # Validate file size
        if len(audio_bytes) > self.MAX_FILE_SIZE:
            raise ProviderUnavailableError(
                f"Audio file too large: {len(audio_bytes)} bytes "
                f"(max: {self.MAX_FILE_SIZE})"
            )
        
        # Validate MIME type
        if mime_type not in self.MIME_TO_EXT:
            raise ProviderUnavailableError(
                f"Unsupported MIME type: {mime_type}. "
                f"Supported types: {', '.join(self.MIME_TO_EXT.keys())}"
            )
        
        # Get file extension for the audio format
        extension = self.MIME_TO_EXT[mime_type]
        
        try:
            # OpenAI expects a file-like object with a name attribute
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = f"audio.{extension}"
            
            # Call OpenAI Whisper API
            response = self._client.audio.transcriptions.create(
                model=self._model,
                file=audio_file,
                response_format="verbose_json",
            )
            
            return TranscriptionResponse(
                transcript=response.text,
                language=getattr(response, "language", None),
                duration=getattr(response, "duration", None),
                model=self._model,
            )
        except Exception as exc:
            raise ProviderUnavailableError(
                f"OpenAI speech transcription failed: {exc}"
            ) from exc
