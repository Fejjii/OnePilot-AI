from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TranscriptionResponse:
    """Response from speech transcription."""
    
    transcript: str
    language: str | None = None
    duration: float | None = None
    model: str | None = None


class SpeechProvider(ABC):
    """Base interface for speech transcription providers."""
    
    @abstractmethod
    def transcribe(self, audio_bytes: bytes, mime_type: str) -> TranscriptionResponse:
        """Transcribe audio bytes to text.
        
        Args:
            audio_bytes: Raw audio bytes
            mime_type: MIME type of the audio (e.g., 'audio/webm')
            
        Returns:
            TranscriptionResponse with transcript and metadata
            
        Raises:
            ProviderUnavailableError: If transcription fails
        """
        ...
