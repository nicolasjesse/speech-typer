"""Unit tests for TextCorrector — skip conditions, sanity check, LLM mocking."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.text.corrector import TextCorrector


def _fake_response(text: str, prompt_tokens: int = 100, completion_tokens: int = 20):
    """Build an object shaped like OpenAI/Groq chat.completions response."""
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )
    choice = SimpleNamespace(message=SimpleNamespace(content=text))
    return SimpleNamespace(choices=[choice], usage=usage)


def _corrector_with_mock(response_text: str, provider="openai"):
    c = TextCorrector(api_key="sk-fake", provider=provider)
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _fake_response(response_text)
    c._client = mock_client  # inject mocked client
    return c, mock_client


def test_skip_when_disabled():
    c, mock = _corrector_with_mock("anything")
    c.set_enabled(False)
    result = c.correct("hello there friend")
    assert result.text == "hello there friend"
    assert result.error == "disabled"
    mock.chat.completions.create.assert_not_called()


def test_skip_when_no_api_key():
    c = TextCorrector(api_key="", provider="openai")
    result = c.correct("hello there friend")
    assert result.error == "no API key"
    assert result.text == "hello there friend"


def test_skip_when_empty():
    c, mock = _corrector_with_mock("anything")
    result = c.correct("")
    assert result.error == "empty input"
    mock.chat.completions.create.assert_not_called()


def test_skip_when_too_short():
    c, mock = _corrector_with_mock("anything")
    result = c.correct("hi there")  # 2 words
    assert result.error == "too short"
    mock.chat.completions.create.assert_not_called()


def test_happy_path_returns_corrected_text():
    c, _ = _corrector_with_mock("How are you?")
    result = c.correct("how are you question mark")
    assert result.text == "How are you?"
    assert result.corrected is True
    assert result.error is None
    assert result.prompt_tokens == 100
    assert result.completion_tokens == 20
    assert result.prompt_id == "transcription_en" or result.prompt_id == "prompt_mode_en"


def test_length_sanity_check_rejects_hallucinated_expansion():
    # 200-char output from a 20-char input > 2× → reject, fall back to input
    c, _ = _corrector_with_mock("x" * 200)
    result = c.correct("this is a short one")
    assert result.text == "this is a short one"
    assert result.error == "length sanity check failed"
    assert result.corrected is False


def test_length_sanity_check_rejects_truncation():
    # 2-char output from a 50-char input < 0.3× → reject
    c, _ = _corrector_with_mock("x")
    result = c.correct("this is a somewhat longer original sentence here")
    assert result.text.startswith("this is")
    assert result.error == "length sanity check failed"


def test_corrected_flag_false_when_output_equals_input():
    # Model returns the input verbatim — corrected should be False
    original = "this is already perfectly fine"
    c, _ = _corrector_with_mock(original)
    result = c.correct(original)
    assert result.corrected is False
    assert result.error is None


def test_mode_and_language_switching():
    c, _ = _corrector_with_mock("Como você está?")
    c.set_mode(TextCorrector.MODE_TRANSCRIPTION)
    c.set_language("pt")
    result = c.correct("como vai você")
    assert result.prompt_id == "transcription_pt"


def test_provider_switching_resets_model():
    c = TextCorrector(api_key="sk-fake", provider="openai")
    assert c._model == "gpt-4o-mini"
    c.set_provider("groq", api_key="gsk-fake")
    assert c._model == "llama-3.3-70b-versatile"


@pytest.mark.parametrize(
    "mode,expected_id",
    [
        ("transcription", "transcription_en"),
        ("prompt", "prompt_mode_en"),
    ],
)
def test_prompt_id_matches_mode(mode, expected_id):
    # Mock output must be within the 0.3×-2× sanity window of the input
    c, _ = _corrector_with_mock("hello there friend today.")
    c.set_mode(mode)
    c.set_language("en")
    result = c.correct("hello there friend today")
    assert result.error is None  # guard: happy-path must not hit any skip branch
    assert result.prompt_id == expected_id
