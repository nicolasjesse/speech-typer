"""Settings dialog."""

from typing import Callable, Optional, List
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QCheckBox, QPushButton,
    QMessageBox, QGroupBox
)
from PyQt5.QtCore import Qt

from ..core.config import Config
from ..audio.recorder import AudioRecorder


class SettingsDialog(QDialog):
    """Settings configuration dialog."""

    LANGUAGES = [
        ("Auto-detect", "auto"),
        ("English", "en"),
        ("Spanish", "es"),
        ("French", "fr"),
        ("German", "de"),
        ("Italian", "it"),
        ("Portuguese", "pt"),
        ("Dutch", "nl"),
        ("Polish", "pl"),
        ("Russian", "ru"),
        ("Japanese", "ja"),
        ("Korean", "ko"),
        ("Chinese", "zh"),
    ]

    def __init__(
        self,
        config: Config,
        on_save: Optional[Callable[[Config], None]] = None,
        parent=None
    ):
        super().__init__(parent)
        self._config = config
        self._on_save = on_save
        self._setup_ui()
        self._load_config()

    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        self.setWindowTitle("PontySpeech Settings")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # API Settings group
        api_group = QGroupBox("API Settings")
        api_layout = QFormLayout()

        self._api_key_input = QLineEdit()
        self._api_key_input.setEchoMode(QLineEdit.Password)
        self._api_key_input.setPlaceholderText("Enter your Groq API key")
        api_layout.addRow("API Key:", self._api_key_input)

        # Test button
        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self._test_connection)
        api_layout.addRow("", test_btn)

        api_group.setLayout(api_layout)
        layout.addWidget(api_group)

        # Audio Settings group
        audio_group = QGroupBox("Audio Settings")
        audio_layout = QFormLayout()

        self._device_combo = QComboBox()
        self._refresh_devices()
        audio_layout.addRow("Microphone:", self._device_combo)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_devices)
        audio_layout.addRow("", refresh_btn)

        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)

        # Transcription Settings group
        transcription_group = QGroupBox("Transcription Settings")
        transcription_layout = QFormLayout()

        self._language_combo = QComboBox()
        for name, code in self.LANGUAGES:
            self._language_combo.addItem(name, code)
        transcription_layout.addRow("Language:", self._language_combo)

        self._filler_checkbox = QCheckBox("Remove filler words (um, uh, like...)")
        transcription_layout.addRow("", self._filler_checkbox)

        transcription_group.setLayout(transcription_layout)
        layout.addWidget(transcription_group)

        # Hotkey info
        hotkey_label = QLabel(f"Hotkey: Hold {self._config.get_hotkey_name()} to record")
        hotkey_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(hotkey_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _load_config(self) -> None:
        """Load current config into UI."""
        self._api_key_input.setText(self._config.api_key)

        # Set language
        for i in range(self._language_combo.count()):
            if self._language_combo.itemData(i) == self._config.language:
                self._language_combo.setCurrentIndex(i)
                break

        # Set device
        if self._config.audio_device is not None:
            for i in range(self._device_combo.count()):
                if self._device_combo.itemData(i) == self._config.audio_device:
                    self._device_combo.setCurrentIndex(i)
                    break

        self._filler_checkbox.setChecked(self._config.remove_fillers)

    def _refresh_devices(self) -> None:
        """Refresh audio device list."""
        self._device_combo.clear()
        self._device_combo.addItem("Default", None)

        devices = AudioRecorder.list_devices()
        for device in devices:
            self._device_combo.addItem(device["name"], device["id"])

    def _test_connection(self) -> None:
        """Test the API connection."""
        api_key = self._api_key_input.text().strip()

        if not api_key:
            QMessageBox.warning(self, "Error", "Please enter an API key first.")
            return

        from ..transcription.groq_client import GroqTranscriber
        transcriber = GroqTranscriber(api_key)

        success, message = transcriber.test_connection()

        if success:
            QMessageBox.information(self, "Success", "API connection successful!")
        else:
            QMessageBox.warning(self, "Error", f"Connection failed: {message}")

    def _save(self) -> None:
        """Save settings."""
        api_key = self._api_key_input.text().strip()

        if not api_key:
            QMessageBox.warning(self, "Error", "API key is required.")
            return

        self._config.api_key = api_key
        self._config.language = self._language_combo.currentData()
        self._config.audio_device = self._device_combo.currentData()
        self._config.remove_fillers = self._filler_checkbox.isChecked()
        self._config.save()

        if self._on_save:
            self._on_save(self._config)

        self.accept()
