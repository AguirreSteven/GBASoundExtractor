"""PSG (Programmable Sound Generator) waveform generators for GBA.

Covers the GBA's four PSG channels:
- Square wave 1 & 2 (with configurable duty cycle)
- Wave channel (32-sample 4-bit wavetable)
- Noise channel (LFSR-based)
"""

import numpy as np

from ..rom.reader import ROMReader


# GBA PSG volume relative to DirectSound (PCM). PSG channels are quieter.
PSG_VOLUME_SCALE = 0.25


class SquareWaveGenerator:
    """Generates a square wave with one of 4 GBA duty cycles."""

    DUTY_CYCLES = [0.125, 0.25, 0.5, 0.75]

    def __init__(self, duty_index: int = 2):
        self.duty = self.DUTY_CYCLES[duty_index % 4]
        self.phase = 0.0

    def render(self, num_frames: int, frequency: float,
               output_rate: int) -> np.ndarray:
        if frequency <= 0 or num_frames <= 0:
            return np.zeros(num_frames, dtype=np.float32)

        phase_inc = frequency / output_rate
        phases = (self.phase + np.arange(num_frames) * phase_inc) % 1.0
        out = np.where(phases < self.duty, 1.0, -1.0).astype(np.float32)
        self.phase = (self.phase + num_frames * phase_inc) % 1.0
        return out * PSG_VOLUME_SCALE


class NoiseGenerator:
    """LFSR-based noise generator matching GBA hardware."""

    def __init__(self, short_mode: bool = False):
        self.short_mode = short_mode
        self.width = 7 if short_mode else 15
        self.lfsr = (1 << self.width) - 1
        self.phase = 0.0
        self._current_bit = 1.0

    def render(self, num_frames: int, frequency: float,
               output_rate: int) -> np.ndarray:
        if frequency <= 0 or num_frames <= 0:
            return np.zeros(num_frames, dtype=np.float32)

        out = np.empty(num_frames, dtype=np.float32)
        phase_inc = frequency / output_rate

        for i in range(num_frames):
            out[i] = self._current_bit * PSG_VOLUME_SCALE
            self.phase += phase_inc
            while self.phase >= 1.0:
                self.phase -= 1.0
                self._clock()

        return out

    def _clock(self):
        bit0 = self.lfsr & 1
        bit1 = (self.lfsr >> 1) & 1
        feedback = bit0 ^ bit1
        self.lfsr >>= 1
        self.lfsr |= feedback << (self.width - 1)
        self._current_bit = 1.0 if (bit0 == 0) else -1.0


class WaveGenerator:
    """Plays back a GBA wave channel wavetable (32 x 4-bit samples)."""

    def __init__(self, rom: ROMReader, wave_data_offset: int):
        # Read 16 bytes = 32 x 4-bit samples (high nibble first)
        raw = rom.read_bytes(wave_data_offset, 16)
        self.wavetable = np.zeros(32, dtype=np.float32)
        for i, byte in enumerate(raw):
            high = (byte >> 4) & 0x0F
            low = byte & 0x0F
            # Normalise 0-15 to -1.0..1.0
            self.wavetable[i * 2] = (high - 7.5) / 7.5
            self.wavetable[i * 2 + 1] = (low - 7.5) / 7.5
        self.phase = 0.0

    def render(self, num_frames: int, frequency: float,
               output_rate: int) -> np.ndarray:
        if frequency <= 0 or num_frames <= 0:
            return np.zeros(num_frames, dtype=np.float32)

        # Advance through 32-sample wavetable at the correct rate
        # One cycle of the wavetable = one period of the wave
        phase_inc = (frequency * 32.0) / output_rate
        indices = (self.phase + np.arange(num_frames) * phase_inc) % 32.0
        int_indices = indices.astype(np.int32) % 32
        out = self.wavetable[int_indices] * PSG_VOLUME_SCALE
        self.phase = (self.phase + num_frames * phase_inc) % 32.0
        return out
