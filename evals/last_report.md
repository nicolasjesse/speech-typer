# Eval Report

> **This is a placeholder.** Run `make eval` to populate with real numbers from your API keys.

- **Generated:** (not yet run)
- **Provider / model:** (will be set by `make eval`)
- **Golden set:** `evals/golden_set.yaml`
- **Cases:** 15

## What lives here

After `make eval` runs, this file will contain:

- **Summary table** — exact-match rate, similarity (mean/median), p50/p95 latency, total cost.
- **Per-tag breakdown** — e.g., `spoken_punctuation`, `portuguese`, `whisper_misdetect`, `prompt_mode`, `no_hallucination`. Useful for spotting regressions when a prompt change helps one category and hurts another.
- **Per-case table** — input, actual output, exact match ✅/⚠️/❌, similarity, latency.
- **Methodology notes** — exactly how each metric is computed.

## How to read it

| Metric | Good | Watch out |
|---|---|---|
| Exact match (transcription mode) | ≥ 80% | Drops usually mean punctuation/capitalization regressed |
| Similarity mean (prompt mode) | ≥ 0.85 | Many rephrases are valid, so exact-match is harsh here |
| Latency p95 | < 1500 ms | Spikes usually = rate limiting, retry |
| Cost per case | < $0.0001 | Spikes = model too verbose (prompt issue, not pricing) |

## Workflow

1. Edit a prompt in `prompts/`.
2. Run `make eval` — this overwrites `last_report.md`.
3. `git diff evals/last_report.md` shows exactly which cases improved or regressed.
4. Commit prompt + new `last_report.md` together.
