"""Unit tests for the prompt registry."""

from __future__ import annotations

from src.text import prompts


def test_registry_loads_all_four_builtin_prompts():
    prompts.reload()
    all_prompts = prompts.list_all()
    ids = {p.id for p in all_prompts}
    assert ids == {"transcription_en", "transcription_pt", "prompt_mode_en", "prompt_mode_pt"}


def test_get_by_mode_and_language():
    p = prompts.get("transcription", "en")
    assert p.id == "transcription_en"
    assert p.mode == "transcription"
    assert p.language == "en"
    assert p.prompt.strip() != ""


def test_get_falls_back_to_english():
    # "fr" doesn't exist — should fall back to English prompt of same mode
    p = prompts.get("transcription", "fr")
    assert p.language == "en"
    assert p.mode == "transcription"


def test_get_raises_for_unknown_mode():
    import pytest

    with pytest.raises(KeyError):
        prompts.get("does_not_exist", "en")


def test_version_is_an_integer():
    for p in prompts.list_all():
        assert isinstance(p.version, int)
        assert p.version >= 1


def test_prompts_include_required_fields():
    for p in prompts.list_all():
        assert p.id
        assert p.mode in {"transcription", "prompt"}
        assert p.language
        assert p.prompt.strip()
        assert p.description.strip()
