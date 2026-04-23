# Prompts

Versioned LLM prompts used by Holler's correction layer.

Each file is a YAML document with metadata + the prompt body. Filenames follow the pattern `{id}.v{version}.yaml`, and the highest version is loaded at runtime. This lets multiple versions coexist during A/B testing or gradual rollout.

## Schema

```yaml
id: transcription_en        # unique identifier, used by the loader
version: 1                  # integer — loader picks the highest
mode: transcription         # "transcription" or "prompt"
language: en                # ISO 639-1 code
updated_at: 2026-04-23
description: |              # human-readable purpose
  ...
prompt: |                   # actual system prompt sent to the LLM
  ...
```

## Current prompts

| ID | Mode | Language | Version |
|---|---|---|---|
| `transcription_en` | transcription | English | 1 |
| `transcription_pt` | transcription | Portuguese | 1 |
| `prompt_mode_en` | prompt | English | 1 |
| `prompt_mode_pt` | prompt | Portuguese | 1 |

## Evaluating changes

Before bumping the version, run the eval harness against the golden set:

```bash
make eval       # runs evals/run.py
```

The generated `evals/last_report.md` shows per-case pass/fail, exact-match rate, similarity scores, latency, and cost. Commit `last_report.md` alongside any prompt change so the diff is reviewable.

## Adding a new language

1. Copy `transcription_en.v1.yaml` → `transcription_XX.v1.yaml` with your language code.
2. Translate the prompt + examples.
3. Add cases to `evals/golden_set.yaml` tagged with the new language.
4. Run `make eval` and iterate on the prompt until `similarity_mean` crosses your bar.
