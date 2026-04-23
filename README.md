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

## Engineering highlights

The pieces I'd want a reviewer to look at:

- **[`prompts/`](prompts/)** — versioned YAML prompts (`transcription_en.v1.yaml` etc.) loaded by a registry in [`src/text/prompts.py`](src/text/prompts.py). Prompts are artifacts, not inline strings.
- **[`evals/`](evals/)** — golden-set harness ([`evals/run.py`](evals/run.py)) that runs the correction layer against ~15 labeled cases and reports exact-match, similarity, latency, and cost per case with a per-tag breakdown. Re-run on every prompt change; diff [`evals/last_report.md`](evals/last_report.md) to see regressions.
- **[`src/core/metrics.py`](src/core/metrics.py)** — append-only JSONL telemetry for every request (tokens, latency, estimated cost, prompt version). Summarize with [`scripts/report.py`](scripts/report.py) — useful for verifying the "<$1/month" cost claim empirically.
- **[`src/text/corrector.py`](src/text/corrector.py)** — multi-provider LLM abstraction (Groq ↔ OpenAI) with guardrails: skip on empty/short input, length-based sanity check (reject outputs <0.3× or >2× the input), graceful fallback to raw transcription on any failure. Returns a structured `CorrectionResult` with observability fields.
- **[`src/core/session.py`](src/core/session.py)** — runtime detection of X11 / Wayland / COSMIC with the routing logic that picks `dotool` / `wtype` / `xdotool` accordingly. The original reason this project needed to exist.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full pipeline, threading model, and extension points. Quick version:

```
hotkey press → mic → Groq Whisper → filler removal → LLM correction → text injection
                       (timing + cost per request logged to metrics.jsonl)
```

## Quick start

```bash
git clone https://github.com/nicolasjesse/holler
cd holler
make install          # handles system deps, venv, dotool, desktop entry, optional service
make run              # or launch from your app menu
```

That's it. `make install` is interactive and will:

1. Detect your distro (apt / dnf / pacman) and install system packages
2. Build `dotool` from source if you're on Wayland and don't have it
3. Add you to the `input` group (Wayland hotkeys)
4. Create a venv and install Holler in editable mode
5. Copy `config.example.json` → `config.json`
6. Write a `.desktop` entry so Holler appears in your launcher
7. Optionally install a `systemd --user` service so it auto-starts on login

Flags: `./install.sh --yes` (non-interactive), `--no-service`, `--no-dotool`.

On first run without API keys, a settings dialog appears where you can paste your Groq key.

## Configuration reference

Edit `config.json` (or use the settings dialog):

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

## Evaluation

Holler's LLM correction layer has a regression test suite — see [`evals/`](evals/). Each run prints an exact-match rate, similarity score, p50/p95 latency, and total cost, plus a per-tag breakdown:

```bash
make eval                                   # uses your config.json API keys
python evals/run.py --provider groq         # or switch provider
python evals/run.py --cases en_spoken_qmark # or run one case
```

The golden set ([`evals/golden_set.yaml`](evals/golden_set.yaml)) covers spoken punctuation, bilingual translate-back, rephrase-vs-preserve fidelity, and guardrails against LLM hallucinations. Extend it whenever a real-world bug escapes — that's how the set stays useful instead of stale.

The last-run report is committed at [`evals/last_report.md`](evals/last_report.md), so prompt changes can be reviewed as a diff.

## Observability

Every dictation request appends one JSONL record to `$XDG_DATA_HOME/holler/metrics.jsonl` (default `~/.local/share/holler/metrics.jsonl`) with:

- timestamp, mode, language
- audio duration, transcription latency, transcription cost
- correction model + provider, correction latency, token counts, correction cost
- prompt id + version (so you can catch regressions after a prompt bump)
- `corrected` flag (did the LLM actually change the text?)

Summarize with:

```bash
make report              # last 30 days
make report-all          # full history
python scripts/report.py --days 7
```

Sample output:

```
Requests:           42
Total audio:        186.3s (3.11 min)
Total cost:         $0.003102
Avg cost/request:   $0.000074

Latency (total, p50 / p95 / p99):
  980ms / 1.32s / 1.58s
```

## Prompts

Prompts live in [`prompts/*.yaml`](prompts/) with a metadata header (id, version, mode, language, description, updated_at) plus the prompt body. The loader at [`src/text/prompts.py`](src/text/prompts.py) picks the highest version for each `(mode, language)` pair, so multiple versions can coexist during A/B testing. See [`prompts/README.md`](prompts/README.md) for the prompt-change workflow.

## Manual setup (power users)

<details>
<summary>Skip <code>make install</code> and do it yourself</summary>

**System packages:**

```bash
# Wayland (Pop!_OS / GNOME / KDE / Sway / Hyprland)
sudo apt install libportaudio2 wl-clipboard
# Plus dotool — see https://sr.ht/~geb/dotool/
sudo usermod -aG input $USER   # log out and back in

# X11
sudo apt install libportaudio2 xclip xdotool
```

**Python:**

```bash
python3 -m venv .env
source .env/bin/activate
pip install -e .            # or ".[dev]" for ruff/pytest
cp config.example.json config.json
python run.py               # or: holler
```

</details>

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
make dev         # install ruff + pytest into the venv
make lint        # ruff check + format check
make fix         # auto-apply safe ruff fixes + reformat
make test        # run pytest (46 tests, ~0.1s)
make run         # run Holler in the foreground
make eval        # run LLM correction evals against the golden set
make report      # summarize metrics.jsonl
make clean       # remove venv + caches
```

Run `make` with no arguments for the full target list.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the module layout and extension points.

## Uninstall

```bash
make uninstall          # removes venv, service, desktop entry
./uninstall.sh --purge  # also deletes config.json (erases API keys)
```

System packages (`libportaudio2`, `wl-clipboard`, `dotool`) and group memberships (`input`, `uinput`) are left alone — remove manually if you want a full cleanup.

## License

MIT — see [LICENSE](LICENSE).
