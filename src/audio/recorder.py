"""Audio recording using sounddevice."""

import io
import wave
import threading
from typing import Optional, Callable
import numpy as np


class AudioRecorder:
    """Records audio from microphone to WAV format."""

    SAMPLE_RATE = 16000  # Whisper requirement
    CHANNELS = 1  # Mono
    DTYPE = np.int16
    MAX_DURATION = 300  # 5 minutes max

    def __init__(self, device: Optional[int] = None):
        """Initialize recorder with optional device ID."""
        self._device = device
        self._recording = False
        self._audio_data: list[np.ndarray] = []
        self._stream = None
        self._lock = threading.Lock()

    @staticmethod
    def list_devices() -> list[dict]:
        """List available audio input devices."""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            input_devices = []

            for i, device in enumerate(devices):
                if device["max_input_channels"] > 0:
                    input_devices.append({
                        "id": i,
                        "name": device["name"],
                        "channels": device["max_input_channels"],
                        "default": device.get("default_samplerate", 0),
                    })

            return input_devices
        except Exception as e:
            print(f"Error listing devices: {e}")
            return []

    def start(self) -> bool:
        """Start recording audio."""
        try:
            import sounddevice as sd
        except ImportError:
            print("Error: sounddevice not installed")
            return False

        with self._lock:
            if self._recording:
                return False

            self._audio_data = []
            self._recording = True

        try:
            self._stream = sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                channels=self.CHANNELS,
                dtype=self.DTYPE,
                device=self._device,
                callback=self._audio_callback,
            )
            self._stream.start()
            return True
        except Exception as e:
            print(f"Error starting recording: {e}")
            self._recording = False
            return False

    def stop(self) -> Optional[bytes]:
        """Stop recording and return WAV data."""
        with self._lock:
            if not self._recording:
                return None
            self._recording = False

        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                print(f"Error stopping stream: {e}")
            self._stream = None

        return self._get_wav_data()

    def _audio_callback(self, indata: np.ndarray, frames: int, time, status) -> None:
        """Callback for audio stream."""
        if status:
            print(f"Audio status: {status}")

        with self._lock:
            if self._recording:
                # Check duration limit
                total_samples = sum(len(chunk) for chunk in self._audio_data)
                max_samples = self.MAX_DURATION * self.SAMPLE_RATE

                if total_samples < max_samples:
                    self._audio_data.append(indata.copy())

    def _get_wav_data(self) -> Optional[bytes]:
        """Convert recorded audio to WAV bytes."""
        if not self._audio_data:
            return None

        # Concatenate all audio chunks
        audio = np.concatenate(self._audio_data, axis=0)

        # Convert to WAV bytes
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(self.CHANNELS)
            wav.setsampwidth(2)  # 16-bit = 2 bytes
            wav.setframerate(self.SAMPLE_RATE)
            wav.writeframes(audio.tobytes())

        return buffer.getvalue()

    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        with self._lock:
            return self._recording

    @property
    def duration(self) -> float:
        """Get current recording duration in seconds."""
        with self._lock:
            total_samples = sum(len(chunk) for chunk in self._audio_data)
            return total_samples / self.SAMPLE_RATE

    def set_device(self, device_id: Optional[int]) -> None:
        """Set the recording device."""
        self._device = device_id
