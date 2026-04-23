"""Groq Whisper API client for transcription."""

import io
import time
import wave
from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    """Result from transcription."""

    text: str
    language: str | None = None
    audio_duration_s: float = 0.0  # length of the audio clip in seconds
    latency_ms: float = 0.0  # wall-clock time of the API call
    model: str = ""
    error: str | None = None

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
            except ImportError as err:
                raise ImportError("groq package not installed. Run: pip install groq") from err
        return self._client

    def transcribe(self, wav_data: bytes) -> TranscriptionResult:
        """Transcribe WAV audio data."""
        audio_duration_s = _wav_duration_seconds(wav_data)

        if not wav_data:
            return TranscriptionResult(text="", error="No audio data provided", model=self._model)

        if not self._api_key:
            return TranscriptionResult(
                text="",
                error="API key not configured",
                audio_duration_s=audio_duration_s,
                model=self._model,
            )

        started = time.perf_counter()

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
                audio_duration_s=audio_duration_s,
                latency_ms=(time.perf_counter() - started) * 1000,
                model=self._model,
            )

        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "unauthorized" in error_msg.lower():
                error_msg = "Invalid API key"
            elif "429" in error_msg:
                error_msg = "Rate limit exceeded"
            elif "connection" in error_msg.lower():
                error_msg = "Connection error - check internet"

            return TranscriptionResult(
                text="",
                error=error_msg,
                audio_duration_s=audio_duration_s,
                latency_ms=(time.perf_counter() - started) * 1000,
                model=self._model,
            )

    def set_api_key(self, api_key: str) -> None:
        """Update the API key."""
        self._api_key = api_key
        self._client = None

    def set_language(self, language: str) -> None:
        """Update the transcription language."""
        self._language = language


def _wav_duration_seconds(wav_data: bytes) -> float:
    """Best-effort duration parse from a WAV byte blob. Returns 0.0 on failure."""
    if not wav_data:
        return 0.0
    try:
        with wave.open(io.BytesIO(wav_data), "rb") as wav:
            frames = wav.getnframes()
            rate = wav.getframerate() or 1
            return frames / float(rate)
    except Exception:
        return 0.0
