"""Main application window with drag-and-drop ROM loading, song analysis,
name resolution, and custom name file support."""

import logging
import os

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QSplitter, QTextEdit, QPushButton, QLabel,
                              QFileDialog, QMessageBox, QStatusBar, QMenuBar,
                              QAction, QProgressDialog, QApplication)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer

import mido

from ..rom.reader import ROMReader
from ..rom.detector import detect_song_tables
from ..rom.parser import parse_song_list, parse_voice_group
from ..mp2k.sequence import decode_track
from ..midi.converter import convert_song_to_midi
from ..audio.preview import MidiPlayer
from ..audio.renderer import GBASynthPlayer, render_to_wav
from ..audio.samples import SampleCache
from ..analysis.tagger import tag_song
from ..analysis.custom_names import load_custom_names, save_custom_names
from .song_list import SongListWidget
from .player_bar import PlayerBar

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Background workers
# ---------------------------------------------------------------------------

class ROMLoadWorker(QThread):
    """Background thread for loading and parsing a ROM."""
    finished = pyqtSignal(object, object, object)  # rom, songs, error
    progress = pyqtSignal(str)

    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath

    def run(self):
        try:
            self.progress.emit("Loading ROM...")
            rom = ROMReader(self.filepath)
            if not rom.validate():
                self.finished.emit(None, None, "Invalid GBA ROM file.")
                return

            self.progress.emit("Detecting song table...")
            candidates = detect_song_tables(rom)
            if not candidates:
                self.finished.emit(rom, None,
                                   "No MP2K song table found in this ROM.")
                return

            best = candidates[0]
            self.progress.emit(
                f"Parsing {best.count} songs from table at "
                f"0x{best.offset:06X}...")
            songs = parse_song_list(rom, best.offset, best.count)

            self.finished.emit(rom, songs, None)
        except Exception as e:
            logger.exception("ROM load error")
            self.finished.emit(None, None, str(e))


