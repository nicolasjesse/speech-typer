"""Main application class."""

import sys
import threading
from typing import Optional

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

from .core.session import Session
from .core.config import Config
from .audio.recorder import AudioRecorder
from .transcription.groq_client import GroqTranscriber
from .text.formatter import TextFormatter
from .text.corrector import TextCorrector
from .input.injector import TextInjector
from .commands.command_handler import CommandHandler
from .ui.tray import SystemTray
from .ui.overlay import RecordingOverlay
from .ui.settings import SettingsDialog


class SignalBridge(QObject):
    """Bridge for thread-safe Qt signals."""

    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    transcription_done = pyqtSignal(str)
    error = pyqtSignal(str)


class PontySpeechApp:
    """Main application orchestrating all components."""

    def __init__(self):
        # Initialize Qt application
        self._qt_app = QApplication(sys.argv)
        self._qt_app.setQuitOnLastWindowClosed(False)

        # Load configuration
        self._config = Config.load()

        # Detect session type
        self._session = Session.detect()
        print(f"Detected session: {self._session}")

        # Check dependencies
        self._check_dependencies()

        # Initialize components
        self._recorder = AudioRecorder(self._config.audio_device)
        self._transcriber = GroqTranscriber(
            self._config.api_key,
            self._config.model,
            self._config.language,
        )
        self._formatter = TextFormatter(self._config.remove_fillers)

        # Use OpenAI or Groq for LLM correction
        correction_api_key = (
            self._config.openai_api_key
            if self._config.correction_provider == "openai"
            else self._config.api_key
        )
        self._corrector = TextCorrector(
            api_key=correction_api_key,
            provider=self._config.correction_provider,
            language=self._config.language,
        )

        self._injector = TextInjector(self._session)

        # Initialize voice command handler
        self._command_handler = CommandHandler(
            session=self._session,
            keyboard_commands=self._config.keyboard_commands,
            shell_commands=self._config.shell_commands,
            enabled=self._config.voice_commands_enabled,
        )

        # Initialize hotkey handler based on session
        self._hotkey = self._create_hotkey_handler()

        # Initialize UI
        self._tray = SystemTray(
            on_settings=self._show_settings,
            on_quit=self._quit,
            on_mode_change=self._set_mode,
            on_language_change=self._set_language,
            on_reload=self._reload_config,
        )
        # Sync tray with config
        self._tray._language = self._config.language
        self._overlay = RecordingOverlay()

        # Signal bridge for thread-safe communication
        self._signals = SignalBridge()
        self._signals.recording_started.connect(self._on_recording_started)
        self._signals.recording_stopped.connect(self._on_recording_stopped)
        self._signals.transcription_done.connect(self._on_transcription_done)
        self._signals.error.connect(self._on_error)

        # Check if configured
        if not self._config.is_configured:
            QTimer.singleShot(500, self._show_settings)

    def _check_dependencies(self) -> None:
        """Check and warn about missing dependencies."""
        deps = self._session.check_dependencies()
        missing = [name for name, available in deps.items() if not available]

        if missing:
            print(f"Warning: Missing dependencies: {', '.join(missing)}")
            if self._session.is_wayland and "dotool" not in deps:
                print("For Wayland, install dotool: https://sr.ht/~geb/dotool/")

        if self._session.is_wayland and not self._session.check_input_group():
            print("Warning: User not in 'input' group (required for Wayland hotkeys)")
            print("Run: sudo usermod -aG input $USER")
            print("Then logout and login again.")

    def _create_hotkey_handler(self):
        """Create appropriate hotkey handler for session type."""
        if self._session.is_wayland:
            from .input.hotkey_evdev import HotkeyEvdev
            return HotkeyEvdev(
                self._config.hotkey_modifiers,
                on_press=self._on_hotkey_press,
                on_release=self._on_hotkey_release,
            )
        else:
            from .input.hotkey_x11 import HotkeyX11
            return HotkeyX11(
                self._config.hotkey_modifiers,
                on_press=self._on_hotkey_press,
                on_release=self._on_hotkey_release,
            )

    def run(self) -> int:
        """Run the application."""
        # Show tray icon
        self._tray.show()

        # Start hotkey listener
        if not self._hotkey.start():
            QMessageBox.critical(
                None,
                "Error",
                "Failed to start hotkey listener.\n"
                "Check permissions and try again.",
            )
            return 1

        print(f"PontySpeech started. Hold {self._config.get_hotkey_name()} to record.")

        # Run Qt event loop
        return self._qt_app.exec_()

    def _on_hotkey_press(self) -> None:
        """Handle hotkey press (start recording)."""
        self._signals.recording_started.emit()

    def _on_hotkey_release(self) -> None:
        """Handle hotkey release (stop recording)."""
        self._signals.recording_stopped.emit()

    def _on_recording_started(self) -> None:
        """Start recording audio."""
        if not self._config.is_configured:
            self._tray.show_message(
                "Not Configured",
                "Please configure your API key first.",
            )
            return

        if self._recorder.start():
            self._tray.set_status(SystemTray.Status.RECORDING)
            # Overlay disabled - steals focus on Wayland
            # self._overlay.show_recording()
        else:
            self._signals.error.emit("Failed to start recording")

    def _on_recording_stopped(self) -> None:
        """Stop recording and transcribe."""
        wav_data = self._recorder.stop()
        # Overlay disabled - steals focus on Wayland
        # self._overlay.show_transcribing()
        self._tray.set_status(SystemTray.Status.TRANSCRIBING)

        if wav_data and len(wav_data) > 1000:  # Minimum viable recording
            # Transcribe in background thread
            thread = threading.Thread(
                target=self._transcribe_async,
                args=(wav_data,),
                daemon=True,
            )
            thread.start()
        else:
            self._tray.set_status(SystemTray.Status.IDLE)

    def _transcribe_async(self, wav_data: bytes) -> None:
        """Transcribe audio in background thread."""
        try:
            result = self._transcriber.transcribe(wav_data)

            if result.success:
                # Format the text
                formatted = self._formatter.format(result.text)
                # Apply LLM correction for better quality
                corrected = self._corrector.correct(formatted)
                self._signals.transcription_done.emit(corrected)
            else:
                self._signals.error.emit(result.error or "Transcription failed")

        except Exception as e:
            self._signals.error.emit(str(e))

    def _on_transcription_done(self, text: str) -> None:
        """Handle completed transcription."""
        self._tray.set_status(SystemTray.Status.IDLE)

        if text:
            # Check for voice commands first
            result = self._command_handler.process(text)

            if result.is_command:
                # It was a command - show feedback if it failed
                if not result.executed and result.error:
                    self._tray.show_message("Command Error", result.error)
                return

            # Not a command - inject text into active window
            if not self._injector.inject(text):
                self._tray.show_message("Error", "Failed to paste text")

    def _on_error(self, message: str) -> None:
        """Handle errors."""
        self._tray.set_status(SystemTray.Status.ERROR)
        self._tray.show_message("Error", message)

        # Reset to idle after showing error
        QTimer.singleShot(3000, lambda: self._tray.set_status(SystemTray.Status.IDLE))

    def _set_mode(self, mode: str) -> None:
        """Set the processing mode."""
        self._corrector.set_mode(mode)

    def _set_language(self, language: str) -> None:
        """Set the transcription language."""
        self._transcriber.set_language(language)
        self._corrector.set_language(language)
        self._config.language = language
        self._config.save()

    def _show_settings(self) -> None:
        """Show settings dialog."""
        dialog = SettingsDialog(self._config, on_save=self._apply_settings)
        dialog.exec_()

    def _apply_settings(self, config: Config) -> None:
        """Apply updated settings."""
        self._transcriber.set_api_key(config.api_key)
        self._transcriber.set_language(config.language)
        self._recorder.set_device(config.audio_device)
        self._formatter.set_remove_fillers(config.remove_fillers)

    def _reload_config(self) -> None:
        """Reload configuration from disk and apply changes."""
        print("[PontySpeech] Reloading configuration...")

        # Reload config from disk
        self._config = Config.load()

        # Update transcriber
        self._transcriber.set_api_key(self._config.api_key)
        self._transcriber.set_language(self._config.language)

        # Update recorder
        self._recorder.set_device(self._config.audio_device)

        # Update formatter
        self._formatter.set_remove_fillers(self._config.remove_fillers)

        # Update corrector
        correction_api_key = (
            self._config.openai_api_key
            if self._config.correction_provider == "openai"
            else self._config.api_key
        )
        self._corrector.set_api_key(correction_api_key)
        self._corrector.set_provider(self._config.correction_provider)
        self._corrector.set_language(self._config.language)

        # Update voice command handler
        self._command_handler.set_enabled(self._config.voice_commands_enabled)
        self._command_handler.set_shell_commands(self._config.shell_commands)
        self._command_handler.set_keyboard_commands(self._config.keyboard_commands)

        # Update tray language display
        self._tray.set_language(self._config.language)

        # Show confirmation
        self._tray.show_message("Config Reloaded", "Configuration has been reloaded successfully.")
        print("[PontySpeech] Configuration reloaded.")

    def _quit(self) -> None:
        """Quit the application."""
        self._hotkey.stop()
        self._overlay.hide_overlay()
        self._tray.hide()
        self._qt_app.quit()
