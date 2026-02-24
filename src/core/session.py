"""Session detection for X11 vs Wayland and desktop environment."""

import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SessionType(Enum):
    X11 = "x11"
    WAYLAND = "wayland"
    UNKNOWN = "unknown"


class DesktopEnvironment(Enum):
    GNOME = "gnome"
    KDE = "kde"
    SWAY = "sway"
    HYPRLAND = "hyprland"
    COSMIC = "cosmic"
    XFCE = "xfce"
    CINNAMON = "cinnamon"
    MATE = "mate"
    OTHER = "other"


@dataclass
class Session:
    """Represents the current desktop session."""

    session_type: SessionType
    desktop_env: DesktopEnvironment

    @classmethod
    def detect(cls) -> "Session":
        """Detect the current session type and desktop environment."""
        session_type = cls._detect_session_type()
        desktop_env = cls._detect_desktop_environment()
        return cls(session_type=session_type, desktop_env=desktop_env)

    @staticmethod
    def _detect_session_type() -> SessionType:
        """Detect X11 vs Wayland session."""
        xdg_session = os.environ.get("XDG_SESSION_TYPE", "").lower()

        if xdg_session == "wayland":
            return SessionType.WAYLAND
        elif xdg_session == "x11":
            return SessionType.X11

        # Fallback checks
        if os.environ.get("WAYLAND_DISPLAY"):
            return SessionType.WAYLAND
        if os.environ.get("DISPLAY"):
            return SessionType.X11

        return SessionType.UNKNOWN

    @staticmethod
    def _detect_desktop_environment() -> DesktopEnvironment:
        """Detect the desktop environment."""
        xdg_desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        desktop_session = os.environ.get("DESKTOP_SESSION", "").lower()

        # Check XDG_CURRENT_DESKTOP first
        if "cosmic" in xdg_desktop:
            return DesktopEnvironment.COSMIC
        elif "gnome" in xdg_desktop:
            return DesktopEnvironment.GNOME
        elif "kde" in xdg_desktop or "plasma" in xdg_desktop:
            return DesktopEnvironment.KDE
        elif "sway" in xdg_desktop:
            return DesktopEnvironment.SWAY
        elif "hyprland" in xdg_desktop:
            return DesktopEnvironment.HYPRLAND
        elif "xfce" in xdg_desktop:
            return DesktopEnvironment.XFCE
        elif "cinnamon" in xdg_desktop:
            return DesktopEnvironment.CINNAMON
        elif "mate" in xdg_desktop:
            return DesktopEnvironment.MATE

        # Fallback to DESKTOP_SESSION
        if "gnome" in desktop_session:
            return DesktopEnvironment.GNOME
        elif "plasma" in desktop_session or "kde" in desktop_session:
            return DesktopEnvironment.KDE

        return DesktopEnvironment.OTHER

    @property
    def is_wayland(self) -> bool:
        """Check if running under Wayland."""
        return self.session_type == SessionType.WAYLAND

    @property
    def is_x11(self) -> bool:
        """Check if running under X11."""
        return self.session_type == SessionType.X11

    @property
    def is_cosmic(self) -> bool:
        """Check if running under COSMIC desktop."""
        return self.desktop_env == DesktopEnvironment.COSMIC

    def check_dependencies(self) -> dict[str, bool]:
        """Check if required system dependencies are available."""
        deps = {}

        if self.is_x11:
            deps["xclip"] = self._command_exists("xclip")
            deps["xdotool"] = self._command_exists("xdotool")
        else:
            deps["wl-copy"] = self._command_exists("wl-copy")
            deps["wl-paste"] = self._command_exists("wl-paste")
            deps["dotool"] = self._command_exists("dotool")
            deps["ydotool"] = self._command_exists("ydotool")

        return deps

    def check_input_group(self) -> bool:
        """Check if user is in the input group (required for evdev on Wayland)."""
        try:
            result = subprocess.run(
                ["groups"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return "input" in result.stdout.split()
        except Exception:
            return False

    @staticmethod
    def _command_exists(command: str) -> bool:
        """Check if a command exists in PATH."""
        try:
            subprocess.run(
                ["which", command],
                capture_output=True,
                check=True,
                timeout=5
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False

    def __str__(self) -> str:
        return f"Session(type={self.session_type.value}, desktop={self.desktop_env.value})"
