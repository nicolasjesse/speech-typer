# Evaluation

Holler ships an evaluation harness for its LLM **correction** step. It runs a labeled golden set through the current `TextCorrector` configuration and reports exact-match rate, similarity, latency, and cost per case and in aggregate.

> The Whisper transcription step is **not** evaluated here — that would need a labeled audio corpus and domain-specific WER methodology, which is out of scope. The correction layer is the part that prompt engineering, bilingual logic, and guardrails actually live in, so that's what we regression-test.

## Running

```bash
make eval                                # uses config.json API keys
python evals/run.py --provider groq      # switch provider
python evals/run.py --model gpt-4o       # override model
python evals/run.py --cases en_basic_filler,en_spoken_qmark
```

Each run writes:

- `evals/last_report.md` — the full markdown report (commit this after prompt changes)
- `evals/last_report.json` — machine-readable form for CI comparison

## Golden set

Defined in [`golden_set.yaml`](golden_set.yaml). Each case has:

```yaml
- id: en_spoken_qmark       # unique, referenced by --cases
  mode: transcription       # transcription | prompt
  language: en              # en | pt
  tags: [spoken_punctuation, questions]
  input: "how are you today question mark"
  expected: "How are you today?"
```

**Growing the set:** when a real-world bug escapes, add a case that reproduces it. The set deliberately stays small and representative rather than large and benchmark-like.

## Metrics

| Metric | Meaning |
|---|---|
| `exact_match` | `output.strip() == expected.strip()` (case-sensitive) |
| `similarity` | `difflib.SequenceMatcher.ratio()` on lowercase + whitespace-normalized strings, range [0, 1] |
| `latency_ms` | Wall-clock for the correction call |
| `cost_usd` | Estimated from returned token counts × rate table in `src/core/metrics.py` |

Report aggregates: exact-match rate, mean/median similarity, p50/p95 latency, total cost, per-tag breakdown.

## Interpretation

- **>90% exact match** is realistic for simple literal-transcription cases. Prompt-mode cases (rephrasing) will sit lower because many rephrases are valid — look at `similarity` instead.
- **`similarity < 0.8`** on a case that used to pass is a regression. Investigate before merging a prompt change.
- **Latency p95 > 1.5s** on `gpt-4o-mini` usually means rate limiting; re-run.
- Cost per case should be **<$0.0001** for short dictation snippets. Large jumps indicate the model is being too verbose (prompt issue, not pricing issue).

## Prompt-change workflow

1. Bump the prompt: edit `prompts/<id>.v<N>.yaml` or create `prompts/<id>.v<N+1>.yaml`.
2. Run `make eval`.
3. Compare `last_report.md` against the committed previous version — look for tags that regressed.
4. If exact-match drops on a tag, either fix the prompt or update the golden set (if the old expected was wrong).
5. Commit both the prompt change and `last_report.md` in the same PR.

## Why not use `lm-eval-harness` / `promptfoo` / etc.?

- This codebase is small. Pulling in a full eval framework would dwarf the app.
- The things we care about (exact spoken-punctuation behavior, bilingual translate-back) don't map cleanly to MMLU-style frameworks.
- Pure-stdlib + a YAML golden set keeps the barrier to adding cases near zero.

If the repo ever grows to need structured eval infra, `promptfoo` would be the first tool I'd reach for.
