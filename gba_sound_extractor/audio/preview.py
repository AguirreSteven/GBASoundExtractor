"""MIDI playback preview using python-rtmidi."""

import logging
import threading
import time

import mido
import rtmidi

logger = logging.getLogger(__name__)


class MidiPlayer:
    """Plays a mido.MidiFile through the system MIDI synthesizer."""

    def __init__(self):
        self._output = None
        self._playing = False
        self._paused = False
        self._thread = None
        self._lock = threading.Lock()
        self._elapsed = 0.0
        self._total_length = 0.0

    def play(self, midi_file: mido.MidiFile):
        """Start playback of a MIDI file."""
        self.stop()
        self._ensure_output()
        if self._output is None:
            logger.error("No MIDI output device available")
            return

        self._total_length = midi_file.length
        self._elapsed = 0.0
        self._playing = True
        self._paused = False
        self._thread = threading.Thread(
            target=self._playback_loop, args=(midi_file,), daemon=True)
        self._thread.start()

    def stop(self):
        """Stop playback."""
        self._playing = False
        self._paused = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._all_notes_off()
        self._elapsed = 0.0

    def pause(self):
        """Toggle pause state."""
        self._paused = not self._paused

    @property
    def is_playing(self) -> bool:
        return self._playing and not self._paused

    @property
    def is_active(self) -> bool:
        return self._playing

    @property
    def elapsed(self) -> float:
        return self._elapsed

    @property
    def total_length(self) -> float:
        return self._total_length

    def _ensure_output(self):
        if self._output is not None:
            return
        try:
            midi_out = rtmidi.MidiOut()
            ports = midi_out.get_ports()
            if not ports:
                # Try opening a virtual port on systems that support it,
                # otherwise fall back to the first available port
                logger.warning("No MIDI output ports found. "
                               "MIDI preview will be unavailable.")
                midi_out.delete()
                return
            # Open the first available port (typically Microsoft GS Wavetable)
            midi_out.open_port(0)
            logger.info("Opened MIDI output: %s", ports[0])
            self._output = midi_out
        except Exception as e:
            logger.error("Failed to open MIDI output: %s", e)
            self._output = None

    def _playback_loop(self, midi_file: mido.MidiFile):
        """Play MIDI messages with correct timing."""
        start_time = time.perf_counter()
        try:
            for msg in midi_file.play():
                if not self._playing:
                    break
                while self._paused and self._playing:
                    time.sleep(0.05)
                if not self._playing:
                    break

                self._elapsed = time.perf_counter() - start_time

                if msg.is_meta:
                    continue
                if self._output is None:
                    continue

                try:
                    self._output.send_message(msg.bytes())
                except Exception as e:
                    logger.debug("MIDI output error: %s", e)
        except Exception as e:
            logger.error("Playback error: %s", e)
        finally:
            self._playing = False
            self._all_notes_off()

    def _all_notes_off(self):
        """Send All Notes Off on all channels."""
        if self._output is None:
            return
        try:
            for ch in range(16):
                self._output.send_message([0xB0 | ch, 123, 0])  # All Notes Off
                self._output.send_message([0xB0 | ch, 121, 0])  # Reset All
        except Exception:
            pass

    def cleanup(self):
        """Clean up resources."""
        self.stop()
        if self._output is not None:
            try:
                self._output.close_port()
                self._output.delete()
            except Exception:
                pass
            self._output = None
