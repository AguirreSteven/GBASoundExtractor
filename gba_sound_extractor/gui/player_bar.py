"""Playback controls, tag display, and export buttons."""

from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
                              QSlider, QLabel, QComboBox, QFrame)
from PyQt5.QtCore import pyqtSignal, Qt


class PlayerBar(QWidget):
    """Playback controls, progress slider, song info badges, and export buttons."""

    play_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    export_clicked = pyqtSignal()
    export_wav_clicked = pyqtSignal()
    export_all_clicked = pyqtSignal()
    loop_count_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 4, 8, 4)
        outer.setSpacing(4)

        # --- Row 1: song info badges ---
        self._info_frame = QFrame()
        info_layout = QHBoxLayout(self._info_frame)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(12)

        self._song_name_label = QLabel("")
        self._song_name_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        info_layout.addWidget(self._song_name_label)

        self._category_badge = QLabel("")
        self._category_badge.setStyleSheet(
            "background: #cde; padding: 2px 8px; border-radius: 4px; font-size: 11px;")
        info_layout.addWidget(self._category_badge)

        self._tempo_badge = QLabel("")
        self._tempo_badge.setStyleSheet(
            "color: #555; font-size: 11px;")
        info_layout.addWidget(self._tempo_badge)

        self._duration_badge = QLabel("")
        self._duration_badge.setStyleSheet(
            "color: #555; font-size: 11px;")
        info_layout.addWidget(self._duration_badge)

        self._loop_badge = QLabel("")
        self._loop_badge.setStyleSheet(
            "color: #555; font-size: 11px;")
        info_layout.addWidget(self._loop_badge)

        self._inst_badge = QLabel("")
        self._inst_badge.setStyleSheet(
            "color: #555; font-size: 11px;")
        info_layout.addWidget(self._inst_badge)

        info_layout.addStretch()
        self._info_frame.setVisible(False)
        outer.addWidget(self._info_frame)

        # --- Row 2: transport controls ---
        controls = QHBoxLayout()
        controls.setSpacing(6)

        # Play/Stop buttons
        self.play_btn = QPushButton("Play")
        self.play_btn.setFixedWidth(70)
        self.play_btn.clicked.connect(self.play_clicked)
        controls.addWidget(self.play_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setFixedWidth(70)
        self.stop_btn.clicked.connect(self.stop_clicked)
        controls.addWidget(self.stop_btn)

        # Progress slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.setEnabled(False)
        controls.addWidget(self.slider, 1)

        # Time label
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setFixedWidth(100)
        controls.addWidget(self.time_label)

        # Separator
        controls.addSpacing(16)

        # Loop count
        loop_label = QLabel("Loops:")
        controls.addWidget(loop_label)
        self.loop_combo = QComboBox()
        self.loop_combo.addItems(["1x", "2x", "3x", "4x"])
        self.loop_combo.setCurrentIndex(1)  # Default 2x
        self.loop_combo.currentIndexChanged.connect(
            lambda i: self.loop_count_changed.emit(i + 1))
        controls.addWidget(self.loop_combo)

        # Separator
        controls.addSpacing(16)

        # Export buttons
        self.export_btn = QPushButton("Export MIDI")
        self.export_btn.clicked.connect(self.export_clicked)
        controls.addWidget(self.export_btn)

        self.export_wav_btn = QPushButton("Export WAV")
        self.export_wav_btn.clicked.connect(self.export_wav_clicked)
        controls.addWidget(self.export_wav_btn)

        self.export_all_btn = QPushButton("Export Selected")
        self.export_all_btn.clicked.connect(self.export_all_clicked)
        controls.addWidget(self.export_all_btn)

        outer.addLayout(controls)

        self.set_enabled(False)

    def set_enabled(self, enabled):
        self.play_btn.setEnabled(enabled)
        self.stop_btn.setEnabled(enabled)
        self.export_btn.setEnabled(enabled)
        self.export_wav_btn.setEnabled(enabled)
        self.export_all_btn.setEnabled(enabled)

    def set_playing(self, playing):
        self.play_btn.setText("Pause" if playing else "Play")

    def update_time(self, elapsed, total):
        if total > 0:
            pos = int((elapsed / total) * 1000)
            self.slider.setValue(min(pos, 1000))
        self.time_label.setText(
            f"{_format_time(elapsed)} / {_format_time(total)}")

    def reset_time(self):
        self.slider.setValue(0)
        self.time_label.setText("0:00 / 0:00")
        self.set_playing(False)

    # --- Song info badges ---

    _CATEGORY_STYLES = {
        "Music":   "background: #c8dcff; color: #1a3a6a;",
        "SFX":     "background: #dcdcdc; color: #333;",
        "Jingle":  "background: #fff5c8; color: #6a5a1a;",
        "Fanfare": "background: #d2ffd2; color: #1a6a1a;",
    }

    def set_song_info(self, song):
        """Update the info badges for the currently selected song."""
        if song is None:
            self._info_frame.setVisible(False)
            return

        self._info_frame.setVisible(True)
        self._song_name_label.setText(song.name)

        cat = song.category or "?"
        style = self._CATEGORY_STYLES.get(cat,
            "background: #eee; color: #333;")
        self._category_badge.setText(cat)
        self._category_badge.setStyleSheet(
            f"{style} padding: 2px 8px; border-radius: 4px; font-size: 11px;")

        if song.tempo_bpm > 0:
            self._tempo_badge.setText(
                f"{song.tempo_bpm} BPM ({song.tempo_label})")
        else:
            self._tempo_badge.setText("")

        if song.duration_secs > 0:
            self._duration_badge.setText(
                f"{_format_duration(song.duration_secs)}")
        else:
            self._duration_badge.setText("")

        self._loop_badge.setText(song.loop_status or "")
        self._inst_badge.setText(song.instrument_profile or "")

    def clear_song_info(self):
        self._info_frame.setVisible(False)


def _format_time(seconds):
    """Format seconds as M:SS."""
    if seconds < 0:
        seconds = 0
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m}:{s:02d}"


def _format_duration(secs):
    """Format seconds as M:SS."""
    if secs <= 0:
        return "0:00"
    m = int(secs) // 60
    s = int(secs) % 60
    return f"{m}:{s:02d}"
