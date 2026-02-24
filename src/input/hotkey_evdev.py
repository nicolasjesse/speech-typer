"""Wayland global hotkey handling using evdev (requires input group)."""

import os
import threading
import select
from typing import Callable, Optional, List, Set


class HotkeyEvdev:
    """Global hotkey listener for Wayland using evdev at kernel level.

    Requires user to be in the 'input' group:
        sudo usermod -aG input $USER
    Then logout and login.
    """

    # Evdev key codes for modifiers
    KEY_CODES = {
        "ctrl": {29, 97},      # Left Ctrl, Right Ctrl
        "super": {125, 126},   # Left Super, Right Super
        "alt": {56, 100},      # Left Alt, Right Alt
        "shift": {42, 54},     # Left Shift, Right Shift
    }

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
        self._devices = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._pressed_keys: Set[int] = set()
        self._hotkey_active = False

        # Build set of all key codes we care about
        self._all_modifier_codes: Set[int] = set()
        for mod in self._modifiers:
            if mod in self.KEY_CODES:
                self._all_modifier_codes.update(self.KEY_CODES[mod])

    def _check_hotkey_state(self) -> bool:
        """Check if all required modifiers are currently pressed."""
        for mod in self._modifiers:
            codes = self.KEY_CODES.get(mod, set())
            # At least one key from this modifier group must be pressed
            if not (self._pressed_keys & codes):
                return False
        return True

    def _find_keyboards(self) -> list:
        """Find all keyboard input devices."""
        try:
            import evdev
        except ImportError:
            print("Error: evdev not installed")
            return []

        keyboards = []

        try:
            devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        except PermissionError:
            print("Error: Permission denied accessing input devices.")
            print("Add your user to the 'input' group:")
            print("  sudo usermod -aG input $USER")
            print("Then logout and login again.")
            return []
        except Exception as e:
            print(f"Error listing input devices: {e}")
            return []

        for device in devices:
            try:
                capabilities = device.capabilities()
                # Check if device has key events (EV_KEY = 1)
                if 1 in capabilities:
                    keys = capabilities[1]
                    # Check if it has typical keyboard keys
                    # KEY_A = 30, KEY_ENTER = 28
                    if 30 in keys or 28 in keys:
                        keyboards.append(device)
            except Exception:
                continue

        return keyboards

    def start(self) -> bool:
        """Start listening for hotkey."""
        if self._running:
            return True

        try:
            import evdev
        except ImportError:
            print("Error: evdev not installed. Run: pip install evdev")
            return False

        self._devices = self._find_keyboards()

        if not self._devices:
            print("No keyboard devices found. Check permissions.")
            return False

        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

        return True

    def _listen_loop(self) -> None:
        """Main event loop for listening to keyboard events."""
        try:
            import evdev
        except ImportError:
            return

        while self._running:
            try:
                # Use select to wait for events from any device
                readable, _, _ = select.select(self._devices, [], [], 0.1)

                for device in readable:
                    try:
                        for event in device.read():
                            if event.type == evdev.ecodes.EV_KEY:
                                self._handle_key_event(event)
                    except OSError:
                        # Device disconnected, try to reconnect
                        self._devices = self._find_keyboards()
                        break

            except Exception as e:
                if self._running:
                    print(f"Error in hotkey listener: {e}")

    def _handle_key_event(self, event) -> None:
        """Handle a key event."""
        # Only care about our modifier keys
        if event.code not in self._all_modifier_codes:
            return

        # event.value: 0 = release, 1 = press, 2 = repeat
        if event.value == 1:  # Press
            self._pressed_keys.add(event.code)
        elif event.value == 0:  # Release
            self._pressed_keys.discard(event.code)

        # Check if hotkey state changed
        hotkey_pressed = self._check_hotkey_state()

        if hotkey_pressed and not self._hotkey_active:
            # Hotkey just activated
            self._hotkey_active = True
            if self._on_press:
                try:
                    self._on_press()
                except Exception as e:
                    print(f"Error in press callback: {e}")

        elif not hotkey_pressed and self._hotkey_active:
            # Hotkey just deactivated
            self._hotkey_active = False
            if self._on_release:
                try:
                    self._on_release()
                except Exception as e:
                    print(f"Error in release callback: {e}")

    def stop(self) -> None:
        """Stop listening for hotkey."""
        self._running = False

        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

        for device in self._devices:
            try:
                device.close()
            except Exception:
                pass
        self._devices = []
        self._pressed_keys.clear()
        self._hotkey_active = False

    def set_modifiers(self, modifiers: List[str]) -> None:
        """Change the hotkey modifiers."""
        was_running = self._running
        if was_running:
            self.stop()

        self._modifiers = [m.lower() for m in modifiers]
        self._all_modifier_codes = set()
        for mod in self._modifiers:
            if mod in self.KEY_CODES:
                self._all_modifier_codes.update(self.KEY_CODES[mod])

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

    @staticmethod
    def check_permissions() -> tuple[bool, str]:
        """Check if user has permission to access input devices."""
        import subprocess

        # Check if in input group
        try:
            result = subprocess.run(
                ["groups"],
                capture_output=True,
                text=True,
                timeout=5
            )
            groups = result.stdout.split()

            if "input" not in groups:
                return False, (
                    "User not in 'input' group.\n"
                    "Run: sudo usermod -aG input $USER\n"
                    "Then logout and login again."
                )

        except Exception as e:
            return False, f"Could not check groups: {e}"

        # Check if /dev/input is accessible
        input_dir = "/dev/input"
        if not os.access(input_dir, os.R_OK):
            return False, f"Cannot read {input_dir}"

        return True, "Permissions OK"
