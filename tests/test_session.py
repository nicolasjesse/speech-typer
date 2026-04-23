"""Unit tests for session detection (X11 vs Wayland, desktop environments)."""

from __future__ import annotations

from src.core.session import DesktopEnvironment, Session, SessionType


def _reset_env(monkeypatch):
    for var in (
        "XDG_SESSION_TYPE",
        "WAYLAND_DISPLAY",
        "DISPLAY",
        "XDG_CURRENT_DESKTOP",
        "DESKTOP_SESSION",
    ):
        monkeypatch.delenv(var, raising=False)


def test_detects_wayland_from_xdg(monkeypatch):
    _reset_env(monkeypatch)
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    s = Session.detect()
    assert s.is_wayland is True
    assert s.is_x11 is False


def test_detects_x11_from_xdg(monkeypatch):
    _reset_env(monkeypatch)
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    s = Session.detect()
    assert s.is_x11 is True
    assert s.is_wayland is False


def test_wayland_fallback_via_wayland_display(monkeypatch):
    _reset_env(monkeypatch)
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    s = Session.detect()
    assert s.is_wayland is True


def test_detects_cosmic(monkeypatch):
    _reset_env(monkeypatch)
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "COSMIC")
    s = Session.detect()
    assert s.is_cosmic is True
    assert s.desktop_env == DesktopEnvironment.COSMIC


def test_detects_gnome(monkeypatch):
    _reset_env(monkeypatch)
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")
    s = Session.detect()
    assert s.desktop_env == DesktopEnvironment.GNOME
    assert s.is_cosmic is False


def test_unknown_session_when_nothing_set(monkeypatch):
    _reset_env(monkeypatch)
    s = Session.detect()
    assert s.session_type == SessionType.UNKNOWN
