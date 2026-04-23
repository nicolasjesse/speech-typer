#!/usr/bin/env python3
"""Run Holler's LLM correction layer against the golden set and write a report.

What this evaluates
-------------------
The LLM **correction** step only (raw_transcript → corrected_text). Whisper
transcription is not evaluated here — that would need a labeled audio corpus
and domain-specific WER methodology, which is a separate effort.

Why correction is the interesting target
---------------------------------------
Whisper accuracy is largely a function of the model size you pick. The
correction layer is where *our* engineering lives: prompt design, spoken-
punctuation handling, bilingual translate-back, guardrails against LLM
hallucinations. Regressions here are subtle and silent without a harness.

Metrics reported
----------------
- **exact_match**: correction output == expected output
- **similarity**: difflib.SequenceMatcher ratio in [0, 1] (LCS-based)
- **latency_ms**: wall-clock for the correction call
- **cost_usd**: estimated from token counts
- Aggregated: exact-match rate, mean/median similarity, p50/p95 latency,
  total cost, per-tag breakdown

Usage
-----
    python evals/run.py                          # uses config.json API keys
    python evals/run.py --model gpt-4o-mini
    python evals/run.py --provider groq
    python evals/run.py --cases en_basic_filler,en_spoken_qmark
    python evals/run.py --output evals/last_report.md

Requires a Groq or OpenAI API key via config.json or --api-key.
"""

from __future__ import annotations

import argparse
import difflib
import json
import statistics
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO))

from src.core.config import Config  # noqa: E402
from src.core.metrics import estimate_chat_cost  # noqa: E402
from src.text.corrector import TextCorrector  # noqa: E402


@dataclass
class CaseResult:
    id: str
    mode: str
    language: str
    tags: list
    input: str
    expected: str
    actual: str
    exact_match: bool
    similarity: float
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    prompt_id: str
    prompt_version: int
    error: str | None = None


@dataclass
class Report:
    model: str
    provider: str
    timestamp: str
    cases: list = field(default_factory=list)
    exact_match_rate: float = 0.0
    similarity_mean: float = 0.0
    similarity_median: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    total_cost_usd: float = 0.0
    by_tag: dict = field(default_factory=dict)


def similarity(a: str, b: str) -> float:
    """difflib-based similarity in [0, 1]. Case/whitespace normalized."""
    na = " ".join(a.lower().split())
    nb = " ".join(b.lower().split())
    return difflib.SequenceMatcher(a=na, b=nb).ratio()


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(len(s) - 1, max(0, round(pct / 100.0 * (len(s) - 1))))
    return s[idx]


def run_case(corrector: TextCorrector, case: dict) -> CaseResult:
    corrector.set_mode(case["mode"])
    corrector.set_language(case["language"])

    result = corrector.correct(case["input"])

    sim = similarity(result.text, case["expected"])
    exact = result.text.strip() == case["expected"].strip()
    cost = estimate_chat_cost(result.model, result.prompt_tokens, result.completion_tokens)

    return CaseResult(
        id=case["id"],
        mode=case["mode"],
        language=case["language"],
        tags=case.get("tags", []),
        input=case["input"],
        expected=case["expected"],
        actual=result.text,
        exact_match=exact,
        similarity=round(sim, 4),
        latency_ms=round(result.latency_ms, 2),
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        cost_usd=cost,
        prompt_id=result.prompt_id,
        prompt_version=result.prompt_version,
        error=result.error,
    )


def aggregate(cases: list[CaseResult], provider: str, model: str) -> Report:
    rep = Report(
        model=model,
        provider=provider,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        cases=cases,
    )
    scored = [c for c in cases if c.error is None]
    if not scored:
        return rep

    rep.exact_match_rate = round(sum(c.exact_match for c in scored) / len(scored), 4)
    sims = [c.similarity for c in scored]
    rep.similarity_mean = round(statistics.mean(sims), 4)
    rep.similarity_median = round(statistics.median(sims), 4)
    lats = [c.latency_ms for c in scored]
    rep.latency_p50_ms = round(percentile(lats, 50), 2)
    rep.latency_p95_ms = round(percentile(lats, 95), 2)
    rep.total_cost_usd = round(sum(c.cost_usd for c in scored), 6)

    # Tag breakdown
    by_tag: dict[str, dict] = defaultdict(lambda: {"n": 0, "exact": 0, "sim_sum": 0.0})
    for c in scored:
        for tag in c.tags:
            by_tag[tag]["n"] += 1
            by_tag[tag]["exact"] += 1 if c.exact_match else 0
            by_tag[tag]["sim_sum"] += c.similarity
    rep.by_tag = {
        tag: {
            "n": info["n"],
            "exact_match_rate": round(info["exact"] / info["n"], 4),
            "similarity_mean": round(info["sim_sum"] / info["n"], 4),
        }
        for tag, info in by_tag.items()
    }
    return rep


