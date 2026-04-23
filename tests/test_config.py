"""Unit tests for Config — load/save round-trip, defaults, is_configured."""

from __future__ import annotations

from src.core.config import Config


def test_defaults_when_file_missing(tmp_config_path):
    cfg = Config.load(tmp_config_path)
    assert cfg.api_key == ""
    assert cfg.language == "en"
    assert cfg.hotkey_modifiers == ["ctrl", "super"]
    assert cfg.is_configured is False


def test_is_configured_reflects_api_key(tmp_config_path):
    cfg = Config.load(tmp_config_path)
    assert cfg.is_configured is False
    cfg.api_key = "gsk_fake"
    assert cfg.is_configured is True


def test_load_save_round_trip(tmp_config_path):
    cfg = Config.load(tmp_config_path)
    cfg.api_key = "gsk_test_key"
    cfg.language = "pt"
    cfg.remove_fillers = False
    cfg.keyboard_commands = {"send it": "Return"}
    cfg.save(tmp_config_path)

    reloaded = Config.load(tmp_config_path)
    assert reloaded.api_key == "gsk_test_key"
    assert reloaded.language == "pt"
    assert reloaded.remove_fillers is False
    assert reloaded.keyboard_commands == {"send it": "Return"}


def test_load_tolerates_malformed_json(tmp_config_path, capsys):
    tmp_config_path.write_text("{ this is not json")
    cfg = Config.load(tmp_config_path)
    # Falls back to defaults instead of raising
    assert cfg.api_key == ""
    err = capsys.readouterr().out
    assert "Failed to load" in err


def test_hotkey_name_formatting():
    cfg = Config()
    cfg.hotkey_modifiers = ["ctrl", "super"]
    assert cfg.get_hotkey_name() == "Ctrl + Super"
