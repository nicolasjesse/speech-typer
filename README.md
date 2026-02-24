# Ponty Speech

A lightweight voice dictation app for Linux using Groq's Whisper API.

> **Note:** This is a personal project built primarily for **Pop!_OS with Wayland**. It may work on other Linux distributions, but Pop!_OS + Wayland is the only officially supported configuration.

## Features

- **Hold-to-record**: Hold Ctrl + Super (Windows key) while speaking, release to transcribe
- **Smart formatting**: Auto-punctuation, filler word removal, capitalization
- **Auto-paste**: Transcribed text is automatically pasted into the active window
- **System tray**: Minimal UI, runs in background
- **Recording indicator**: Visual feedback when recording

## Requirements

### Python Dependencies

```bash
pip install -r requirements.txt
```

### System Dependencies

**Pop!_OS (recommended):**
```bash
# Audio
sudo apt install libportaudio2

# Wayland clipboard + input
sudo apt install wl-clipboard
# dotool: build from source (https://sr.ht/~geb/dotool/)
```

**Other Debian/Ubuntu (X11):**
```bash
sudo apt install libportaudio2 xclip xdotool
```

**Fedora:**
```bash
sudo dnf install portaudio xclip xdotool wl-clipboard
```

### Wayland Setup (Pop!_OS)

Add your user to the `input` group:

```bash
sudo usermod -aG input $USER
```

Then **logout and login again** for the change to take effect.

## Setup

1. Get a Groq API key from https://console.groq.com/
2. Run the application:
   ```bash
   python run.py
   ```
3. Click the tray icon → Settings and enter your API key

## Usage

1. Hold **Ctrl + Super** (Windows key) while speaking
2. Release the keys when done
3. Your transcribed text will be automatically pasted

## Configuration

Settings are stored in `config.json`:

- `api_key`: Your Groq API key
- `model`: Whisper model (default: `whisper-large-v3-turbo`)
- `language`: Transcription language (default: `en`)
- `hotkey_modifiers`: Modifier keys to hold (default: `["ctrl", "super"]`)
- `audio_device`: Audio input device ID (default: system default)
- `remove_fillers`: Remove filler words like "um", "uh" (default: `true`)

## Cost

Using Groq's Whisper API costs approximately $0.04/hour of audio - significantly cheaper than alternatives.

## Troubleshooting

### "Failed to start hotkey listener"

- **Pop!_OS / Wayland**: Make sure you're in the `input` group and have logged out/in
- **X11**: Make sure `pynput` can access the display

### "Failed to paste text"

- **Pop!_OS / Wayland**: Install `wl-clipboard` and `dotool` (or `ydotool`)
- **X11**: Install `xdotool` and `xclip`

### No audio input

- Check that `libportaudio2` is installed
- Try selecting a specific microphone in Settings

## Contributing

This is a personal/community project. Contributions are welcome, but please note that Pop!_OS + Wayland will remain the primary focus. Issues and PRs for other configurations may not be prioritized.

## License

MIT
