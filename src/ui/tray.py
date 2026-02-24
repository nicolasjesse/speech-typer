"""System tray icon and menu."""

from typing import Callable, Optional
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QApplication
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush
from PyQt5.QtCore import Qt, QSize


class SystemTray:
    """System tray icon with menu."""

    class Status:
        IDLE = "idle"
        RECORDING = "recording"
        TRANSCRIBING = "transcribing"
        ERROR = "error"

    def __init__(
        self,
        on_settings: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
        on_mode_change: Optional[Callable[[str], None]] = None,
        on_language_change: Optional[Callable[[str], None]] = None,
        on_reload: Optional[Callable[[], None]] = None,
    ):
        """Initialize system tray."""
        self._on_settings = on_settings
        self._on_quit = on_quit
        self._on_mode_change = on_mode_change
        self._on_language_change = on_language_change
        self._on_reload = on_reload
        self._status = self.Status.IDLE
        self._mode = "prompt"
        self._language = "en"

        # Create tray icon
        self._tray = QSystemTrayIcon()
        self._tray.setIcon(self._create_icon(self.Status.IDLE))
        self._tray.setToolTip("PontySpeech - Voice Dictation")

        # Create menu
        self._menu = QMenu()
        self._setup_menu()
        self._tray.setContextMenu(self._menu)

        # Status action (not clickable, just shows status)
        self._status_action = self._menu.actions()[0]

    def _setup_menu(self) -> None:
        """Setup the tray menu."""
        # Status display
        status_action = QAction("Ready", self._menu)
        status_action.setEnabled(False)
        self._menu.addAction(status_action)

        self._menu.addSeparator()

        # Mode submenu
        mode_menu = QMenu("Mode", self._menu)

        self._prompt_action = QAction("Prompt ✨", mode_menu)
        self._prompt_action.setCheckable(True)
        self._prompt_action.setChecked(self._mode == "prompt")
        self._prompt_action.triggered.connect(lambda: self._set_mode_from_menu("prompt"))
        mode_menu.addAction(self._prompt_action)

        self._transcription_action = QAction("Transcription", mode_menu)
        self._transcription_action.setCheckable(True)
        self._transcription_action.setChecked(self._mode == "transcription")
        self._transcription_action.triggered.connect(lambda: self._set_mode_from_menu("transcription"))
        mode_menu.addAction(self._transcription_action)

        self._menu.addMenu(mode_menu)

        # Language submenu
        lang_menu = QMenu("Language", self._menu)

        self._lang_en_action = QAction("English", lang_menu)
        self._lang_en_action.setCheckable(True)
        self._lang_en_action.setChecked(self._language == "en")
        self._lang_en_action.triggered.connect(lambda: self._set_language_from_menu("en"))
        lang_menu.addAction(self._lang_en_action)

        self._lang_pt_action = QAction("Português", lang_menu)
        self._lang_pt_action.setCheckable(True)
        self._lang_pt_action.setChecked(self._language == "pt")
        self._lang_pt_action.triggered.connect(lambda: self._set_language_from_menu("pt"))
        lang_menu.addAction(self._lang_pt_action)

        self._lang_auto_action = QAction("Auto-detect", lang_menu)
        self._lang_auto_action.setCheckable(True)
        self._lang_auto_action.setChecked(self._language == "auto")
        self._lang_auto_action.triggered.connect(lambda: self._set_language_from_menu("auto"))
        lang_menu.addAction(self._lang_auto_action)

        self._menu.addMenu(lang_menu)

        self._menu.addSeparator()

        # Reload Config
        reload_action = QAction("Reload Config", self._menu)
        reload_action.triggered.connect(self._handle_reload)
        self._menu.addAction(reload_action)

        # Settings
        settings_action = QAction("Settings...", self._menu)
        settings_action.triggered.connect(self._handle_settings)
        self._menu.addAction(settings_action)

        # About
        about_action = QAction("About", self._menu)
        about_action.triggered.connect(self._handle_about)
        self._menu.addAction(about_action)

        self._menu.addSeparator()

        # Quit
        quit_action = QAction("Quit", self._menu)
        quit_action.triggered.connect(self._handle_quit)
        self._menu.addAction(quit_action)

    def _create_icon(self, status: str) -> QIcon:
        """Create a tray icon based on status."""
        size = 22
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Choose color based on status
        if status == self.Status.RECORDING:
            color = QColor(220, 50, 50)  # Red
        elif status == self.Status.TRANSCRIBING:
            color = QColor(50, 150, 220)  # Blue
        elif status == self.Status.ERROR:
            color = QColor(220, 150, 50)  # Orange
        else:
            color = QColor(100, 100, 100)  # Gray

        # Draw microphone icon (simplified)
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)

        # Microphone head
        painter.drawRoundedRect(7, 2, 8, 12, 3, 3)

        # Microphone base
        painter.drawRect(9, 14, 4, 2)
        painter.drawRect(6, 16, 10, 2)

        # Add recording indicator (pulsing dot would be animated in practice)
        if status == self.Status.RECORDING:
            painter.setBrush(QBrush(QColor(255, 100, 100)))
            painter.drawEllipse(16, 2, 5, 5)

        painter.end()
        return QIcon(pixmap)

    def show(self) -> None:
        """Show the tray icon."""
        self._tray.show()

    def hide(self) -> None:
        """Hide the tray icon."""
        self._tray.hide()

    def set_status(self, status: str) -> None:
        """Update the tray icon status."""
        self._status = status
        self._tray.setIcon(self._create_icon(status))

        # Update status text in menu
        status_texts = {
            self.Status.IDLE: "Ready",
            self.Status.RECORDING: "Recording...",
            self.Status.TRANSCRIBING: "Transcribing...",
            self.Status.ERROR: "Error",
        }
        self._status_action.setText(status_texts.get(status, "Unknown"))

        # Update tooltip
        tooltips = {
            self.Status.IDLE: "PontySpeech - Ready (Hold Ctrl+Super to record)",
            self.Status.RECORDING: "PontySpeech - Recording...",
            self.Status.TRANSCRIBING: "PontySpeech - Transcribing...",
            self.Status.ERROR: "PontySpeech - Error",
        }
        self._tray.setToolTip(tooltips.get(status, "PontySpeech"))

    def show_message(self, title: str, message: str, icon: int = QSystemTrayIcon.Information) -> None:
        """Show a notification message."""
        self._tray.showMessage(title, message, icon, 3000)

    def _handle_reload(self) -> None:
        """Handle reload config menu click."""
        if self._on_reload:
            self._on_reload()

    def _handle_settings(self) -> None:
        """Handle settings menu click."""
        if self._on_settings:
            self._on_settings()

    def _handle_about(self) -> None:
        """Handle about menu click."""
        self._tray.showMessage(
            "PontySpeech",
            "Voice dictation for Linux\n\nHold Ctrl + Super to record.\nRelease to transcribe and paste.",
            QSystemTrayIcon.Information,
            5000,
        )

    def _handle_quit(self) -> None:
        """Handle quit menu click."""
        if self._on_quit:
            self._on_quit()

    def _set_mode_from_menu(self, mode: str) -> None:
        """Handle mode selection from menu."""
        if self._on_mode_change:
            self._on_mode_change(mode)
        self.set_mode(mode)

    def _set_language_from_menu(self, language: str) -> None:
        """Handle language selection from menu."""
        if self._on_language_change:
            self._on_language_change(language)
        self.set_language(language)

    def set_language(self, language: str) -> None:
        """Update the language display in menu."""
        self._language = language

        # Rebuild menu to force update
        self._menu.clear()
        self._setup_menu()
        self._status_action = self._menu.actions()[0]

        # Show notification
        lang_names = {"en": "English", "pt": "Português", "auto": "Auto-detect"}
        msg = f"Language set to {lang_names.get(language, language)}"
        self._tray.showMessage("Language Changed", msg, QSystemTrayIcon.Information, 2000)

    def set_mode(self, mode: str) -> None:
        """Update the mode display in menu."""
        self._mode = mode

        # Rebuild menu to force update (Linux DEs cache menus)
        self._menu.clear()
        self._setup_menu()
        self._status_action = self._menu.actions()[0]

        # Show notification
        if mode == "prompt":
            msg = "PROMPT mode - Speech will be transformed into better prompts"
        else:
            msg = "TRANSCRIPTION mode - Speech will be transcribed as-is"

        self._tray.showMessage("Mode Changed", msg, QSystemTrayIcon.Information, 2000)
