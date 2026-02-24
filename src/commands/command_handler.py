"""Voice command detection and execution."""

import subprocess
import re
from dataclasses import dataclass
from typing import Optional, Dict, List

from ..core.session import Session


@dataclass
class CommandResult:
    """Result of command processing."""

    is_command: bool  # True if text was recognized as a command
    executed: bool  # True if command executed successfully
    error: Optional[str] = None  # Error message if execution failed
    remaining_text: Optional[str] = None  # Text to inject if not a command


# Default keyboard commands - maps spoken phrase to key name
DEFAULT_KEYBOARD_COMMANDS: Dict[str, str] = {
    "enter": "Return",
    "tab": "Tab",
    "escape": "Escape",
    "backspace": "BackSpace",
    "delete": "Delete",
    "space": "space",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "home": "Home",
    "end": "End",
    "page up": "Page_Up",
    "page down": "Page_Down",
}


class CommandHandler:
    """Handles voice command detection and execution."""

    def __init__(
        self,
        session: Session,
        keyboard_commands: Optional[Dict[str, str]] = None,
        shell_commands: Optional[Dict[str, str]] = None,
        enabled: bool = True,
    ):
        """Initialize command handler.

        Args:
            session: Session info for platform-specific execution
            keyboard_commands: Map of spoken phrase to key name (e.g., {"enter": "Return"})
            shell_commands: Map of spoken phrase to shell command (e.g., {"open browser": "xdg-open https://google.com"})
            enabled: Whether command detection is enabled
        """
        self._session = session
        self._enabled = enabled

        # Merge default keyboard commands with custom ones
        self._keyboard_commands = DEFAULT_KEYBOARD_COMMANDS.copy()
        if keyboard_commands:
            self._keyboard_commands.update(keyboard_commands)

        self._shell_commands = shell_commands or {}

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable command detection."""
        self._enabled = enabled

    def set_shell_commands(self, commands: Dict[str, str]) -> None:
        """Update shell commands configuration."""
        self._shell_commands = commands

    def set_keyboard_commands(self, commands: Dict[str, str]) -> None:
        """Update keyboard commands configuration (merges with defaults)."""
        self._keyboard_commands = DEFAULT_KEYBOARD_COMMANDS.copy()
        if commands:
            self._keyboard_commands.update(commands)

    def process(self, text: str) -> CommandResult:
        """Process transcribed text for commands.

        Returns CommandResult indicating if text was a command and execution status.
        If not a command, remaining_text contains the original text for injection.
        """
        if not self._enabled or not text:
            print(f"[VoiceCmd] Disabled or empty text, passing through: '{text}'")
            return CommandResult(
                is_command=False,
                executed=False,
                remaining_text=text,
            )

        # Normalize text for matching
        normalized = text.strip().lower()

        # Remove trailing punctuation for matching
        normalized_clean = re.sub(r'[.!?,;:]+$', '', normalized).strip()

        print(f"[VoiceCmd] Checking: '{normalized_clean}' (original: '{text}')")

        # Check keyboard commands first (exact match)
        if normalized_clean in self._keyboard_commands:
            key = self._keyboard_commands[normalized_clean]
            print(f"[VoiceCmd] Keyboard command detected: '{normalized_clean}' -> key '{key}'")
            success = self._press_key(key)
            print(f"[VoiceCmd] Key press {'succeeded' if success else 'FAILED'}")
            return CommandResult(
                is_command=True,
                executed=success,
                error=None if success else f"Failed to press key: {key}",
            )

        # Check shell commands (exact match)
        for phrase, command in self._shell_commands.items():
            if normalized_clean == phrase.lower():
                print(f"[VoiceCmd] Shell command detected: '{normalized_clean}' -> '{command}'")
                success, error = self._run_shell_command(command)
                print(f"[VoiceCmd] Shell command {'succeeded' if success else 'FAILED'}")
                return CommandResult(
                    is_command=True,
                    executed=success,
                    error=error,
                )

        # Not a command - return text for normal injection
        print(f"[VoiceCmd] No command match, will inject text: '{text}'")
        return CommandResult(
            is_command=False,
            executed=False,
            remaining_text=text,
        )

    def _press_key(self, key: str) -> bool:
        """Press a keyboard key."""
        if self._session.is_wayland:
            return self._press_key_wayland(key)
        else:
            return self._press_key_x11(key)

    def _press_key_x11(self, key: str) -> bool:
        """Press key on X11 using xdotool."""
        try:
            proc = subprocess.run(
                ["xdotool", "key", "--clearmodifiers", key],
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
            print(f"Error pressing key: {e}")
            return False

    def _press_key_wayland(self, key: str) -> bool:
        """Press key on Wayland using dotool or wtype."""
        # Try dotool first
        if self._try_dotool_key(key):
            return True

        # Try wtype as fallback
        if self._try_wtype_key(key):
            return True

        print("Error: Neither dotool nor wtype available for Wayland key press")
        return False

    def _try_dotool_key(self, key: str) -> bool:
        """Press key using dotool."""
        try:
            # Convert key name for dotool (uses different naming)
            dotool_key = self._convert_key_for_dotool(key)
            print(f"[VoiceCmd] Using dotool: key {dotool_key}")
            proc = subprocess.run(
                ["dotool"],
                input=f"key {dotool_key}\n".encode("utf-8"),
                capture_output=True,
                timeout=5,
            )
            if proc.stderr:
                print(f"[VoiceCmd] dotool stderr: {proc.stderr.decode()}")
            return proc.returncode == 0
        except FileNotFoundError:
            return False
        except Exception as e:
            print(f"[VoiceCmd] dotool error: {e}")
            return False

    def _try_wtype_key(self, key: str) -> bool:
        """Press key using wtype."""
        try:
            # wtype uses -k for key press
            wtype_key = self._convert_key_for_wtype(key)
            proc = subprocess.run(
                ["wtype", "-k", wtype_key],
                capture_output=True,
                timeout=5,
            )
            return proc.returncode == 0
        except FileNotFoundError:
            return False
        except Exception:
            return False

    def _convert_key_for_dotool(self, key: str) -> str:
        """Convert X11 key name to dotool format."""
        # dotool uses its own key names
        key_map = {
            "Return": "enter",
            "Tab": "tab",
            "Escape": "esc",
            "BackSpace": "backspace",
            "Delete": "delete",
            "space": "space",
            "Up": "up",
            "Down": "down",
            "Left": "left",
            "Right": "right",
            "Home": "home",
            "End": "end",
            "Page_Up": "pageup",
            "Page_Down": "pagedown",
        }
        return key_map.get(key, key.lower())

    def _convert_key_for_wtype(self, key: str) -> str:
        """Convert X11 key name to wtype format."""
        # wtype uses XKB key names
        key_map = {
            "Return": "Return",
            "Tab": "Tab",
            "Escape": "Escape",
            "BackSpace": "BackSpace",
            "Delete": "Delete",
            "space": "space",
            "Up": "Up",
            "Down": "Down",
            "Left": "Left",
            "Right": "Right",
            "Home": "Home",
            "End": "End",
            "Page_Up": "Prior",
            "Page_Down": "Next",
        }
        return key_map.get(key, key)

    def _run_shell_command(self, command: str) -> tuple[bool, Optional[str]]:
        """Run a shell command.

        Returns (success, error_message).
        """
        try:
            # Run command asynchronously (don't block on result)
            subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,  # Detach from parent process
            )
            return True, None
        except Exception as e:
            error = f"Failed to run command: {e}"
            print(error)
            return False, error

    def get_all_commands(self) -> Dict[str, Dict[str, str]]:
        """Get all configured commands for display."""
        return {
            "keyboard": self._keyboard_commands.copy(),
            "shell": self._shell_commands.copy(),
        }
