"""ADSR envelope processor matching MP2K sound engine behaviour."""

import numpy as np

# MP2K engine runs envelope updates at ~60 Hz (once per frame)
ENGINE_FRAME_RATE = 59.7275


class ADSREnvelope:
    """Generates per-sample gain values from MP2K ADSR parameters.

    MP2K ADSR values (0-255):
    - attack:  higher = faster attack (255 = instant)
    - decay:   higher = faster decay
    - sustain: sustain level (0-255, maps to 0.0-1.0)
    - release: higher = faster release (255 = instant)
    """

    STATE_ATTACK = 0
    STATE_DECAY = 1
    STATE_SUSTAIN = 2
    STATE_RELEASE = 3
    STATE_OFF = 4

    def __init__(self, attack: int, decay: int, sustain: int, release: int,
                 output_rate: int = 44100):
        self.output_rate = output_rate
        self.state = self.STATE_ATTACK
        self.level = 0.0

        # Convert MP2K frame-based rates to per-sample increments
        samples_per_frame = output_rate / ENGINE_FRAME_RATE

        # Attack: ramp from 0 to 1.0
        # MP2K: attack=255 is instant, lower values are slower
        if attack >= 255:
            self._attack_rate = 1.0  # instant
        elif attack == 0:
            self._attack_rate = 1.0 / (samples_per_frame * 256)
        else:
            frames = max(1, 256 - attack)
            self._attack_rate = 1.0 / (samples_per_frame * frames)

        # Decay: ramp from 1.0 down to sustain level
        if decay >= 255:
            self._decay_rate = 1.0
        elif decay == 0:
            self._decay_rate = 1.0 / (samples_per_frame * 256)
        else:
            frames = max(1, 256 - decay)
            self._decay_rate = 1.0 / (samples_per_frame * frames)

        # Sustain level
        self._sustain_level = sustain / 255.0

        # Release: ramp from current level to 0
        if release >= 255:
            self._release_rate = 1.0
        elif release == 0:
            self._release_rate = 1.0 / (samples_per_frame * 256)
        else:
            frames = max(1, 256 - release)
            self._release_rate = 1.0 / (samples_per_frame * frames)

    def trigger_release(self):
        """Transition to release phase (called on note-off / EOT)."""
        if self.state != self.STATE_OFF:
            self.state = self.STATE_RELEASE

    def is_finished(self) -> bool:
        return self.state == self.STATE_OFF

    def advance(self, num_frames: int) -> np.ndarray:
        """Generate gain values for num_frames audio samples."""
        out = np.empty(num_frames, dtype=np.float32)
        i = 0

        while i < num_frames:
            if self.state == self.STATE_ATTACK:
                self.level += self._attack_rate
                if self.level >= 1.0:
                    self.level = 1.0
                    self.state = self.STATE_DECAY
                out[i] = self.level

            elif self.state == self.STATE_DECAY:
                self.level -= self._decay_rate
                if self.level <= self._sustain_level:
                    self.level = self._sustain_level
                    self.state = self.STATE_SUSTAIN
                out[i] = self.level

            elif self.state == self.STATE_SUSTAIN:
                out[i] = self._sustain_level

            elif self.state == self.STATE_RELEASE:
                self.level -= self._release_rate
                if self.level <= 0.0:
                    self.level = 0.0
                    self.state = self.STATE_OFF
                out[i] = self.level

            else:  # STATE_OFF
                out[i:] = 0.0
                break

            i += 1

        return out
