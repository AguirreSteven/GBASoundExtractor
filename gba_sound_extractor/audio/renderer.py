"""Real-time GBA audio playback and WAV export.

GBASynthPlayer is a drop-in replacement for MidiPlayer, using the same
interface (play/stop/pause/is_playing/is_active/elapsed/total_length/cleanup).
"""

import logging
import struct
import threading
import time
import wave
from collections import deque

import numpy as np

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except (ImportError, OSError):
    HAS_SOUNDDEVICE = False

from ..mp2k.structures import Song
from .samples import SampleCache
from .synth import GBASynth

logger = logging.getLogger(__name__)

OUTPUT_RATE = 44100
CHUNK_SIZE = 1024
BUFFER_CHUNKS = 8  # ring buffer depth


class GBASynthPlayer:
    """Streams GBA-synthesised audio in real time via sounddevice."""

    def __init__(self):
        self._stream = None
        self._synth = None
        self._playing = False
        self._paused = False
        self._thread = None
        self._lock = threading.Lock()
        self._elapsed = 0.0
        self._total_length = 0.0
        self._buffer: deque[np.ndarray] = deque()
        self._stop_event = threading.Event()

    def play(self, song: Song, sample_cache: SampleCache, rom=None):
        """Start playback of a decoded song using ROM samples."""
        self.stop()

        if not HAS_SOUNDDEVICE:
            logger.error("sounddevice not available — install it with: "
                         "pip install sounddevice")
            return

        synth = GBASynth(song, sample_cache, OUTPUT_RATE, rom=rom)
        self._synth = synth
        self._total_length = synth.total_seconds
        self._elapsed = 0.0
        self._buffer.clear()
        self._stop_event.clear()

        # Pre-fill buffer
        for _ in range(BUFFER_CHUNKS):
            if synth.finished:
                break
            chunk = synth.render_chunk(CHUNK_SIZE)
            self._buffer.append(chunk)

        self._playing = True
        self._paused = False

        # Start audio stream
        self._stream = sd.OutputStream(
            samplerate=OUTPUT_RATE,
            channels=2,
            dtype='float32',
            blocksize=CHUNK_SIZE,
            callback=self._audio_callback,
        )
        self._stream.start()

        # Start synth render thread
        self._thread = threading.Thread(target=self._render_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop playback and clean up."""
        self._playing = False
        self._paused = False
        self._stop_event.set()

        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

        self._synth = None
        self._buffer.clear()
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

    def cleanup(self):
        """Release all resources."""
        self.stop()

    def _audio_callback(self, outdata, frames, time_info, status):
        """sounddevice callback — fills output buffer from the ring buffer."""
        if not self._playing or self._paused:
            outdata[:] = 0
            return

        if self._buffer:
            chunk = self._buffer.popleft()
            # Chunk might be shorter than frames on last chunk
            n = min(len(chunk), frames)
            outdata[:n] = chunk[:n]
            if n < frames:
                outdata[n:] = 0
            self._elapsed += n / OUTPUT_RATE
        else:
            outdata[:] = 0
            # Check if synth is done
            if self._synth is not None and self._synth.finished:
                self._playing = False

    def _render_loop(self):
        """Background thread that feeds the ring buffer from the synth."""
        while self._playing and not self._stop_event.is_set():
            if self._paused:
                time.sleep(0.01)
                continue

            if len(self._buffer) < BUFFER_CHUNKS:
                if self._synth is not None and not self._synth.finished:
                    chunk = self._synth.render_chunk(CHUNK_SIZE)
                    # Clip to prevent distortion
                    np.clip(chunk, -1.0, 1.0, out=chunk)
                    self._buffer.append(chunk)
                elif not self._buffer:
                    # Synth done and buffer empty
                    self._playing = False
                    break
                else:
                    time.sleep(0.005)
            else:
                time.sleep(0.005)


def render_to_wav(song: Song, sample_cache: SampleCache, filepath: str,
                  output_rate: int = 44100, rom=None):
    """Render a decoded song to a WAV file (offline, as fast as possible)."""
    synth = GBASynth(song, sample_cache, output_rate, rom=rom)
    chunks = []

    while not synth.finished:
        chunk = synth.render_chunk(CHUNK_SIZE)
        chunks.append(chunk)
        # Safety: cap at 10 minutes
        total_frames = sum(len(c) for c in chunks)
        if total_frames > output_rate * 600:
            break

    if not chunks:
        return

    audio = np.concatenate(chunks, axis=0)
    np.clip(audio, -1.0, 1.0, out=audio)

    # Convert float32 [-1, 1] to int16
    pcm16 = (audio * 32767).astype(np.int16)

    with wave.open(filepath, 'wb') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(output_rate)
        wf.writeframes(pcm16.tobytes())
