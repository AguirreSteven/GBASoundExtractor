"""Single voice/channel renderer for the GBA software synthesizer.

A SynthChannel represents one active note — it reads from a PCM sample
(with pitch shifting via linear interpolation) or a PSG generator,
applies an ADSR envelope, and produces mono float32 audio.
"""

import numpy as np

from .envelope import ADSREnvelope


# MIDI note 60 (middle C) = 261.626 Hz
_NOTE_FREQ_TABLE = [
    440.0 * (2.0 ** ((n - 69) / 12.0)) for n in range(128)
]


def note_to_freq(note: float) -> float:
    """Convert a MIDI note number (0-127, fractional OK) to frequency in Hz."""
    note = max(0.0, min(127.0, float(note)))
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


class SynthChannel:
    """Renders audio for a single playing note."""

    def __init__(self, sample_data, sample_rate, base_key, note, velocity,
                 adsr_params, output_rate, duration_frames=None,
                 loop=False, loop_start=0,
                 psg_generator=None):
        """
        Args:
            sample_data: numpy float32 array of PCM data, or None for PSG.
            sample_rate: native sample rate of the PCM data.
            base_key: root MIDI note of the sample (the note at which
                      the sample plays at its native rate).
            note: the MIDI note to play (float OK for pitch bend).
            velocity: 0-127 velocity.
            adsr_params: (attack, decay, sustain, release) tuple.
            output_rate: audio output sample rate (e.g. 44100).
            duration_frames: number of output frames before auto note-off.
                             None = sustained (TIE), waits for release().
            loop: whether the sample loops.
            loop_start: loop point in samples (from sample start).
            psg_generator: PSG generator instance (if not PCM).
        """
        self.output_rate = output_rate
        self.note = note
        # Linear velocity — track volume in the mixer applies the squared curve
        self.velocity_gain = velocity / 127.0
        self.finished = False

        # Envelope
        a, d, s, r = adsr_params
        self.envelope = ADSREnvelope(a, d, s, r, output_rate)

        # PSG or PCM mode
        self.psg = psg_generator
        self.frequency = note_to_freq(note)

        if self.psg is None:
            # PCM mode
            self.sample_data = sample_data
            self.sample_length = len(sample_data) if sample_data is not None else 0
            self.loop = loop
            self.loop_start = min(loop_start, self.sample_length)
            self.loop_length = self.sample_length - self.loop_start

            # Playback speed ratio: how many source samples per output sample
            if sample_rate > 0 and base_key >= 0:
                semitone_diff = note - base_key
                freq_ratio = 2.0 ** (semitone_diff / 12.0)
                self.speed = (sample_rate * freq_ratio) / output_rate
            else:
                self.speed = 1.0

            self.position = 0.0  # float for sub-sample interpolation
        else:
            self.sample_data = None
            self.sample_length = 0
            self.loop = True  # PSG always loops
            self.speed = 0.0
            self.position = 0.0

        # Duration tracking
        self.duration_frames = duration_frames
        self.frames_played = 0
        self._released = False

    def release(self):
        """Trigger the release phase (note-off)."""
        if not self._released:
            self._released = True
            self.envelope.trigger_release()

    def render(self, num_frames: int) -> np.ndarray:
        """Render num_frames of mono audio. Returns float32 array."""
        if self.finished:
            return np.zeros(num_frames, dtype=np.float32)

        # Check if timed note should release
        if (self.duration_frames is not None and not self._released
                and self.frames_played + num_frames >= self.duration_frames):
            # Split: play remaining active frames, then release
            remaining = max(0, self.duration_frames - self.frames_played)
            if remaining > 0:
                part1 = self._render_raw(remaining)
                self.release()
                part2 = self._render_raw(num_frames - remaining)
                audio = np.concatenate([part1, part2])
            else:
                self.release()
                audio = self._render_raw(num_frames)
        else:
            audio = self._render_raw(num_frames)

        # Apply envelope
        env = self.envelope.advance(num_frames)
        audio *= env * self.velocity_gain

        self.frames_played += num_frames

        if self.envelope.is_finished():
            self.finished = True

        return audio

    def _render_raw(self, num_frames: int) -> np.ndarray:
        """Render raw waveform without envelope."""
        if num_frames <= 0:
            return np.empty(0, dtype=np.float32)

        if self.psg is not None:
            return self.psg.render(num_frames, self.frequency, self.output_rate)

        return self._render_pcm(num_frames)

    def _render_pcm(self, num_frames: int) -> np.ndarray:
        """Render PCM sample with linear interpolation and looping (vectorised)."""
        if self.sample_data is None or self.sample_length == 0:
            self.finished = True
            return np.zeros(num_frames, dtype=np.float32)

        data = self.sample_data
        length = self.sample_length
        total_requested = num_frames

        # Compute all sample positions
        positions = self.position + np.arange(num_frames) * self.speed

        if self.loop and self.loop_length > 0:
            # Wrap positions past sample end into loop region
            mask = positions >= length
            if np.any(mask):
                positions[mask] = (
                    self.loop_start
                    + (positions[mask] - length) % self.loop_length
                )
        else:
            # Find where we exceed sample length
            past_end = positions >= length
            if np.any(past_end):
                first_past = int(np.argmax(past_end))
                if first_past == 0:
                    self.finished = True
                    return np.zeros(total_requested, dtype=np.float32)
                self.finished = True
                positions = positions[:first_past]
                num_frames = first_past

        # Integer indices and fractional parts for interpolation
        int_pos = positions.astype(np.int64)
        frac = (positions - int_pos).astype(np.float32)

        # Clamp indices to valid range
        np.clip(int_pos, 0, length - 1, out=int_pos)
        next_pos = int_pos + 1

        # Wrap next_pos for looping samples
        if self.loop and self.loop_length > 0:
            wrap_mask = next_pos >= length
            next_pos[wrap_mask] = self.loop_start
        else:
            np.clip(next_pos, 0, length - 1, out=next_pos)

        # Linear interpolation
        s0 = data[int_pos]
        s1 = data[next_pos]
        out = s0 + (s1 - s0) * frac

        # Update position
        self.position = self.position + num_frames * self.speed

        # Wrap position for next call
        if self.loop and self.loop_length > 0 and self.position >= length:
            self.position = (
                self.loop_start
                + (self.position - length) % self.loop_length
            )

        # Pad to requested size if we truncated due to sample end
        if len(out) < total_requested:
            out = np.pad(out, (0, total_requested - len(out)))

        return out
