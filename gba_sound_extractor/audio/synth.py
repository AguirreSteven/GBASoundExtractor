"""GBA software synthesizer — processes MP2K sequences and mixes audio.

Merges all track commands into a timeline, maintains per-track state,
creates SynthChannel voices for notes, and mixes to stereo output.
"""

import logging
import math

import numpy as np

from ..mp2k import commands as cmd
from ..mp2k.structures import Song, Instrument
from .samples import SampleCache
from .channel import SynthChannel, note_to_freq
from .psg import SquareWaveGenerator, NoiseGenerator, WaveGenerator

logger = logging.getLogger(__name__)

PPQN = 24
DEFAULT_BPM = 120
MAX_VOICES = 16


class TrackState:
    """Per-track playback state."""

    def __init__(self):
        self.instrument_index = 0
        self.volume = 127
        self.pan = 64
        self.pitch_bend = 0.0  # in semitones
        self.bend_range = 2
        self.key_shift = 0
        self.finished = False
        self.tied_voices: list[SynthChannel] = []


class GBASynth:
    """Processes an MP2K song sequence and renders audio."""

    def __init__(self, song: Song, sample_cache: SampleCache,
                 output_rate: int = 44100, rom=None):
        self.song = song
        self.sample_cache = sample_cache
        self.output_rate = output_rate
        self.rom = rom  # needed for PSG wave data

        self.bpm = DEFAULT_BPM
        self._samples_per_tick = self._calc_spt(self.bpm)

        # Build merged timeline: list of (tick, track_index, command)
        self._timeline = []
        for track in song.tracks:
            for command in track.commands:
                self._timeline.append((command.tick, track.index, command))
        self._timeline.sort(key=lambda x: (x[0], x[1]))

        self._timeline_pos = 0
        self._sample_pos = 0  # total output samples rendered

        # Tempo-aware tick→sample mapping:
        # _tempo_base_tick and _tempo_base_sample track the reference point
        # from which current samples_per_tick applies.
        self._tempo_base_tick = 0.0
        self._tempo_base_sample = 0

        # Per-track state
        self._tracks = {}
        for track in song.tracks:
            self._tracks[track.index] = TrackState()

        # Active voices
        self._voices: list[tuple[int, SynthChannel]] = []  # (track_idx, channel)

        # Pre-compute total length by walking tempo changes
        self.total_frames = self._estimate_total_frames()

        self.finished = False

    def _calc_spt(self, bpm: int) -> float:
        """Calculate samples per tick for given BPM."""
        if bpm <= 0:
            bpm = DEFAULT_BPM
        return (self.output_rate * 60.0) / (bpm * PPQN)

    def _tick_to_sample(self, tick: float) -> int:
        """Convert a tick position to an absolute sample position,
        accounting for tempo changes."""
        delta_ticks = tick - self._tempo_base_tick
        return self._tempo_base_sample + int(delta_ticks * self._samples_per_tick)

    def _estimate_total_frames(self) -> int:
        """Walk the timeline to compute accurate total length with tempo changes."""
        if not self._timeline:
            return 0
        cur_bpm = DEFAULT_BPM
        cur_spt = self._calc_spt(cur_bpm)
        base_tick = 0.0
        base_sample = 0
        last_tick = 0

        for tick, _, command in self._timeline:
            last_tick = tick
            if command.cmd_type == cmd.TEMPO and command.args:
                # Advance base to this point before changing tempo
                base_sample += int((tick - base_tick) * cur_spt)
                base_tick = tick
                cur_bpm = command.args[0] * 2
                if cur_bpm < 1:
                    cur_bpm = DEFAULT_BPM
                cur_spt = self._calc_spt(cur_bpm)

        total = base_sample + int((last_tick - base_tick) * cur_spt)
        return total + self.output_rate  # add 1s for release tails

    @property
    def total_seconds(self) -> float:
        return self.total_frames / self.output_rate if self.output_rate else 0.0

    def render_chunk(self, num_frames: int) -> np.ndarray:
        """Render num_frames of stereo audio. Returns (num_frames, 2) float32."""
        output = np.zeros((num_frames, 2), dtype=np.float32)

        if self.finished:
            return output

        frames_rendered = 0

        while frames_rendered < num_frames:
            # How many frames until the next event?
            frames_to_next = num_frames - frames_rendered

            if self._timeline_pos < len(self._timeline):
                next_tick = self._timeline[self._timeline_pos][0]
                next_sample = self._tick_to_sample(next_tick)
                frames_until_event = max(0, next_sample - self._sample_pos)
                frames_to_render = min(frames_to_next, frames_until_event)
            else:
                frames_to_render = frames_to_next

            if frames_to_render <= 0:
                frames_to_render = 0

            # Render active voices for this chunk
            if frames_to_render > 0:
                self._mix_voices(output, frames_rendered, frames_to_render)
                frames_rendered += frames_to_render
                self._sample_pos += frames_to_render

            # Process events at current position
            if self._timeline_pos < len(self._timeline):
                event_tick = self._timeline[self._timeline_pos][0]
                event_sample = self._tick_to_sample(event_tick)
                if self._sample_pos >= event_sample:
                    self._process_events_at_tick(event_tick)
                else:
                    continue
            else:
                # No more events — render remaining voices
                if not self._voices:
                    self.finished = True
                    break

        # Clean up finished voices
        self._voices = [(ti, v) for ti, v in self._voices if not v.finished]

        if (self._timeline_pos >= len(self._timeline)
                and not self._voices):
            self.finished = True

        return output

    def _process_events_at_tick(self, tick: int):
        """Process all timeline events at the given tick."""
        while (self._timeline_pos < len(self._timeline)
               and self._timeline[self._timeline_pos][0] == tick):
            _, track_idx, command = self._timeline[self._timeline_pos]
            self._timeline_pos += 1
            self._handle_command(track_idx, command)

    def _handle_command(self, track_idx: int, command):
        """Handle a single MP2K command."""
        ts = self._tracks.get(track_idx)
        if ts is None or ts.finished:
            return

        ct = command.cmd_type

        if ct == cmd.TEMPO:
            # Update tempo base point before changing rate
            event_tick = command.tick
            self._tempo_base_sample = self._tick_to_sample(event_tick)
            self._tempo_base_tick = event_tick
            self.bpm = command.args[0] * 2
            if self.bpm < 1:
                self.bpm = DEFAULT_BPM
            self._samples_per_tick = self._calc_spt(self.bpm)

        elif ct == cmd.VOICE:
            ts.instrument_index = command.args[0]

        elif ct == cmd.VOL:
            ts.volume = min(command.args[0], 127)

        elif ct == cmd.PAN:
            ts.pan = min(command.args[0], 127)

        elif ct == cmd.BEND:
            raw = command.args[0]
            ts.pitch_bend = ((raw - 64) / 64.0) * ts.bend_range

        elif ct == cmd.BENDR:
            ts.bend_range = command.args[0]

        elif ct == cmd.KEYSH:
            ts.key_shift = command.args[0]

        elif ct == cmd.TIE:
            # Sustained note
            key = command.args[0] + ts.key_shift if command.args else 60
            vel = min(command.args[1], 127) if len(command.args) > 1 else 127
            key = max(0, min(127, key))
            voice = self._create_voice(ts, key, vel, duration_frames=None)
            if voice is not None:
                voice._match_key = key  # integer key for EOT matching
                self._add_voice(track_idx, voice)
                ts.tied_voices.append(voice)

        elif ct == cmd.EOT:
            # Release tied notes
            if command.args:
                target_key = command.args[0] + ts.key_shift
                target_key = max(0, min(127, target_key))
                for v in ts.tied_voices:
                    match_key = getattr(v, '_match_key', None)
                    if match_key == target_key:
                        v.release()
                ts.tied_voices = [v for v in ts.tied_voices
                                  if not v._released]
            elif ts.tied_voices:
                ts.tied_voices[-1].release()
                ts.tied_voices.pop()

        elif cmd.NOTE_BASE <= ct <= cmd.NOTE_MAX:
            key = command.args[0] + ts.key_shift if command.args else 60
            vel = min(command.args[1], 127) if len(command.args) > 1 else 127
            duration_ticks = command.args[2] if len(command.args) > 2 else 1
            gate_adj = command.args[3] if len(command.args) > 3 else 0
            total_ticks = max(1, duration_ticks + gate_adj)
            key = max(0, min(127, key))

            duration_frames = int(total_ticks * self._samples_per_tick)
            voice = self._create_voice(ts, key, vel,
                                       duration_frames=duration_frames)
            if voice is not None:
                self._add_voice(track_idx, voice)

        elif ct == cmd.FINE:
            ts.finished = True
            # Release all tied voices on this track
            for v in ts.tied_voices:
                v.release()
            ts.tied_voices.clear()

    def _create_voice(self, ts: TrackState, note: int, velocity: int,
                      duration_frames=None):
        """Create a SynthChannel for the given note using the track's instrument."""
        instruments = self.song.instruments
        inst_idx = ts.instrument_index
        if inst_idx >= len(instruments):
            return None
        inst = instruments[inst_idx]
        # Apply pitch bend as fractional note offset
        bent_note = note + ts.pitch_bend
        return self._voice_from_instrument(inst, bent_note, velocity,
                                           duration_frames, ts)

    def _voice_from_instrument(self, inst: Instrument, note: int,
                               velocity: int, duration_frames,
                               ts: TrackState):
        """Create a voice from an instrument definition."""
        base_type = inst.type & 0x3F
        is_percussion = (inst.type & 0x80) != 0
        is_keysplit = (inst.type & 0x40) != 0

        # Keysplit/percussion: resolve to sub-instrument by note
        if (is_keysplit or is_percussion) and inst.sub_instruments:
            sub_idx = int(max(0, min(note, len(inst.sub_instruments) - 1)))
            sub = inst.sub_instruments[sub_idx]
            if sub is not None:
                return self._voice_from_instrument(
                    sub, note, velocity, duration_frames, ts)
            return None

        if base_type in (cmd.VOICE_DIRECT_SOUND, cmd.VOICE_DIRECT_SOUND_ALT):
            return self._create_pcm_voice(inst, note, velocity, duration_frames)

        elif base_type in (cmd.VOICE_SQUARE_1, cmd.VOICE_SQUARE_2):
            # Duty cycle from base_key field (common encoding)
            duty_idx = inst.base_key % 4 if inst.base_key < 4 else 2
            psg = SquareWaveGenerator(duty_idx)
            return SynthChannel(
                sample_data=None,
                sample_rate=0,
                base_key=60,
                note=note,
                velocity=velocity,
                adsr_params=inst.adsr,
                output_rate=self.output_rate,
                duration_frames=duration_frames,
                psg_generator=psg,
            )

        elif base_type == cmd.VOICE_NOISE:
            short = (inst.base_key & 1) != 0
            psg = NoiseGenerator(short_mode=short)
            return SynthChannel(
                sample_data=None,
                sample_rate=0,
                base_key=60,
                note=note,
                velocity=velocity,
                adsr_params=inst.adsr,
                output_rate=self.output_rate,
                duration_frames=duration_frames,
                psg_generator=psg,
            )

        elif base_type == cmd.VOICE_WAVE:
            if self.rom is not None and inst.sample is not None:
                try:
                    psg = WaveGenerator(self.rom, inst.sample.offset)
                    return SynthChannel(
                        sample_data=None,
                        sample_rate=0,
                        base_key=60,
                        note=note,
                        velocity=velocity,
                        adsr_params=inst.adsr,
                        output_rate=self.output_rate,
                        duration_frames=duration_frames,
                        psg_generator=psg,
                    )
                except Exception:
                    pass
            return None

        return None

    def _create_pcm_voice(self, inst: Instrument, note: int,
                          velocity: int, duration_frames):
        """Create a PCM (DirectSound) voice."""
        if inst.sample is None:
            return None

        sample = inst.sample
        sample_data = self.sample_cache.get(sample)
        if sample_data is None or len(sample_data) == 0:
            return None

        return SynthChannel(
            sample_data=sample_data,
            sample_rate=sample.sample_rate,
            base_key=inst.base_key,
            note=note,
            velocity=velocity,
            adsr_params=inst.adsr,
            output_rate=self.output_rate,
            duration_frames=duration_frames,
            loop=sample.loop,
            loop_start=sample.loop_start,
        )

    def _add_voice(self, track_idx: int, voice: SynthChannel):
        """Add a voice, stealing the oldest if over the limit."""
        if len(self._voices) >= MAX_VOICES:
            # Voice stealing: kill the oldest voice
            oldest = self._voices.pop(0)
            oldest[1].finished = True
        self._voices.append((track_idx, voice))

    def _mix_voices(self, output: np.ndarray, start: int, num_frames: int):
        """Mix all active voices into the output buffer."""
        for track_idx, voice in self._voices:
            if voice.finished:
                continue

            ts = self._tracks.get(track_idx)
            if ts is None:
                continue

            mono = voice.render(num_frames)

            # Apply track volume
            vol_gain = ts.volume / 127.0

            # Stereo panning (equal-power)
            pan_norm = ts.pan / 127.0
            left_gain = math.cos(pan_norm * math.pi / 2.0) * vol_gain
            right_gain = math.sin(pan_norm * math.pi / 2.0) * vol_gain

            end = start + num_frames
            output[start:end, 0] += mono * left_gain
            output[start:end, 1] += mono * right_gain
