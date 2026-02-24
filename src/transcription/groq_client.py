"""Groq Whisper API client for transcription."""

import io
from typing import Optional
from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    """Result from transcription."""

    text: str
    language: Optional[str] = None
    duration: Optional[float] = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None and bool(self.text)


class GroqTranscriber:
    """Transcribes audio using Groq's Whisper API."""

    def __init__(
        self,
        api_key: str,
        model: str = "whisper-large-v3-turbo",
        language: str = "en",
    ):
        """Initialize the Groq client."""
        self._api_key = api_key
        self._model = model
        self._language = language
        self._client = None

    def _get_client(self):
        """Lazily initialize the Groq client."""
        if self._client is None:
            try:
                from groq import Groq
                self._client = Groq(api_key=self._api_key)
            except ImportError:
                raise ImportError("groq package not installed. Run: pip install groq")
        return self._client

    def transcribe(self, wav_data: bytes) -> TranscriptionResult:
        """Transcribe WAV audio data."""
        if not wav_data:
            return TranscriptionResult(text="", error="No audio data provided")

        if not self._api_key:
            return TranscriptionResult(text="", error="API key not configured")

        try:
            client = self._get_client()

            # Create file-like object from bytes
            audio_file = io.BytesIO(wav_data)
            audio_file.name = "recording.wav"

            # Call Groq API
            params = {
                "file": audio_file,
                "model": self._model,
                "response_format": "json",
            }
            # Only set language if not auto-detect
            if self._language and self._language != "auto":
                params["language"] = self._language

            response = client.audio.transcriptions.create(**params)

            text = response.text.strip() if response.text else ""

            return TranscriptionResult(
                text=text,
                language=self._language,
            )

        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "unauthorized" in error_msg.lower():
                error_msg = "Invalid API key"
            elif "429" in error_msg:
                error_msg = "Rate limit exceeded"
            elif "connection" in error_msg.lower():
                error_msg = "Connection error - check internet"

            return TranscriptionResult(text="", error=error_msg)

    def set_api_key(self, api_key: str) -> None:
        """Update the API key."""
        self._api_key = api_key
        self._client = None

    def set_language(self, language: str) -> None:
        """Update the transcription language."""
        self._language = language
