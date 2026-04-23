# Holler

[![CI](https://github.com/nicolasjesse/holler/actions/workflows/ci.yml/badge.svg)](https://github.com/nicolasjesse/holler/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Push-to-talk voice dictation for Linux. Hold a hotkey, speak, release — transcribed text appears in whatever window is focused.

Holler streams audio through [Groq's Whisper API](https://console.groq.com/) for fast speech-to-text, then runs the result through an LLM (OpenAI or Groq) that fixes transcription errors, handles spoken punctuation, and optionally rephrases half-formed thoughts into clean prompts.

## Why this exists

Voice dictation on Linux — especially on Wayland compositors like COSMIC — is a mess. `wtype` misbehaves on some compositors, `ydotool` needs a daemon, and no stock tool ships with LLM correction. Holler is the dictation tool I wanted: a single hotkey, usable everywhere, with transcription quality that matches what's possible in 2026.

Primary target: **Pop!_OS 24.04 with COSMIC (Wayland)**. It also works on GNOME/KDE Wayland, Sway, Hyprland, and X11 — platform detection in [`src/core/session.py`](src/core/session.py) picks the right backend at runtime.

## Features

- **Push-to-talk** with a configurable hotkey (default `Ctrl + Super`)
- **Groq Whisper** transcription (`whisper-large-v3-turbo`, ~$0.04/hour of audio)
- **LLM correction** — fixes spelling, handles spoken punctuation (`"question mark"` → `?`), removes filler words
- **Two modes** — *transcription* (literal dictation) and *prompt* (rephrase into a clean LLM prompt)
- **Multilingual** — English, Portuguese, 10+ others
- **Voice commands** — map spoken phrases to keyboard shortcuts or shell commands
- **Platform-aware** — automatically routes to `dotool` (COSMIC), `wtype` (other Wayland), or `xdotool` (X11)
- **System tray** with mode/language switcher and hot config reload

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full pipeline, threading model, and platform-detection logic. Quick version:

```
hotkey press → mic → Groq Whisper → filler removal → LLM correction → text injection
```

## Setup

### 1. System dependencies

**Pop!_OS 24.04 (COSMIC) or any Wayland compositor:**

```bash
sudo apt install libportaudio2 wl-clipboard
# Plus dotool (preferred) — see https://sr.ht/~geb/dotool/
# Add your user to the input group so evdev can read hotkeys on Wayland:
sudo usermod -aG input $USER   # log out and back in after
```

**X11 (Debian/Ubuntu):**

```bash
sudo apt install libportaudio2 xclip xdotool
```

### 2. Python

```bash
python3 -m venv .env
source .env/bin/activate
pip install -e .           # or: pip install -r requirements.txt
```

For development:

```bash
pip install -e ".[dev]"
```

### 3. Configuration

```bash
cp config.example.json config.json
# edit config.json with your keys
```

| Property | Required | Description |
|---|---|---|
| `api_key` | ✅ | Groq API key — https://console.groq.com/ |
| `openai_api_key` | conditional¹ | OpenAI key for correction — https://platform.openai.com/ |
| `correction_provider` | | `"openai"` (default) or `"groq"` |
| `model` | | Whisper model (default `whisper-large-v3-turbo`) |
| `language` | | `"en"`, `"pt"`, `"auto"`, etc. |
| `hotkey_modifiers` | | default `["ctrl", "super"]` |
| `audio_device` | | `null` = system default |
| `remove_fillers` | | default `true` |
| `voice_commands_enabled` | | default `false` |
| `keyboard_commands` | | `{"send it": "Return"}` |
| `shell_commands` | | `{"open terminal": "gnome-terminal"}` |

¹ Required only if `correction_provider` is `"openai"`. Set to `"groq"` to use a single API key for both transcription and correction.

### 4. Run

```bash
python run.py
# or, after pip install -e .
holler
```

On first launch without a `config.json`, a settings dialog appears where you can paste your API key and pick a microphone.

## COSMIC-specific notes

- `wtype` reports success but types wrong characters on COSMIC. Holler auto-detects COSMIC and routes to `dotool` instead — see [ARCHITECTURE.md#why-dotool-on-cosmic-specifically](ARCHITECTURE.md#why-dotool-on-cosmic-specifically).
- You **must** be in the `input` group for hotkey detection on Wayland.
- `dotool` must be installed and on `PATH`.

## Troubleshooting

| Problem | Fix |
|---|---|
| "Failed to start hotkey listener" | Join the `input` group and re-login |
| "Failed to paste text" | Install `wl-clipboard`+`dotool` (Wayland) or `xdotool`+`xclip` (X11) |
| No audio captured | Install `libportaudio2`, check the mic in Settings |
| Wrong characters typed | You're on COSMIC — update to latest, it auto-detects COSMIC |
| Transcription errors | Try `correction_provider: "groq"` |

## Cost

Running cost is negligible — daily use over a month stays **well under $1**:

- **Groq Whisper**: ~$0.04/hour of audio (each dictation is a few seconds)
- **OpenAI `gpt-4o-mini`** correction: fractions of a cent per call
- **Groq Llama 3.3 70B** correction (alternative): free tier covers heavy use

## Development

```bash
pip install -e ".[dev]"

# Lint + format
ruff check .
ruff format .

# Tests (coming in PR 3)
pytest
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for extension points.

## License

MIT — see [LICENSE](LICENSE).
