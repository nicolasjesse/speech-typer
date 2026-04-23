"""Shared pytest fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make `src.*` importable without installing the package
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def tmp_config_path(tmp_path) -> Path:
    """A writable tmp path for Config load/save round-trip tests."""
    return tmp_path / "config.json"
