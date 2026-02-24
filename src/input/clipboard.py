"""Clipboard operations for X11 and Wayland."""

import subprocess
from typing import Optional

from ..core.session import Session, SessionType


class Clipboard:
    """Cross-platform clipboard operations."""

    def __init__(self, session: Session):
        """Initialize clipboard with session info."""
        self._session = session

    def copy(self, text: str) -> bool:
        """Copy text to clipboard."""
        if self._session.is_wayland:
            return self._copy_wayland(text)
        else:
            return self._copy_x11(text)

    def paste(self) -> Optional[str]:
        """Get text from clipboard."""
        if self._session.is_wayland:
            return self._paste_wayland()
        else:
            return self._paste_x11()

    def _copy_x11(self, text: str) -> bool:
        """Copy to X11 clipboard using xclip."""
        try:
            proc = subprocess.run(
                ["xclip", "-selection", "clipboard"],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=5,
            )
            return proc.returncode == 0
        except FileNotFoundError:
            print("Error: xclip not installed")
            return False
        except subprocess.TimeoutExpired:
            print("Error: xclip timed out")
            return False
        except Exception as e:
            print(f"Error copying to clipboard: {e}")
            return False

    def _copy_wayland(self, text: str) -> bool:
        """Copy to Wayland clipboard using wl-copy."""
        try:
            proc = subprocess.Popen(
                ["wl-copy"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            proc.communicate(input=text.encode("utf-8"), timeout=2)
            return proc.returncode == 0
        except FileNotFoundError:
            print("Error: wl-copy not installed")
            return False
        except subprocess.TimeoutExpired:
            proc.kill()
            print("Error: wl-copy timed out")
            return False
        except Exception as e:
            print(f"Error copying to clipboard: {e}")
            return False

    def _paste_x11(self) -> Optional[str]:
        """Get from X11 clipboard using xclip."""
        try:
            proc = subprocess.run(
                ["xclip", "-selection", "clipboard", "-o"],
                capture_output=True,
                timeout=5,
            )
            if proc.returncode == 0:
                return proc.stdout.decode("utf-8")
            return None
        except Exception:
            return None

    def _paste_wayland(self) -> Optional[str]:
        """Get from Wayland clipboard using wl-paste."""
        try:
            proc = subprocess.run(
                ["wl-paste"],
                capture_output=True,
                timeout=5,
            )
            if proc.returncode == 0:
                return proc.stdout.decode("utf-8")
            return None
        except Exception:
            return None
