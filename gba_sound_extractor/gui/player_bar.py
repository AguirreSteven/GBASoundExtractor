"""Playback controls, tag display, and export buttons — Spotify-style layout."""

from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
                              QSlider, QLabel, QComboBox, QSizePolicy)
from PyQt5.QtCore import pyqtSignal, Qt


class PlayerBar(QWidget):
    """Spotify-style bottom bar: song info | transport | loop & export."""

    play_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    export_clicked = pyqtSignal()
    export_wav_clicked = pyqtSignal()
    export_all_clicked = pyqtSignal()
    loop_count_changed = pyqtSignal(int)
    engine_changed = pyqtSignal(int)   # 0=PCM, 1=MIDI

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("playerBar")
        self._setup_ui()

    def _setup_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 8, 12, 8)
        outer.setSpacing(12)

        # ---- Left column: song info ----
        left = QVBoxLayout()
        left.setSpacing(2)

        self._song_name_label = QLabel("")
        self._song_name_label.setStyleSheet(
            "font-weight: bold; font-size: 14px; color: #e0e0e0;")
        self._song_name_label.setFixedWidth(250)
        self._song_name_label.setWordWrap(False)
        left.addWidget(self._song_name_label)

        badges_row = QHBoxLayout()
        badges_row.setSpacing(8)
        badges_row.setContentsMargins(0, 0, 0, 0)

        self._category_badge = QLabel("")
        badges_row.addWidget(self._category_badge)

        self._tempo_badge = QLabel("")
        self._tempo_badge.setStyleSheet("color: #8a8a9a; font-size: 11px;")
        badges_row.addWidget(self._tempo_badge)

        self._duration_badge = QLabel("")
        self._duration_badge.setStyleSheet("color: #8a8a9a; font-size: 11px;")
        badges_row.addWidget(self._duration_badge)

        self._loop_badge = QLabel("")
        self._loop_badge.setStyleSheet("color: #8a8a9a; font-size: 11px;")
        badges_row.addWidget(self._loop_badge)

        self._inst_badge = QLabel("")
        self._inst_badge.setStyleSheet("color: #8a8a9a; font-size: 11px;")
        badges_row.addWidget(self._inst_badge)

        badges_row.addStretch()
        left.addLayout(badges_row)

        # Hide info initially
        self._song_name_label.setVisible(False)

        outer.addLayout(left)

        # ---- Center column: transport controls ----
        center = QVBoxLayout()
        center.setSpacing(4)
        center.setAlignment(Qt.AlignCenter)

        # Transport buttons row
        transport_row = QHBoxLayout()
        transport_row.setSpacing(8)
        transport_row.setAlignment(Qt.AlignCenter)

        self.play_btn = QPushButton("Play")
        self.play_btn.setObjectName("playBtn")
        self.play_btn.setFixedWidth(80)
        self.play_btn.clicked.connect(self.play_clicked)
        transport_row.addWidget(self.play_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setFixedWidth(70)
        self.stop_btn.clicked.connect(self.stop_clicked)
        transport_row.addWidget(self.stop_btn)

        center.addLayout(transport_row)

        # Slider + time row
        slider_row = QHBoxLayout()
        slider_row.setSpacing(8)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.setEnabled(False)
        slider_row.addWidget(self.slider, 1)

        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setStyleSheet("color: #8a8a9a; font-size: 11px;")
        self.time_label.setFixedWidth(90)
        self.time_label.setAlignment(Qt.AlignCenter)
        slider_row.addWidget(self.time_label)

        center.addLayout(slider_row)

        outer.addLayout(center, 1)  # stretch factor

        # ---- Right column: loop + export ----
        right = QHBoxLayout()
        right.setSpacing(8)
        right.setAlignment(Qt.AlignRight)

        engine_label = QLabel("Engine:")
        engine_label.setStyleSheet("color: #8a8a9a; font-size: 12px;")
        right.addWidget(engine_label)

        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["PCM (GBA Samples)", "MIDI (Wavetable)"])
        self.engine_combo.setCurrentIndex(0)
        self.engine_combo.currentIndexChanged.connect(self.engine_changed)
        right.addWidget(self.engine_combo)

        right.addSpacing(12)

        loop_label = QLabel("Loops:")
        loop_label.setStyleSheet("color: #8a8a9a; font-size: 12px;")
        right.addWidget(loop_label)

        self.loop_combo = QComboBox()
        self.loop_combo.addItems(["1x", "2x", "3x", "4x"])
        self.loop_combo.setCurrentIndex(1)
        self.loop_combo.currentIndexChanged.connect(
            lambda i: self.loop_count_changed.emit(i + 1))
        right.addWidget(self.loop_combo)

        right.addSpacing(12)

        self.export_btn = QPushButton("Export MIDI")
        self.export_btn.clicked.connect(self.export_clicked)
        right.addWidget(self.export_btn)

        self.export_wav_btn = QPushButton("Export WAV")
        self.export_wav_btn.clicked.connect(self.export_wav_clicked)
        right.addWidget(self.export_wav_btn)

        self.export_all_btn = QPushButton("Export Selected")
        self.export_all_btn.clicked.connect(self.export_all_clicked)
        right.addWidget(self.export_all_btn)

        outer.addLayout(right)

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
        "Music":   "background: #1a2e4a; color: #5ba0f0;",
        "SFX":     "background: #2a2a2a; color: #999999;",
        "Jingle":  "background: #3a3520; color: #d4b84a;",
        "Fanfare": "background: #1a3a1a; color: #5ac05a;",
    }

    def set_song_info(self, song):
        """Update the info badges for the currently selected song."""
        if song is None:
            self._song_name_label.setVisible(False)
            return

        self._song_name_label.setVisible(True)
        self._song_name_label.setText(song.name)

        cat = song.category or "?"
        style = self._CATEGORY_STYLES.get(cat,
            "background: #2a2a2a; color: #8a8a9a;")
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
        self._song_name_label.setVisible(False)
        self._category_badge.setText("")
        self._tempo_badge.setText("")
        self._duration_badge.setText("")
        self._loop_badge.setText("")
        self._inst_badge.setText("")


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
