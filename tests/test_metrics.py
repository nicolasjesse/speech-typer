"""Unit tests for the metrics logger + cost estimation."""

from __future__ import annotations

import json
from types import SimpleNamespace

from src.core.metrics import (
    MetricsLogger,
    RequestMetric,
    default_metrics_path,
    estimate_chat_cost,
    estimate_whisper_cost,
)


def test_whisper_cost_turbo():
    # 1 hour of audio at $0.04/hr
    assert estimate_whisper_cost("whisper-large-v3-turbo", 3600.0) == 0.04


def test_whisper_cost_unknown_model_returns_zero():
    assert estimate_whisper_cost("unknown-model", 3600.0) == 0.0


def test_chat_cost_gpt4o_mini():
    # gpt-4o-mini: $0.15/M input, $0.60/M output
    cost = estimate_chat_cost("gpt-4o-mini", 1_000_000, 1_000_000)
    assert cost == 0.75


def test_chat_cost_unknown_model_returns_zero():
    assert estimate_chat_cost("made-up-model", 1000, 500) == 0.0


def test_logger_writes_jsonl(tmp_path):
    path = tmp_path / "metrics.jsonl"
    logger = MetricsLogger(path=path)
    m = RequestMetric(timestamp="2026-04-23T00:00:00+00:00", mode="transcription", language="en")
    logger.log(m)
    logger.log(m)

    lines = path.read_text().strip().splitlines()
    assert len(lines) == 2
    # Each line must be valid JSON
    for line in lines:
        parsed = json.loads(line)
        assert parsed["mode"] == "transcription"
        assert parsed["language"] == "en"


def test_logger_respects_enabled_flag(tmp_path):
    path = tmp_path / "metrics.jsonl"
    logger = MetricsLogger(path=path, enabled=False)
    logger.log(RequestMetric(mode="transcription", language="en"))
    assert not path.exists()


def test_logger_never_raises_on_write_failure(tmp_path, capsys):
    # Point at a path whose parent is a FILE (not a dir) to force a failure
    blocker = tmp_path / "blocker"
    blocker.write_text("")
    bad_path = blocker / "metrics.jsonl"
    logger = MetricsLogger(path=bad_path)
    logger.log(RequestMetric())  # must not raise
    captured = capsys.readouterr()
    assert "warning" in captured.err.lower() or captured.err == ""


def test_record_request_aggregates_cost_and_latency(tmp_path):
    path = tmp_path / "metrics.jsonl"
    logger = MetricsLogger(path=path)

    transcription = SimpleNamespace(
        text="hello world",
        audio_duration_s=2.0,
        latency_ms=300.0,
        model="whisper-large-v3-turbo",
        error=None,
    )
    correction = SimpleNamespace(
        text="Hello world.",
        corrected=True,
        latency_ms=200.0,
        prompt_tokens=100,
        completion_tokens=20,
        total_tokens=120,
        model="gpt-4o-mini",
        provider="openai",
        prompt_id="transcription_en",
        prompt_version=1,
        error=None,
    )

    m = logger.record_request(
        mode="transcription",
        language="en",
        transcription=transcription,
        correction=correction,
    )
    assert m.total_ms == 500.0
    assert m.whisper_cost_usd == estimate_whisper_cost("whisper-large-v3-turbo", 2.0)
    assert m.correction_cost_usd == estimate_chat_cost("gpt-4o-mini", 100, 20)
    assert m.total_cost_usd == round(m.whisper_cost_usd + m.correction_cost_usd, 6)
    assert path.exists()


def test_default_path_respects_xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert default_metrics_path() == tmp_path / "holler" / "metrics.jsonl"
