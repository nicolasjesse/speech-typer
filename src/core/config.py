"""Configuration management for PontySpeech."""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """Application configuration."""

    # Groq API (for Whisper transcription)
    api_key: str = ""
    model: str = "whisper-large-v3-turbo"
    language: str = "en"

    # LLM correction settings
    correction_provider: str = "openai"  # "groq" or "openai"
    openai_api_key: str = ""

    hotkey_modifiers: list = field(default_factory=lambda: ["ctrl", "super"])
    audio_device: Optional[int] = None
    remove_fillers: bool = True

    # Voice commands settings
    voice_commands_enabled: bool = True
    shell_commands: dict = field(default_factory=dict)  # phrase -> shell command
    keyboard_commands: dict = field(default_factory=dict)  # phrase -> key name (extends defaults)

    _config_path: Path = field(default=None, repr=False)

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """Load configuration from file."""
        if config_path is None:
            # Default to config.json in project root
            config_path = Path(__file__).parent.parent.parent / "config.json"

        config = cls()
        config._config_path = config_path

        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)

                config.api_key = data.get("api_key", config.api_key)
                config.model = data.get("model", config.model)
                config.language = data.get("language", config.language)
                config.correction_provider = data.get("correction_provider", config.correction_provider)
                config.openai_api_key = data.get("openai_api_key", config.openai_api_key)
                config.hotkey_modifiers = data.get("hotkey_modifiers", config.hotkey_modifiers)
                config.audio_device = data.get("audio_device", config.audio_device)
                config.remove_fillers = data.get("remove_fillers", config.remove_fillers)
                config.voice_commands_enabled = data.get("voice_commands_enabled", config.voice_commands_enabled)
                config.shell_commands = data.get("shell_commands", config.shell_commands)
                config.keyboard_commands = data.get("keyboard_commands", config.keyboard_commands)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to load config from {config_path}: {e}")

        return config

    def save(self, config_path: Optional[Path] = None) -> None:
        """Save configuration to file."""
        if config_path is None:
            config_path = self._config_path

        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config.json"

        data = {
            "api_key": self.api_key,
            "model": self.model,
            "language": self.language,
            "correction_provider": self.correction_provider,
            "openai_api_key": self.openai_api_key,
            "hotkey_modifiers": self.hotkey_modifiers,
            "audio_device": self.audio_device,
            "remove_fillers": self.remove_fillers,
            "voice_commands_enabled": self.voice_commands_enabled,
            "shell_commands": self.shell_commands,
            "keyboard_commands": self.keyboard_commands,
        }

        try:
            with open(config_path, "w") as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            print(f"Error: Failed to save config to {config_path}: {e}")

    @property
    def is_configured(self) -> bool:
        """Check if the API key is configured."""
        return bool(self.api_key)

    def get_hotkey_name(self) -> str:
        """Get human-readable hotkey name."""
        names = {
            "ctrl": "Ctrl",
            "super": "Super",
            "alt": "Alt",
            "shift": "Shift",
        }
        parts = [names.get(m, m.capitalize()) for m in self.hotkey_modifiers]
        return " + ".join(parts)
