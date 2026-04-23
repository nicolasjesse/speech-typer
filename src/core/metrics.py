"""Metrics logger — append-only JSONL for observability and cost tracking.

Every completed dictation request writes one line to
``$XDG_DATA_HOME/holler/metrics.jsonl`` (default
``~/.local/share/holler/metrics.jsonl``). The file is never read by the app
itself — ``scripts/report.py`` summarizes it on demand.

Design: single line per request, stdlib-only, fire-and-forget. Failures logging
must never break the dictation pipeline, so every write is wrapped in a
try/except that drops the record silently (with a stderr warning).
"""

from __future__ import annotations

import json
import os
import sys
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# ----- pricing (USD, as of 2026-04) ---------------------------------------
# These are coarse estimates for tracking, not billing. Update as providers move.
WHISPER_COST_PER_HOUR_USD = {
    "whisper-large-v3-turbo": 0.04,
    "whisper-large-v3": 0.111,
}

# (prompt, completion) cost per 1M tokens
CHAT_COST_PER_M_TOKENS_USD = {
    # OpenAI
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    # Groq (free tier in practice, but we track list price)
    "llama-3.3-70b-versatile": (0.59, 0.79),
    "llama-3.1-8b-instant": (0.05, 0.08),
}


def estimate_whisper_cost(model: str, audio_duration_s: float) -> float:
    """USD cost for a Whisper call. Returns 0 for unknown models."""
    rate = WHISPER_COST_PER_HOUR_USD.get(model, 0.0)
    return round(rate * audio_duration_s / 3600.0, 6)


def estimate_chat_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """USD cost for a chat completion. Returns 0 for unknown models."""
    rates = CHAT_COST_PER_M_TOKENS_USD.get(model)
    if rates is None:
        return 0.0
    in_rate, out_rate = rates
    return round(
        (prompt_tokens * in_rate + completion_tokens * out_rate) / 1_000_000.0,
        6,
    )


# ----- record -------------------------------------------------------------


@dataclass
class RequestMetric:
    """One completed dictation request. Serialized as one JSONL line."""

    timestamp: str = ""
    mode: str = ""  # "transcription" or "prompt"
    language: str = ""
    # transcription step
    whisper_model: str = ""
    audio_duration_s: float = 0.0
    transcription_ms: float = 0.0
    whisper_cost_usd: float = 0.0
    transcription_chars: int = 0
    transcription_error: str | None = None
    # correction step
    correction_provider: str = ""
    correction_model: str = ""
    correction_ms: float = 0.0
    prompt_id: str = ""
    prompt_version: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    correction_cost_usd: float = 0.0
    correction_error: str | None = None
    corrected: bool = False
    # totals
    total_ms: float = 0.0
    total_cost_usd: float = 0.0
    # arbitrary extras for future use without a schema bump
    extra: dict = field(default_factory=dict)


# ----- logger -------------------------------------------------------------


def default_metrics_path() -> Path:
    """Return the default metrics file path, honoring XDG_DATA_HOME."""
    base = os.environ.get("XDG_DATA_HOME", "").strip()
    root = Path(base) if base else Path.home() / ".local" / "share"
    return root / "holler" / "metrics.jsonl"


class MetricsLogger:
    """Append-only JSONL logger. Thread-safe (dictation runs in a background thread)."""

    def __init__(self, path: Path | None = None, enabled: bool = True):
        self._path = path or default_metrics_path()
        self._enabled = enabled
        self._lock = threading.Lock()

    @property
    def path(self) -> Path:
        return self._path

    def log(self, metric: RequestMetric) -> None:
        """Append a single metric. Never raises — warns to stderr on failure."""
        if not self._enabled:
            return
        try:
            with self._lock:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                with self._path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(asdict(metric), ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[metrics] warning: failed to write metric: {e}", file=sys.stderr)

    # -- convenience helpers for the app ---------------------------------

    def record_request(
        self,
        mode: str,
        language: str,
        transcription,
        correction,
    ) -> RequestMetric:
        """Build and log a metric from a TranscriptionResult + CorrectionResult."""
        whisper_cost = estimate_whisper_cost(
            getattr(transcription, "model", "") or "",
            getattr(transcription, "audio_duration_s", 0.0) or 0.0,
        )
        correction_cost = estimate_chat_cost(
            getattr(correction, "model", "") or "",
            getattr(correction, "prompt_tokens", 0) or 0,
            getattr(correction, "completion_tokens", 0) or 0,
        )
        transcription_ms = float(getattr(transcription, "latency_ms", 0.0) or 0.0)
        correction_ms = float(getattr(correction, "latency_ms", 0.0) or 0.0)

        metric = RequestMetric(
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            mode=mode,
            language=language,
            whisper_model=getattr(transcription, "model", "") or "",
            audio_duration_s=round(float(getattr(transcription, "audio_duration_s", 0.0)), 3),
            transcription_ms=round(transcription_ms, 2),
            whisper_cost_usd=whisper_cost,
            transcription_chars=len(getattr(transcription, "text", "") or ""),
            transcription_error=getattr(transcription, "error", None),
            correction_provider=getattr(correction, "provider", "") or "",
            correction_model=getattr(correction, "model", "") or "",
            correction_ms=round(correction_ms, 2),
            prompt_id=getattr(correction, "prompt_id", "") or "",
            prompt_version=int(getattr(correction, "prompt_version", 0) or 0),
            prompt_tokens=int(getattr(correction, "prompt_tokens", 0) or 0),
            completion_tokens=int(getattr(correction, "completion_tokens", 0) or 0),
            correction_cost_usd=correction_cost,
            correction_error=getattr(correction, "error", None),
            corrected=bool(getattr(correction, "corrected", False)),
            total_ms=round(transcription_ms + correction_ms, 2),
            total_cost_usd=round(whisper_cost + correction_cost, 6),
        )
        self.log(metric)
        return metric


# Exposed for tests + scripts/report.py
__all__ = [
    "MetricsLogger",
    "RequestMetric",
    "default_metrics_path",
    "estimate_chat_cost",
    "estimate_whisper_cost",
]


if __name__ == "__main__":
    # Tiny demo: log a synthetic record.
    m = RequestMetric(
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        mode="transcription",
        language="en",
        whisper_model="whisper-large-v3-turbo",
        audio_duration_s=3.5,
        transcription_ms=420.0,
        whisper_cost_usd=estimate_whisper_cost("whisper-large-v3-turbo", 3.5),
        transcription_chars=42,
        correction_provider="openai",
        correction_model="gpt-4o-mini",
        correction_ms=310.0,
        prompt_tokens=180,
        completion_tokens=24,
        correction_cost_usd=estimate_chat_cost("gpt-4o-mini", 180, 24),
        corrected=True,
    )
    m.total_ms = m.transcription_ms + m.correction_ms
    m.total_cost_usd = m.whisper_cost_usd + m.correction_cost_usd
    MetricsLogger().log(m)
    print(f"Wrote demo metric to {default_metrics_path()}")
