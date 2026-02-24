"""Text injection into active window."""

import subprocess
import time
from typing import Optional

from ..core.session import Session, SessionType
from .clipboard import Clipboard


class TextInjector:
    """Injects text into the active window using clipboard + paste."""

    def __init__(self, session: Session):
        """Initialize injector with session info."""
        self._session = session
        self._clipboard = Clipboard(session)
        self._original_clipboard: Optional[str] = None

    def inject(self, text: str, restore_clipboard: bool = True) -> bool:
        """Inject text into active window."""
        if not text:
            return False

        # On Wayland, try direct typing first
        if self._session.is_wayland:
            # wtype is broken on COSMIC (returns success but types wrong keycodes),
            # so use dotool for direct typing on COSMIC
            if self._session.is_cosmic:
                if self._try_dotool_type(text):
                    return True
            else:
                if self._try_wtype(text):
                    return True

        # Fall back to clipboard method
        # Save current clipboard content
        if restore_clipboard:
            self._original_clipboard = self._clipboard.paste()

        # Copy text to clipboard
        if not self._clipboard.copy(text):
            return False

        # Small delay to ensure clipboard is updated
        time.sleep(0.05)

        # Simulate Ctrl+V
        success = self._simulate_paste()

        # Restore original clipboard after a delay
        if restore_clipboard and self._original_clipboard is not None:
            time.sleep(0.1)
            self._clipboard.copy(self._original_clipboard)

        return success

    def _try_wtype(self, text: str) -> bool:
        """Type text using wtype (Wayland)."""
        try:
            proc = subprocess.run(
                ["wtype", "--", text],
                capture_output=True,
                timeout=10,
            )
            return proc.returncode == 0
        except FileNotFoundError:
            return False
        except Exception as e:
            print(f"wtype failed: {e}")
            return False

    def _try_dotool_type(self, text: str) -> bool:
        """Type text directly using dotool."""
        try:
            proc = subprocess.run(
                ["dotool"],
                input=f"type {text}".encode("utf-8"),
                capture_output=True,
                timeout=10,
            )
            return proc.returncode == 0
        except FileNotFoundError:
            return False
        except Exception as e:
            print(f"dotool type failed: {e}")
            return False

    def _simulate_paste(self) -> bool:
        """Simulate Ctrl+V keystroke."""
        if self._session.is_wayland:
            return self._paste_wayland()
        else:
            return self._paste_x11()

    def _paste_x11(self) -> bool:
        """Simulate paste on X11 using xdotool."""
        try:
            proc = subprocess.run(
                ["xdotool", "key", "--clearmodifiers", "ctrl+v"],
                capture_output=True,
                timeout=5,
            )
            return proc.returncode == 0
        except FileNotFoundError:
            print("Error: xdotool not installed")
            return False
        except subprocess.TimeoutExpired:
            print("Error: xdotool timed out")
            return False
        except Exception as e:
            print(f"Error simulating paste: {e}")
            return False

    def _paste_wayland(self) -> bool:
        """Simulate paste on Wayland using dotool or ydotool."""
        # Try dotool first (preferred)
        if self._try_dotool():
            return True

        # Fall back to ydotool
        if self._try_ydotool():
            return True

        print("Error: Neither dotool nor ydotool available for Wayland")
        return False

    def _try_dotool(self) -> bool:
        """Try to paste using dotool."""
        try:
            proc = subprocess.run(
                ["dotool"],
                input=b"key ctrl+v\n",
                capture_output=True,
                timeout=5,
            )
            return proc.returncode == 0
        except FileNotFoundError:
            return False
        except Exception:
            return False

    def _try_ydotool(self) -> bool:
        """Try to paste using ydotool."""
        try:
            proc = subprocess.run(
                ["ydotool", "key", "29:1", "47:1", "47:0", "29:0"],  # Ctrl+V
                capture_output=True,
                timeout=5,
            )
            return proc.returncode == 0
        except FileNotFoundError:
            return False
        except Exception:
            return False

    def type_text(self, text: str) -> bool:
        """Type text directly (fallback for apps that block paste)."""
        if self._session.is_wayland:
            return self._type_wayland(text)
        else:
            return self._type_x11(text)

    def _type_x11(self, text: str) -> bool:
        """Type text on X11 using xdotool."""
        try:
            proc = subprocess.run(
                ["xdotool", "type", "--clearmodifiers", "--", text],
                capture_output=True,
                timeout=30,
            )
            return proc.returncode == 0
        except Exception as e:
            print(f"Error typing text: {e}")
            return False

    def _type_wayland(self, text: str) -> bool:
        """Type text on Wayland using dotool."""
        try:
            # dotool uses 'type' command
            proc = subprocess.run(
                ["dotool"],
                input=f"type {text}\n".encode("utf-8"),
                capture_output=True,
                timeout=30,
            )
            return proc.returncode == 0
        except Exception as e:
            print(f"Error typing text: {e}")
            return False