def render_markdown(report: Report, golden_path: Path) -> str:
    lines = []
    lines.append("# Eval Report")
    lines.append("")
    lines.append(f"- **Generated:** {report.timestamp}")
    lines.append(f"- **Provider / model:** `{report.provider}` / `{report.model}`")
    lines.append(f"- **Golden set:** `{golden_path.relative_to(REPO)}`")
    lines.append(f"- **Cases:** {len(report.cases)}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Exact match rate | **{report.exact_match_rate * 100:.1f}%** |")
    lines.append(f"| Similarity (mean) | {report.similarity_mean:.3f} |")
    lines.append(f"| Similarity (median) | {report.similarity_median:.3f} |")
    lines.append(f"| Latency p50 | {report.latency_p50_ms:.0f} ms |")
    lines.append(f"| Latency p95 | {report.latency_p95_ms:.0f} ms |")
    lines.append(f"| Total cost | ${report.total_cost_usd:.6f} |")
    lines.append("")

    if report.by_tag:
        lines.append("## By tag")
        lines.append("")
        lines.append("| Tag | N | Exact | Similarity |")
        lines.append("|---|---|---|---|")
        for tag, info in sorted(report.by_tag.items()):
            lines.append(
                f"| `{tag}` | {info['n']} | "
                f"{info['exact_match_rate'] * 100:.0f}% | "
                f"{info['similarity_mean']:.3f} |"
            )
        lines.append("")

    lines.append("## Per-case results")
    lines.append("")
    lines.append("| ID | Mode | Lang | Exact | Sim | Latency | Input → Actual |")
    lines.append("|---|---|---|---|---|---|---|")
    for c in report.cases:
        mark = "✅" if c.exact_match else ("⚠️" if c.similarity >= 0.8 else "❌")
        lat = f"{c.latency_ms:.0f}ms" if c.error is None else "—"
        detail = f"`{c.input}` → `{c.actual}`"
        if c.error:
            detail = f"`{c.input}` → **ERROR:** {c.error}"
        lines.append(
            f"| `{c.id}` | {c.mode} | {c.language} | {mark} | "
            f"{c.similarity:.2f} | {lat} | {detail} |"
        )
    lines.append("")
    lines.append("## Methodology")
    lines.append("")
    lines.append(
        "- **exact_match** is case-sensitive and whitespace-sensitive equality of "
        "the stripped output with `expected`."
    )
    lines.append(
        "- **similarity** is `difflib.SequenceMatcher.ratio()` on "
        "lowercase + whitespace-normalized strings."
    )
    lines.append(
        "- The correction-level sanity check (reject outputs that differ in "
        "length by >2× or <0.3×) can cause the pipeline to fall back to the "
        "raw input; such cases will show low similarity here."
    )
    lines.append(
        "- Cost estimates are derived from token counts returned by the "
        "provider and the rate table in `src/core/metrics.py`."
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden", type=Path, default=HERE / "golden_set.yaml")
    ap.add_argument("--output", type=Path, default=HERE / "last_report.md")
    ap.add_argument("--json", type=Path, default=HERE / "last_report.json")
    ap.add_argument("--provider", choices=["openai", "groq"], default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument(
        "--cases",
        default=None,
        help="Comma-separated case IDs to run (default: all)",
    )
    ap.add_argument("--api-key", default=None, help="Override API key (otherwise uses config.json)")
    args = ap.parse_args()

    if not args.golden.exists():
        print(f"Golden set not found: {args.golden}", file=sys.stderr)
        return 1

    with args.golden.open() as f:
        data = yaml.safe_load(f)
    cases = data.get("cases", []) or []
    if args.cases:
        wanted = set(args.cases.split(","))
        cases = [c for c in cases if c["id"] in wanted]
    if not cases:
        print("No cases selected.", file=sys.stderr)
        return 1

    config = Config.load()
    provider = args.provider or config.correction_provider or "openai"
    api_key = args.api_key or (config.openai_api_key if provider == "openai" else config.api_key)
    if not api_key:
        print(
            f"No API key for provider '{provider}'. Set one in config.json or pass --api-key.",
            file=sys.stderr,
        )
        return 1

    corrector = TextCorrector(
        api_key=api_key,
        provider=provider,
        model=args.model,
    )
    model_used = args.model or (
        "gpt-4o-mini" if provider == "openai" else "llama-3.3-70b-versatile"
    )

    print(
        f"Running {len(cases)} case(s) on provider={provider} model={model_used}...",
        file=sys.stderr,
    )
    results = []
    for i, case in enumerate(cases, 1):
        print(f"  [{i}/{len(cases)}] {case['id']}...", end=" ", file=sys.stderr)
        r = run_case(corrector, case)
        mark = "OK" if r.exact_match else f"sim={r.similarity:.2f}"
        print(mark, file=sys.stderr)
        results.append(r)

    report = aggregate(results, provider=provider, model=model_used)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_markdown(report, args.golden))
    args.json.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False))

    print(
        f"\nWrote {args.output.relative_to(REPO)} and {args.json.relative_to(REPO)}",
        file=sys.stderr,
    )
    print(f"Exact match: {report.exact_match_rate * 100:.1f}%")
    print(f"Similarity:  mean {report.similarity_mean:.3f}  median {report.similarity_median:.3f}")
    print(f"Latency:     p50 {report.latency_p50_ms:.0f}ms  p95 {report.latency_p95_ms:.0f}ms")
    print(f"Cost:        ${report.total_cost_usd:.6f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
