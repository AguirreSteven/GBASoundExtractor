"""ADSR envelope processor matching MP2K sound engine behaviour.

MP2K updates envelopes once per frame (~59.7 Hz).  The raw byte parameters
work as follows (from m4a disassembly):

  Attack (0-255): per-frame additive increment to envelope level.
      level += attack  (integer 0-255 scale)
      attack=255 → instant, attack=1 → 255 frames to peak.

  Decay (0-255): per-frame multiplicative retention factor.
      level = (level * decay) >> 8
      decay=0 → instant drop, decay=255 → very slow (~99.6% per frame).

  Sustain (0-255): target level after decay (direct mapping).

  Release (0-255): same as decay — multiplicative retention toward zero.
      release=0 → instant silence, release=255 → very slow fade.
"""

import math

import numpy as np

# MP2K engine runs envelope updates at ~60 Hz (once per frame)
ENGINE_FRAME_RATE = 59.7275

# Threshold below which we consider the envelope silent
_SILENCE = 1e-5


class ADSREnvelope:
    """Generates per-sample gain values from MP2K ADSR parameters."""

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

        samples_per_frame = output_rate / ENGINE_FRAME_RATE

        # --- Attack: linear, additive ---
        # Per frame: level += attack/255.  Per sample: divide by samples_per_frame.
        if attack >= 255:
            self._attack_inc = 1.0  # instant
        elif attack == 0:
            # attack=0 means extremely slow; use a tiny increment so it
            # still eventually reaches peak (avoids division by zero).
            self._attack_inc = (1.0 / 255.0) / (samples_per_frame * 256)
        else:
            self._attack_inc = (attack / 255.0) / samples_per_frame

        # --- Sustain level ---
        self._sustain_level = sustain / 255.0

        # --- Decay: exponential (multiplicative) ---
        # Per frame: level *= (decay / 256).
        # Per sample: level *= (decay / 256) ^ (1 / samples_per_frame).
        if decay == 0:
            self._decay_mul = 0.0
        else:
            self._decay_mul = (decay / 256.0) ** (1.0 / samples_per_frame)

        # --- Release: exponential (multiplicative) ---
        if release == 0:
            self._release_mul = 0.0
        else:
            self._release_mul = (release / 256.0) ** (1.0 / samples_per_frame)

    def trigger_release(self):
        """Transition to release phase (called on note-off / EOT)."""
        if self.state != self.STATE_OFF:
            self.state = self.STATE_RELEASE

    def is_finished(self) -> bool:
        return self.state == self.STATE_OFF

    def advance(self, num_frames: int) -> np.ndarray:
        """Generate gain values for num_frames audio samples (vectorised)."""
        out = np.empty(num_frames, dtype=np.float32)
        pos = 0

        while pos < num_frames:
            remaining = num_frames - pos

            if self.state == self.STATE_ATTACK:
                if self._attack_inc >= 1.0:
                    # Instant attack
                    self.level = 1.0
                    self.state = self.STATE_DECAY
                    out[pos] = 1.0
                    pos += 1
                else:
                    n_to_peak = max(1, int(
                        (1.0 - self.level) / self._attack_inc))
                    n = min(remaining, n_to_peak)
                    ramp = self.level + np.arange(1, n + 1) * self._attack_inc
                    np.minimum(ramp, 1.0, out=ramp)
                    out[pos:pos + n] = ramp
                    self.level = float(ramp[-1])
                    pos += n
                    if self.level >= 1.0:
                        self.level = 1.0
                        self.state = self.STATE_DECAY

            elif self.state == self.STATE_DECAY:
                if self._decay_mul <= 0.0:
                    # Instant decay to sustain
                    self.level = self._sustain_level
                    self.state = self.STATE_SUSTAIN
                    out[pos] = self._sustain_level
                    pos += 1
                elif self.level <= self._sustain_level:
                    self.level = self._sustain_level
                    self.state = self.STATE_SUSTAIN
                    continue
                else:
                    # Exponential decay toward sustain
                    # Find how many samples until level reaches sustain
                    if self._sustain_level > _SILENCE:
                        ratio = self._sustain_level / self.level
                        n_to_sus = max(1, int(math.log(ratio)
                                              / math.log(self._decay_mul)))
                    else:
                        n_to_sus = remaining
                    n = min(remaining, n_to_sus)
                    exponents = np.arange(1, n + 1, dtype=np.float64)
                    ramp = (self.level
                            * (self._decay_mul ** exponents)).astype(np.float32)
                    np.maximum(ramp, self._sustain_level, out=ramp)
                    out[pos:pos + n] = ramp
                    self.level = float(ramp[-1])
                    pos += n
                    if self.level <= self._sustain_level + _SILENCE:
                        self.level = self._sustain_level
                        self.state = self.STATE_SUSTAIN

            elif self.state == self.STATE_SUSTAIN:
                out[pos:] = self._sustain_level
                pos = num_frames

            elif self.state == self.STATE_RELEASE:
                if self._release_mul <= 0.0 or self.level <= _SILENCE:
                    self.level = 0.0
                    self.state = self.STATE_OFF
                    out[pos:] = 0.0
                    pos = num_frames
                else:
                    # Exponential release toward zero
                    n_to_zero = max(1, int(math.log(_SILENCE / self.level)
                                          / math.log(self._release_mul)))
                    n = min(remaining, n_to_zero)
                    exponents = np.arange(1, n + 1, dtype=np.float64)
                    ramp = (self.level
                            * (self._release_mul ** exponents)).astype(
                                np.float32)
                    np.maximum(ramp, 0.0, out=ramp)
                    out[pos:pos + n] = ramp
                    self.level = float(ramp[-1])
                    pos += n
                    if self.level <= _SILENCE:
                        self.level = 0.0
                        self.state = self.STATE_OFF

            else:  # STATE_OFF
                out[pos:] = 0.0
                pos = num_frames

        return out