class AnalysisWorker(QThread):
    """Background thread that decodes all tracks and runs the tagger."""
    finished = pyqtSignal()
    progress = pyqtSignal(int, int)  # current, total

    def __init__(self, rom, songs, loop_count):
        super().__init__()
        self.rom = rom
        self.songs = songs
        self.loop_count = loop_count

    def run(self):
        total = len(self.songs)
        for i, song in enumerate(self.songs):
            self.progress.emit(i, total)
            try:
                # Decode tracks
                if not song.decoded:
                    song.tracks = []
                    for t, offset in enumerate(song.track_offsets):
                        track = decode_track(
                            self.rom, offset, t, self.loop_count)
                        song.tracks.append(track)
                    song.decoded = True

                # Parse instruments for profile tagging
                if not song.instruments:
                    try:
                        song.instruments = parse_voice_group(
                            self.rom, song.voice_group_offset)
                    except Exception:
                        pass  # Non-fatal

                # Tag the song
                tag_song(song)

            except Exception as e:
                logger.warning("Failed to analyse song %d: %s",
                               song.index, e)

        self.progress.emit(total, total)
        self.finished.emit()


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GBA Sound Extractor")
        self.setMinimumSize(1050, 650)
        self.resize(1150, 700)
        self.setAcceptDrops(True)

        self._rom = None
        self._songs = []
        self._songs_by_index = {}
        self._current_song = None
        self._current_midi = None
        self._loop_count = 2
        self._worker = None
        self._analysis_worker = None
        self._game_code = ""
        self._custom_names = {}

        self._sample_cache = None

        self._synth_player = GBASynthPlayer()
        self._midi_player = MidiPlayer()
        self._use_pcm = True
        self._timer = QTimer()
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._update_playback)

        self._setup_menu()
        self._setup_ui()

    @property
    def _player(self):
        """Return the currently active audio player."""
        return self._synth_player if self._use_pcm else self._midi_player

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _setup_menu(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")

        open_act = QAction("&Open ROM...", self)
        open_act.setShortcut("Ctrl+O")
        open_act.triggered.connect(self._open_file_dialog)
        file_menu.addAction(open_act)

        file_menu.addSeparator()

        self._load_names_act = QAction("Load &Name File...", self)
        self._load_names_act.setShortcut("Ctrl+N")
        self._load_names_act.triggered.connect(self._on_load_name_file)
        self._load_names_act.setEnabled(False)
        file_menu.addAction(self._load_names_act)

        self._save_names_act = QAction("&Save Name File...", self)
        self._save_names_act.setShortcut("Ctrl+S")
        self._save_names_act.triggered.connect(self._on_save_name_file)
        self._save_names_act.setEnabled(False)
        file_menu.addAction(self._save_names_act)

        file_menu.addSeparator()

        exit_act = QAction("E&xit", self)
        exit_act.setShortcut("Alt+F4")
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # --- Top bar: file path + open button ---
        top_bar_widget = QWidget()
        top_bar = QHBoxLayout(top_bar_widget)
        top_bar.setContentsMargins(12, 8, 12, 8)
        rom_label = QLabel("ROM:")
        rom_label.setStyleSheet("color: #8a8a9a; font-weight: bold;")
        top_bar.addWidget(rom_label)
        self._file_label = QLabel("Drag and drop a .gba file or click Open")
        self._file_label.setStyleSheet("color: #8a8a9a;")
        top_bar.addWidget(self._file_label, 1)
        open_btn = QPushButton("Open ROM...")
        open_btn.clicked.connect(self._open_file_dialog)
        top_bar.addWidget(open_btn)
        main_layout.addWidget(top_bar_widget)

        # --- Middle: splitter with song list + details ---
        splitter_wrapper = QWidget()
        splitter_layout = QHBoxLayout(splitter_wrapper)
        splitter_layout.setContentsMargins(8, 0, 8, 4)
        splitter = QSplitter(Qt.Horizontal)

        self._song_list = SongListWidget()
        self._song_list.song_selected.connect(self._on_song_selected)
        self._song_list.song_double_clicked.connect(self._on_song_double_click)
        splitter.addWidget(self._song_list)

        self._details = QTextEdit()
        self._details.setReadOnly(True)
        self._details.setPlaceholderText("Select a song to view details")
        splitter.addWidget(self._details)

        splitter.setSizes([550, 300])
        splitter_layout.addWidget(splitter)
        main_layout.addWidget(splitter_wrapper, 1)

        # --- Bottom: player bar ---
        self._player_bar = PlayerBar()
        self._player_bar.play_clicked.connect(self._on_play)
        self._player_bar.stop_clicked.connect(self._on_stop)
        self._player_bar.export_clicked.connect(self._on_export)
        self._player_bar.export_wav_clicked.connect(self._on_export_wav)
        self._player_bar.export_all_clicked.connect(self._on_export_all)
        self._player_bar.loop_count_changed.connect(self._on_loop_changed)
        self._player_bar.engine_changed.connect(self._on_engine_changed)
        main_layout.addWidget(self._player_bar)

        # --- Status bar ---
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready — drag a GBA ROM onto this window")

    # ------------------------------------------------------------------
    # Drag and drop
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path.lower().endswith((".gba", ".bin", ".rom")):
                    event.acceptProposedAction()
                    return

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith((".gba", ".bin", ".rom")):
                self._load_rom(path)
                return

    # ------------------------------------------------------------------
    # File loading
    # ------------------------------------------------------------------

    def _open_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open GBA ROM",
            "", "GBA ROMs (*.gba *.bin *.rom);;All Files (*)")
        if path:
            self._load_rom(path)

    def _load_rom(self, filepath):
        if self._worker is not None and self._worker.isRunning():
            return

        self._on_stop()
        self._song_list.clear_songs()
        self._details.clear()
        self._player_bar.clear_song_info()
        self._rom = None
        self._songs = []
        self._songs_by_index = {}
        self._current_song = None
        self._current_midi = None
        self._game_code = ""
        self._custom_names = {}
        self._sample_cache = None

        self._file_label.setText(os.path.basename(filepath))
        self._file_label.setStyleSheet("color: #e0e0e0;")
        self._status.showMessage("Loading ROM...")

        self._worker = ROMLoadWorker(filepath)
        self._worker.progress.connect(
            lambda msg: self._status.showMessage(msg))
        self._worker.finished.connect(self._on_rom_loaded)
        self._worker.start()

    def _on_rom_loaded(self, rom, songs, error):
        self._worker = None
        if error:
            QMessageBox.warning(self, "Error", error)
            self._status.showMessage("Failed to load ROM")
            return

        self._rom = rom
        self._songs = songs
        self._songs_by_index = {s.index: s for s in songs}
        self._game_code = rom.game_code().strip()
        self._sample_cache = SampleCache(rom)

        title = rom.game_title()
        code = self._game_code
        self._file_label.setText(
            f"{os.path.basename(rom.filepath)} — {title} [{code}]")

        # Show songs immediately (tags will fill in after analysis)
        self._song_list.set_songs(songs)
        self._player_bar.set_enabled(True)
        self._load_names_act.setEnabled(True)
        self._save_names_act.setEnabled(True)

        # Start background analysis (decode + tag all songs)
        self._start_analysis()

    # ------------------------------------------------------------------
    # Song name resolution
    # ------------------------------------------------------------------

    def _apply_custom_names(self, names):
        """Override song names with a user-provided mapping."""
        self._custom_names = names
        applied = 0
        for song in self._songs:
            custom = names.get(song.index)
            if custom:
                song.name = custom
                applied += 1
        self._song_list.refresh()
        self._status.showMessage(
            f"Applied {applied} custom song names")

    def _on_load_name_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Song Name File", "",
            "Name Files (*.json *.txt);;All Files (*)")
        if not path:
            return
        try:
            names = load_custom_names(path)
            self._apply_custom_names(names)
        except Exception as e:
            QMessageBox.warning(self, "Error",
                                f"Failed to load name file:\n{e}")

    def _on_save_name_file(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Song Name File", "",
            "JSON Files (*.json);;All Files (*)")
        if not path:
            return
        # Build the current name mapping
        names = {s.index: s.name for s in self._songs}
        try:
            save_custom_names(path, names)
            self._status.showMessage(f"Saved song names to {path}")
        except Exception as e:
            QMessageBox.warning(self, "Error",
                                f"Failed to save name file:\n{e}")

    # ------------------------------------------------------------------
    # Background analysis (decode all + tag)
    # ------------------------------------------------------------------

    def _start_analysis(self):
        """Decode all tracks and run the auto-tagger in a background thread."""
        if self._analysis_worker is not None and self._analysis_worker.isRunning():
            return

        total = len(self._songs)
        self._progress_dialog = QProgressDialog(
            "Analysing songs...", "Cancel", 0, total, self)
        self._progress_dialog.setWindowModality(Qt.WindowModal)
        self._progress_dialog.setMinimumDuration(0)
        self._progress_dialog.setAutoClose(False)
        self._progress_dialog.setAutoReset(False)
        self._progress_dialog.setValue(0)

        self._analysis_worker = AnalysisWorker(
            self._rom, self._songs, self._loop_count)
        self._analysis_worker.progress.connect(self._on_analysis_progress)
        self._analysis_worker.finished.connect(self._on_analysis_finished)
        self._progress_dialog.canceled.connect(self._analysis_worker.terminate)
        self._analysis_worker.start()

    def _on_analysis_progress(self, current, total):
        dlg = getattr(self, '_progress_dialog', None)
        if dlg is not None:
            try:
                dlg.setLabelText(
                    f"Analysing song {current + 1} of {total}...")
                dlg.setValue(current)
            except (RuntimeError, AttributeError):
                pass  # Dialog was already destroyed

    def _on_analysis_finished(self):
        self._analysis_worker = None
        dlg = getattr(self, '_progress_dialog', None)
        if dlg is not None:
            self._progress_dialog = None
            try:
                dlg.close()
                dlg.deleteLater()
            except RuntimeError:
                pass  # Already destroyed

        # Refresh the song list to show tags
        self._song_list.refresh()
        self._status.showMessage(
            f"Analysis complete — {len(self._songs)} songs tagged")

    # ------------------------------------------------------------------
    # Song selection
    # ------------------------------------------------------------------

    def _on_song_selected(self, song_index):
        song = self._songs_by_index.get(song_index)
        if song is None:
            return

        self._current_song = song
        self._ensure_decoded(song)

        # Update player bar info badges
        self._player_bar.set_song_info(song)

        # Build details text
        lines = [
            f"{song.name}",
            f"{'─' * 40}",
            f"Index:       {song.index:03d}",
            f"Tracks:      {song.num_tracks}",
            f"Reverb:      {song.reverb}",
            f"Priority:    {song.priority}",
            f"Voice Group: 0x{song.voice_group_offset:06X}",
        ]

        # Tag info
        if song.category:
            lines.append("")
            lines.append(f"Category:    {song.category}")
            if song.tempo_bpm > 0:
                lines.append(f"Tempo:       {song.tempo_bpm} BPM ({song.tempo_label})")
            if song.duration_secs > 0:
                dur_m = int(song.duration_secs) // 60
                dur_s = int(song.duration_secs) % 60
                lines.append(f"Duration:    {dur_m}:{dur_s:02d}")
            lines.append(f"Loop:        {song.loop_status}")
            if song.instrument_profile:
                lines.append(f"Instruments: {song.instrument_profile}")

        lines.append("")
        if song.decoded:
            for track in song.tracks:
                lines.append(
                    f"  Track {track.index}: {len(track.commands)} commands, "
                    f"{track.total_ticks} ticks")
        self._details.setText("\n".join(lines))

    def _on_song_double_click(self, song_index):
        self._on_song_selected(song_index)
        self._on_play()

    def _ensure_decoded(self, song):
        """Decode track sequences if not already done."""
        if song.decoded or self._rom is None:
            return
        try:
            song.tracks = []
            for i, offset in enumerate(song.track_offsets):
                track = decode_track(self._rom, offset, i, self._loop_count)
                song.tracks.append(track)
            song.decoded = True
        except Exception as e:
            logger.exception("Failed to decode song %d", song.index)
            self._status.showMessage(f"Error decoding song: {e}")

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    def _on_play(self):
        if self._player.is_active:
            self._player.pause()
            self._player_bar.set_playing(self._player.is_playing)
            return

        song = self._current_song
        if song is None:
            return

        self._ensure_decoded(song)
        if not song.decoded:
            return

        try:
            if self._use_pcm:
                # PCM engine — render from ROM samples
                if not song.instruments and self._rom is not None:
                    try:
                        song.instruments = parse_voice_group(
                            self._rom, song.voice_group_offset)
                    except Exception as e:
                        logger.warning("Failed to parse voice group: %s", e)
                self._synth_player.play(song, self._sample_cache, rom=self._rom)
            else:
                # MIDI engine — convert and play through system synth
                midi = convert_song_to_midi(song)
                self._midi_player.play(midi)

            self._player_bar.set_playing(True)
            self._timer.start()
            self._status.showMessage(f"Playing: {song.name}")
        except Exception as e:
            logger.exception("Playback error")
            self._status.showMessage(f"Playback error: {e}")

    def _on_stop(self):
        self._synth_player.stop()
        self._midi_player.stop()
        self._timer.stop()
        self._player_bar.reset_time()
        self._status.showMessage("Stopped")

    def _update_playback(self):
        if not self._player.is_active:
            self._timer.stop()
            self._player_bar.reset_time()
            self._status.showMessage("Ready")
            return
        self._player_bar.update_time(
            self._player.elapsed, self._player.total_length)

    def _on_loop_changed(self, count):
        self._loop_count = count
        # Re-decode songs when loop count changes
        for song in self._songs:
            song.decoded = False
            song.tracks = []

    def _on_engine_changed(self, index):
        """Switch between PCM (0) and MIDI (1) audio engines."""
        self._on_stop()
        self._use_pcm = (index == 0)
        # Export WAV only available with PCM engine
        self._player_bar.export_wav_btn.setEnabled(
            self._use_pcm and bool(self._songs))
        engine_name = "PCM (GBA Samples)" if self._use_pcm else "MIDI (Wavetable)"
        self._status.showMessage(f"Audio engine: {engine_name}")

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _on_export(self):
        song = self._current_song
        if song is None:
            return
        self._export_song(song)

    def _on_export_wav(self):
        song = self._current_song
        if song is None or self._sample_cache is None:
            return
        self._ensure_decoded(song)
        if not song.decoded:
            return

        if not song.instruments and self._rom is not None:
            try:
                song.instruments = parse_voice_group(
                    self._rom, song.voice_group_offset)
            except Exception:
                pass

        safe_name = self._sanitise_filename(song.name, song.index)
        default_name = f"{safe_name}.wav"
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export WAV", default_name,
            "WAV Files (*.wav);;All Files (*)")
        if not filepath:
            return

        try:
            self._status.showMessage(f"Rendering WAV: {song.name}...")
            QApplication.processEvents()
            render_to_wav(song, self._sample_cache, filepath, rom=self._rom)
            self._status.showMessage(f"Exported WAV to {filepath}")
        except Exception as e:
            logger.exception("WAV export error")
            QMessageBox.warning(self, "Export Error", str(e))

    def _on_export_all(self):
        indices = self._song_list.get_selected_indices()
        if not indices:
            QMessageBox.information(
                self, "Export", "Select one or more songs to export.")
            return

        directory = QFileDialog.getExistingDirectory(
            self, "Export MIDI Files To")
        if not directory:
            return

        exported = 0
        for idx in indices:
            song = self._songs_by_index.get(idx)
            if song is None:
                continue
            self._ensure_decoded(song)
            if not song.decoded:
                continue
            try:
                midi = convert_song_to_midi(song)
                # Use song name for filename (sanitised)
                safe_name = self._sanitise_filename(song.name, song.index)
                filename = f"{safe_name}.mid"
                filepath = os.path.join(directory, filename)
                midi.save(filepath)
                exported += 1
            except Exception as e:
                logger.error("Failed to export song %d: %s", song.index, e)

        self._status.showMessage(
            f"Exported {exported} of {len(indices)} songs to {directory}")

    def _export_song(self, song):
        self._ensure_decoded(song)
        if not song.decoded:
            return

        safe_name = self._sanitise_filename(song.name, song.index)
        default_name = f"{safe_name}.mid"
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export MIDI", default_name,
            "MIDI Files (*.mid);;All Files (*)")
        if not filepath:
            return

        try:
            midi = convert_song_to_midi(song)
            midi.save(filepath)
            self._status.showMessage(f"Exported to {filepath}")
        except Exception as e:
            logger.exception("Export error")
            QMessageBox.warning(self, "Export Error", str(e))

    @staticmethod
    def _sanitise_filename(name, index):
        """Create a filesystem-safe filename from a song name."""
        safe = "".join(c if c.isalnum() or c in " _-.()" else "_"
                       for c in name).strip()
        if not safe:
            safe = f"song_{index:03d}"
        else:
            safe = f"{index:03d}_{safe}"
        return safe

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        self._synth_player.cleanup()
        self._midi_player.cleanup()
        if self._analysis_worker and self._analysis_worker.isRunning():
            self._analysis_worker.terminate()
            self._analysis_worker.wait(1000)
        super().closeEvent(event)
