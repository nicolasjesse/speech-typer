#!/usr/bin/env python3
"""Summarize the metrics JSONL produced by Holler.

Usage:
    python scripts/report.py                # last 30 days
    python scripts/report.py --days 7
    python scripts/report.py --all
    python scripts/report.py --path /custom/path/metrics.jsonl

Pure stdlib — no external deps.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add repo root to sys.path so we can import src.core.metrics
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from src.core.metrics import default_metrics_path  # noqa: E402


def percentile(values: list[float], pct: float) -> float:
    """Simple nearest-rank percentile (no numpy)."""
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(len(s) - 1, max(0, round(pct / 100.0 * (len(s) - 1))))
    return s[idx]


def load(path: Path) -> list[dict]:
    """Read all records from a JSONL file. Skips malformed lines."""
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def within_window(records: list[dict], days: int | None) -> list[dict]:
    """Filter to records within the last `days` days. None = all."""
    if days is None:
        return records
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    kept = []
    for r in records:
        ts = r.get("timestamp", "")
        try:
            dt = datetime.fromisoformat(ts)
        except ValueError:
            continue
        if dt >= cutoff:
            kept.append(r)
    return kept


def fmt_usd(x: float) -> str:
    """Format a dollar value with sensible precision."""
    if x == 0:
        return "$0"
    if x < 0.01:
        return f"${x:.6f}"
    return f"${x:.4f}"


def fmt_ms(x: float) -> str:
    if x >= 1000:
        return f"{x / 1000:.2f}s"
    return f"{x:.0f}ms"


def summary(records: list[dict]) -> None:
    if not records:
        print("No records in window.")
        return

    n = len(records)
    total_audio_s = sum(r.get("audio_duration_s", 0) or 0 for r in records)
    total_cost = sum(r.get("total_cost_usd", 0) or 0 for r in records)
    whisper_cost = sum(r.get("whisper_cost_usd", 0) or 0 for r in records)
    correction_cost = sum(r.get("correction_cost_usd", 0) or 0 for r in records)

    latencies = [r.get("total_ms", 0) or 0 for r in records]
    transc_ms = [r.get("transcription_ms", 0) or 0 for r in records if r.get("transcription_ms")]
    correct_ms = [r.get("correction_ms", 0) or 0 for r in records if r.get("correction_ms")]

    print(f"Requests:           {n}")
    print(f"Total audio:        {total_audio_s:.1f}s ({total_audio_s / 60:.2f} min)")
    print(f"Total cost:         {fmt_usd(total_cost)}")
    print(f"  Whisper:          {fmt_usd(whisper_cost)}")
    print(f"  Correction:       {fmt_usd(correction_cost)}")
    print(f"Avg cost/request:   {fmt_usd(total_cost / n)}")
    print()
    print("Latency (total, p50 / p95 / p99):")
    print(
        f"  {fmt_ms(percentile(latencies, 50))} / "
        f"{fmt_ms(percentile(latencies, 95))} / "
        f"{fmt_ms(percentile(latencies, 99))}"
    )
    if transc_ms:
        print(
            f"  transcription: p50 {fmt_ms(percentile(transc_ms, 50))}  "
            f"p95 {fmt_ms(percentile(transc_ms, 95))}"
        )
    if correct_ms:
        print(
            f"  correction:    p50 {fmt_ms(percentile(correct_ms, 50))}  "
            f"p95 {fmt_ms(percentile(correct_ms, 95))}"
        )
    print()

    # By mode
    by_mode = Counter(r.get("mode", "") for r in records)
    print("By mode:")
    for mode, count in by_mode.most_common():
        print(f"  {mode or '(empty)':<20} {count}")
    print()

    # By language
    by_lang = Counter(r.get("language", "") for r in records)
    print("By language:")
    for lang, count in by_lang.most_common():
        print(f"  {lang or '(empty)':<20} {count}")
    print()

    # By model
    by_model = Counter(r.get("correction_model", "") for r in records if r.get("correction_model"))
    if by_model:
        print("By correction model:")
        for model, count in by_model.most_common():
            print(f"  {model:<30} {count}")
        print()

    # By prompt version (catches prompt regressions)
    by_prompt = Counter(
        (r.get("prompt_id", ""), r.get("prompt_version", 0)) for r in records if r.get("prompt_id")
    )
    if by_prompt:
        print("By prompt version:")
        for (pid, ver), count in by_prompt.most_common():
            print(f"  {pid:<25} v{ver:<3} {count}")
        print()

    # Daily breakdown (last 14 days for readability)
    daily: dict[str, dict] = defaultdict(lambda: {"count": 0, "cost": 0.0})
    for r in records:
        ts = r.get("timestamp", "")
        try:
            day = datetime.fromisoformat(ts).strftime("%Y-%m-%d")
        except ValueError:
            continue
        daily[day]["count"] += 1
        daily[day]["cost"] += r.get("total_cost_usd", 0) or 0

    if daily:
        print("Daily (last 14 shown):")
        for day in sorted(daily)[-14:]:
            print(f"  {day}  {daily[day]['count']:>4} req   {fmt_usd(daily[day]['cost'])}")
        print()

    # Error summary
    errors = [r for r in records if r.get("transcription_error") or r.get("correction_error")]
    if errors:
        print(f"Records with errors: {len(errors)} ({100 * len(errors) / n:.1f}%)")
        reasons = Counter(r.get("correction_error") or r.get("transcription_error") for r in errors)
        for reason, count in reasons.most_common(5):
            print(f"  {reason[:50]:<50} {count}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Summarize Holler metrics.jsonl")
    ap.add_argument(
        "--path",
        type=Path,
        default=None,
        help=f"Path to metrics.jsonl (default: {default_metrics_path()})",
    )
    window = ap.add_mutually_exclusive_group()
    window.add_argument("--days", type=int, default=30, help="Lookback window (default: 30)")
    window.add_argument("--all", action="store_true", help="Use all records")
    args = ap.parse_args()

    path = args.path or default_metrics_path()
    print(f"Source: {path}")
    if not path.exists():
        print("(No metrics file yet — run Holler to generate some.)")
        return 0

    records = load(path)
    print(f"Loaded {len(records)} record(s) from file.")

    windowed = within_window(records, None if args.all else args.days)
    if args.all:
        print("Window: all records")
    else:
        print(f"Window: last {args.days} day(s) — {len(windowed)} record(s)")
    print()
    summary(windowed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
