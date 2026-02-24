"""Recording indicator overlay."""

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen


class RecordingOverlay(QWidget):
    """Floating overlay showing recording status."""

    def __init__(self):
        super().__init__()
        self._pulse_timer = QTimer()
        self._pulse_state = 0
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the overlay UI."""
        # Window flags for floating overlay - avoid stealing focus
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus |
            Qt.BypassWindowManagerHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)

        # Size and position
        self.setFixedSize(120, 40)
        self._position_window()

        # Label
        self._label = QLabel("Recording", self)
        self._label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        self._label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 5, 10, 5)
        layout.addWidget(self._label)

        # Pulse animation timer
        self._pulse_timer.timeout.connect(self._pulse)
        self._pulse_timer.setInterval(500)

    def _position_window(self) -> None:
        """Position overlay in top-right corner."""
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            x = geometry.right() - self.width() - 20
            y = geometry.top() + 20
            self.move(x, y)

    def paintEvent(self, event) -> None:
        """Draw the overlay background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background
        painter.setBrush(QBrush(QColor(40, 40, 40, 220)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 8, 8)

        # Recording indicator (pulsing red dot)
        pulse_alpha = 255 if self._pulse_state % 2 == 0 else 150
        indicator_color = QColor(220, 50, 50, pulse_alpha)
        painter.setBrush(QBrush(indicator_color))
        painter.drawEllipse(10, 12, 16, 16)

    def show_recording(self) -> None:
        """Show the overlay and start pulsing."""
        self._label.setText("Recording")
        self._pulse_state = 0
        self._pulse_timer.start()
        self.show()

    def show_transcribing(self) -> None:
        """Show transcribing status."""
        self._label.setText("Transcribing...")
        self._pulse_timer.stop()
        self.update()
        self.show()

    def hide_overlay(self) -> None:
        """Hide the overlay."""
        self._pulse_timer.stop()
        self.hide()

    def _pulse(self) -> None:
        """Handle pulse animation."""
        self._pulse_state += 1
        self.update()
