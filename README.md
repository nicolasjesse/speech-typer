# Speech Typer

A lightweight push-to-talk voice dictation tool for Linux. Hold a hotkey, speak, release — your words get transcribed and typed into the active window.

Uses [Groq's Whisper API](https://console.groq.com/) for fast speech-to-text and an LLM (OpenAI or Groq) for cleaning up transcription errors.

> **Primary target: Pop!_OS 24.04 with COSMIC desktop (Wayland).** It may work on other Wayland compositors (GNOME, Sway, Hyprland) and X11, but COSMIC is the only tested and actively supported configuration.

## How It Works

1. **Hold** `Ctrl + Super` (Windows key) while speaking
2. **Release** when done
3. Your transcribed text is automatically typed into whatever window is focused

The app runs in the system tray with minimal resource usage.

## Features

- **Push-to-talk recording** with configurable hotkey
- **Groq Whisper** transcription (~$0.04/hour of audio)
- **LLM text correction** — fixes transcription errors, handles spoken punctuation ("question mark" becomes `?`), removes filler words
- **Two modes**: Transcription (literal dictation) and Prompt (rephrases into clear prompts)
- **Multi-language**: English, Portuguese, and 10+ other languages
- **Voice commands**: Trigger keyboard shortcuts or shell commands by voice
- **Platform-aware**: Uses `dotool` on COSMIC, `wtype` on other Wayland compositors, `xdotool` on X11

## Setup

### 1. System Dependencies

**Pop!_OS 24.04 (COSMIC):**

```bash
# Audio capture
sudo apt install libportaudio2

# Wayland clipboard
sudo apt install wl-clipboard

# Text injection (dotool) — build from source
# https://sr.ht/~geb/dotool/
# Or install via your preferred method

# Add your user to the input group (required for hotkey detection on Wayland)
sudo usermod -aG input $USER
# Then logout and login again
```

**Other Debian/Ubuntu (X11):**

```bash
sudo apt install libportaudio2 xclip xdotool
```

### 2. Python Dependencies

```bash
python3 -m venv .env
source .env/bin/activate
pip install -r requirements.txt
```

### 3. Configuration

Copy the example config and fill in your API keys:

```bash
cp config.example.json config.json
```

Then edit `config.json` with your keys:

| Property | Required | Description |
|---|---|---|
| `api_key` | **Yes** | Groq API key for Whisper transcription. Get one at https://console.groq.com/ |
| `openai_api_key` | No* | OpenAI API key for LLM text correction. Get one at https://platform.openai.com/ |
| `correction_provider` | No | `"openai"` (default) or `"groq"` — which LLM to use for text correction |
| `model` | No | Whisper model (default: `whisper-large-v3-turbo`) |
| `language` | No | Transcription language code (default: `"en"`) |
| `hotkey_modifiers` | No | Keys to hold for recording (default: `["ctrl", "super"]`) |
| `audio_device` | No | Microphone device ID, `null` for system default |
| `remove_fillers` | No | Remove "um", "uh", "like" etc. (default: `true`) |
| `voice_commands_enabled` | No | Enable voice commands (default: `false`) |
| `keyboard_commands` | No | Map spoken phrases to key presses, e.g. `{"send it": "Return"}` |
| `shell_commands` | No | Map spoken phrases to shell commands |

*If `correction_provider` is `"openai"`, then `openai_api_key` is required. If set to `"groq"`, the Groq `api_key` is used for both transcription and correction.

### 4. Run

```bash
python run.py
```

On first launch without a `config.json`, a settings dialog will appear where you can enter your API key and select your microphone.

## Important Notes for COSMIC Desktop

- **`wtype` does not work correctly on COSMIC** — it reports success but types wrong characters. Speech Typer automatically detects COSMIC and uses `dotool` instead.
- You **must** be in the `input` group for hotkey detection to work on Wayland. Run `sudo usermod -aG input $USER` and re-login.
- `dotool` must be installed and accessible in your PATH.

## Troubleshooting

| Problem | Solution |
|---|---|
| "Failed to start hotkey listener" | Make sure you're in the `input` group and have logged out/in after adding |
| "Failed to paste text" | Install `wl-clipboard` and `dotool` (Wayland) or `xdotool` and `xclip` (X11) |
| No audio captured | Install `libportaudio2` and check microphone in Settings |
| Wrong characters typed (numbers) | You're likely on COSMIC — update to the latest version which auto-detects COSMIC |
| Transcription errors | Try switching `correction_provider` to `"groq"` if OpenAI is unavailable |

## Cost

The running cost is negligible. With daily use over an entire month, total API spend stayed **well under $1**.

- **Groq Whisper**: ~$0.04/hour of audio (each dictation is just a few seconds)
- **OpenAI gpt-4o-mini**: fractions of a cent per correction call
- **Groq LLM** (alternative): free tier available

## License

MIT
