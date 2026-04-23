"""Prompt registry — loads versioned YAML prompts from prompts/."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Prompt:
    """A versioned LLM prompt with metadata."""

    id: str
    version: int
    mode: str
    language: str
    description: str
    prompt: str
    updated_at: str
    source_path: Path


PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


def _parse_filename(path: Path) -> tuple[str, int] | None:
    """Parse '<id>.v<N>.yaml' into (id, version). Returns None on non-match."""
    stem = path.stem  # e.g., "transcription_en.v1"
    if ".v" not in stem:
        return None
    id_part, _, v_part = stem.rpartition(".v")
    try:
        return id_part, int(v_part)
    except ValueError:
        return None


@lru_cache(maxsize=1)
def _load_all(prompts_dir: Path = PROMPTS_DIR) -> dict[str, Prompt]:
    """Load every prompt YAML in prompts_dir, keeping only the highest version per id."""
    latest: dict[str, Prompt] = {}

    if not prompts_dir.is_dir():
        return latest

    for path in sorted(prompts_dir.glob("*.yaml")):
        parsed = _parse_filename(path)
        if parsed is None:
            continue
        file_id, file_version = parsed

        with path.open() as f:
            data = yaml.safe_load(f) or {}

        # Manifest id/version should agree with filename — warn silently, prefer manifest.
        manifest_id = data.get("id", file_id)
        manifest_version = int(data.get("version", file_version))

        prompt = Prompt(
            id=manifest_id,
            version=manifest_version,
            mode=data.get("mode", ""),
            language=data.get("language", ""),
            description=data.get("description", "").strip(),
            prompt=data.get("prompt", "").strip(),
            updated_at=str(data.get("updated_at", "")),
            source_path=path,
        )

        existing = latest.get(manifest_id)
        if existing is None or prompt.version > existing.version:
            latest[manifest_id] = prompt

    return latest


def get(mode: str, language: str) -> Prompt:
    """Look up a prompt by (mode, language). Falls back to English if the language is missing.

    Raises KeyError if no matching prompt exists — caller decides whether that's fatal.
    """
    prompts = _load_all()

    # Exact match
    for p in prompts.values():
        if p.mode == mode and p.language == language:
            return p

    # Fallback to English for same mode
    for p in prompts.values():
        if p.mode == mode and p.language == "en":
            return p

    raise KeyError(f"No prompt found for mode={mode!r} language={language!r}")


def list_all() -> list[Prompt]:
    """Return all loaded prompts, sorted by (mode, language, version)."""
    prompts = _load_all()
    return sorted(prompts.values(), key=lambda p: (p.mode, p.language, p.version))


def reload() -> None:
    """Clear the cache — useful for tests and eval runs that modify prompts on disk."""
    _load_all.cache_clear()
