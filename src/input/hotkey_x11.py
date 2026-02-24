"""X11 global hotkey handling using pynput."""

import threading
from typing import Callable, Optional, List, Set


class HotkeyX11:
    """Global hotkey listener for X11 using pynput."""

    def __init__(
        self,
        modifiers: List[str],
        on_press: Optional[Callable[[], None]] = None,
        on_release: Optional[Callable[[], None]] = None,
    ):
        """Initialize hotkey listener.

        Args:
            modifiers: List of modifier names (e.g., ["ctrl", "super"])
            on_press: Callback when all modifiers are pressed
            on_release: Callback when any modifier is released
        """
        self._modifiers = [m.lower() for m in modifiers]
        self._on_press = on_press
        self._on_release = on_release
        self._listener = None
        self._running = False
        self._pressed_modifiers: Set[str] = set()
        self._hotkey_active = False

    def _key_to_modifier(self, key) -> Optional[str]:
        """Convert a pynput key to our modifier name."""
        try:
            from pynput.keyboard import Key

            # Check for modifier keys
            if key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r):
                return "ctrl"
            elif key in (Key.cmd, Key.cmd_l, Key.cmd_r):
                return "super"
            elif key in (Key.alt, Key.alt_l, Key.alt_r, Key.alt_gr):
                return "alt"
            elif key in (Key.shift, Key.shift_l, Key.shift_r):
                return "shift"
        except Exception:
            pass
        return None

    def _check_hotkey_state(self) -> bool:
        """Check if all required modifiers are currently pressed."""
        return all(mod in self._pressed_modifiers for mod in self._modifiers)

    def start(self) -> bool:
        """Start listening for hotkey."""
        if self._running:
            return True

        try:
            from pynput import keyboard

            def on_press(key):
                try:
                    modifier = self._key_to_modifier(key)
                    if modifier and modifier in self._modifiers:
                        self._pressed_modifiers.add(modifier)

                        if self._check_hotkey_state() and not self._hotkey_active:
                            self._hotkey_active = True
                            if self._on_press:
                                self._on_press()
                except Exception as e:
                    print(f"Error in key press handler: {e}")

            def on_release(key):
                try:
                    modifier = self._key_to_modifier(key)
                    if modifier and modifier in self._modifiers:
                        self._pressed_modifiers.discard(modifier)

                        if not self._check_hotkey_state() and self._hotkey_active:
                            self._hotkey_active = False
                            if self._on_release:
                                self._on_release()
                except Exception as e:
                    print(f"Error in key release handler: {e}")

            self._listener = keyboard.Listener(
                on_press=on_press,
                on_release=on_release,
            )
            self._listener.start()
            self._running = True
            return True

        except ImportError:
            print("Error: pynput not installed")
            return False
        except Exception as e:
            print(f"Error starting X11 hotkey listener: {e}")
            return False

    def stop(self) -> None:
        """Stop listening for hotkey."""
        if self._listener:
            self._listener.stop()
            self._listener = None
        self._running = False
        self._pressed_modifiers.clear()
        self._hotkey_active = False

    def set_modifiers(self, modifiers: List[str]) -> None:
        """Change the hotkey modifiers."""
        was_running = self._running
        if was_running:
            self.stop()

        self._modifiers = [m.lower() for m in modifiers]

        if was_running:
            self.start()

    @property
    def is_running(self) -> bool:
        """Check if listener is running."""
        return self._running

    @property
    def is_pressed(self) -> bool:
        """Check if hotkey is currently pressed."""
        return self._hotkey_active
