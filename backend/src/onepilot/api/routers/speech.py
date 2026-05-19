"""HTTP endpoint for speech-to-text transcription."""

from __future__ import annotations

import time

from fastapi import APIRouter, File, Form, UploadFile

from onepilot.api.deps import CurrentPrincipal, DBSession, SettingsDep
from onepilot.core.errors import ValidationError, ProviderUnavailableError
from onepilot.providers.speech.openai_speech import OpenAISpeechProvider
from onepilot.schemas.speech import TranscribeResponse
from onepilot.security.permissions import require_member
from onepilot.services import usage_service

router = APIRouter(prefix="/speech", tags=["speech"])

# Allowed MIME types for audio files
ALLOWED_MIME_TYPES = {
    "audio/webm",
    "audio/wav",
    "audio/mpeg",
    "audio/mp4",
    "audio/ogg",
}

# Max file size: 25MB (matches OpenAI limit)
MAX_FILE_SIZE = 25 * 1024 * 1024


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_speech(
    audio: UploadFile = File(...),
    principal: CurrentPrincipal = None,
    session: DBSession = None,
    settings: SettingsDep = None,
) -> TranscribeResponse:
    """Transcribe speech to text using OpenAI Whisper.
    
    Args:
        audio: Audio file (webm, wav, mp3, mp4, ogg)
        principal: Authenticated user principal
        session: Database session
        settings: Application settings
        
    Returns:
        TranscribeResponse with transcript and metadata
        
    Raises:
        ValidationError: If file validation fails
        ProviderUnavailableError: If OpenAI is not configured
    """
    require_member(principal)
    
    # Validate MIME type
    content_type = audio.content_type or "application/octet-stream"
    if content_type not in ALLOWED_MIME_TYPES:
        raise ValidationError(
            f"Unsupported audio format: {content_type}. "
            f"Allowed types: {', '.join(ALLOWED_MIME_TYPES)}"
        )
    
    # Read audio bytes
    start_time = time.time()
    audio_bytes = await audio.read()
    
    # Validate file size
    if len(audio_bytes) > MAX_FILE_SIZE:
        raise ValidationError(
            f"Audio file too large: {len(audio_bytes)} bytes "
            f"(max: {MAX_FILE_SIZE} bytes / {MAX_FILE_SIZE / 1024 / 1024:.1f} MB)"
        )
    
    # Check if OpenAI is configured
    if not settings.has_openai:
        raise ProviderUnavailableError(
            "Speech transcription requires OpenAI configuration. "
            "Please set OPENAI_API_KEY in environment."
        )
    
    # Initialize OpenAI speech provider
    provider = OpenAISpeechProvider(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_SPEECH_MODEL,
    )
    
    # Transcribe audio
    try:
        result = provider.transcribe(audio_bytes, content_type)
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Track usage
        audio_seconds = float(result.duration or 0.0)
        usage_service.record(
            session,
            organization_id=principal.organization_id,
            user_id=principal.user_id,
            feature="speech_transcription",
            provider="openai",
            model=result.model or settings.OPENAI_SPEECH_MODEL,
            audio_seconds=audio_seconds,
            fallback_used=False,
            latency_ms=latency_ms,
            metadata={
                "language": result.language,
                "duration": result.duration,
                "file_size_bytes": len(audio_bytes),
                "mime_type": content_type,
            },
        )
        
        return TranscribeResponse(
            transcript=result.transcript,
            language=result.language,
            duration=result.duration,
            provider="openai",
            model=result.model or settings.OPENAI_SPEECH_MODEL,
            fallback_used=False,
            usage={
                "latency_ms": latency_ms,
                "file_size_bytes": len(audio_bytes),
                "duration_seconds": result.duration,
            },
        )
    except ProviderUnavailableError:
        raise
    except Exception as exc:
        raise ProviderUnavailableError(
            f"Speech transcription failed: {exc}"
        ) from exc
