"""Convert decoded MP2K songs to MIDI files using mido."""

import logging

import mido

from ..mp2k import commands as cmd
from ..mp2k.structures import Song

logger = logging.getLogger(__name__)

# MP2K sequencer uses 24 pulses per quarter note
PPQN = 24
DEFAULT_BPM = 120


def convert_song_to_midi(song: Song) -> mido.MidiFile:
    """Convert a decoded Song to a mido MidiFile.

    The song must have its tracks decoded (song.decoded == True).
    """
    mid = mido.MidiFile(ticks_per_beat=PPQN, type=1)

    for track in song.tracks:
        midi_track = mido.MidiTrack()
        mid.tracks.append(midi_track)

        # Assign MIDI channel: skip channel 10 (drums) for melodic tracks
        ch = track.index
        if ch >= 9:
            ch += 1
        ch = ch % 16

        # Add track name
        midi_track.append(mido.MetaMessage(
            "track_name", name=f"Track {track.index}", time=0))

        _convert_track(midi_track, track, ch)

    return mid


def _convert_track(midi_track: mido.MidiTrack, track, channel: int):
    """Convert a single Track's commands to MIDI messages."""
    prev_tick = 0
    transpose = 0
    # Track active TIE notes for EOT note-off
    tied_notes = []
    # Scheduled note-offs: list of (tick, note) sorted by tick
    pending_offs = []

    for command in track.commands:
        # Flush any pending note-offs that should happen at or before this tick
        prev_tick = _flush_note_offs(midi_track, pending_offs,
                                     command.tick, prev_tick, channel)

        delta = command.tick - prev_tick
        prev_tick = command.tick

        ct = command.cmd_type

        if ct == cmd.TEMPO:
            bpm = command.args[0] * 2
            if bpm < 1:
                bpm = DEFAULT_BPM
            midi_track.append(mido.MetaMessage(
                "set_tempo", tempo=mido.bpm2tempo(bpm), time=delta))
            delta = 0

        elif ct == cmd.VOICE:
            midi_track.append(mido.Message(
                "program_change", channel=channel,
                program=min(command.args[0], 127), time=delta))
            delta = 0

        elif ct == cmd.VOL:
            midi_track.append(mido.Message(
                "control_change", channel=channel,
                control=7, value=min(command.args[0], 127), time=delta))
            delta = 0

        elif ct == cmd.PAN:
            midi_track.append(mido.Message(
                "control_change", channel=channel,
                control=10, value=min(command.args[0], 127), time=delta))
            delta = 0

        elif ct == cmd.BEND:
            # MP2K bend: 0-127, center=64. MIDI pitchwheel: -8192 to 8191
            raw = command.args[0]
            pitch = int((raw - 64) * (8192 / 64))
            pitch = max(-8192, min(8191, pitch))
            midi_track.append(mido.Message(
                "pitchwheel", channel=channel,
                pitch=pitch, time=delta))
            delta = 0

        elif ct == cmd.BENDR:
            # Set pitch bend range via RPN 0
            val = command.args[0]
            for msg in _rpn_pitch_bend_range(channel, val, delta):
                midi_track.append(msg)
                delta = 0

        elif ct == cmd.MOD:
            midi_track.append(mido.Message(
                "control_change", channel=channel,
                control=1, value=min(command.args[0], 127), time=delta))
            delta = 0

        elif ct == cmd.KEYSH:
            transpose = command.args[0]
            # No MIDI message emitted; applied to note values

        elif ct == cmd.TIE:
            # Note on, sustained until EOT
            key = _clamp_note(command.args[0] + transpose)
            vel = min(command.args[1], 127) if len(command.args) > 1 else 127
            midi_track.append(mido.Message(
                "note_on", channel=channel,
                note=key, velocity=vel, time=delta))
            delta = 0
            tied_notes.append(key)

        elif ct == cmd.EOT:
            # Note off for tied notes
            key = _clamp_note(command.args[0] + transpose) \
                if command.args else None
            if key is not None and key in tied_notes:
                midi_track.append(mido.Message(
                    "note_off", channel=channel,
                    note=key, velocity=0, time=delta))
                delta = 0
                tied_notes.remove(key)
            elif tied_notes:
                # Turn off the most recent tied note
                off_key = tied_notes.pop()
                midi_track.append(mido.Message(
                    "note_off", channel=channel,
                    note=off_key, velocity=0, time=delta))
                delta = 0

        elif cmd.NOTE_BASE <= ct <= cmd.NOTE_MAX:
            # Timed note: args = (key, vel, duration, gate_adjust)
            key = _clamp_note(command.args[0] + transpose)
            vel = min(command.args[1], 127) if len(command.args) > 1 else 127
            duration = command.args[2] if len(command.args) > 2 else 1
            gate_adj = command.args[3] if len(command.args) > 3 else 0
            total_dur = max(1, duration + gate_adj)

            midi_track.append(mido.Message(
                "note_on", channel=channel,
                note=key, velocity=vel, time=delta))
            delta = 0

            off_tick = command.tick + total_dur
            pending_offs.append((off_tick, key))
            pending_offs.sort(key=lambda x: x[0])

        elif ct == cmd.FINE:
            # End of track — flush everything
            prev_tick = _flush_note_offs(midi_track, pending_offs,
                                        command.tick + 9999, prev_tick,
                                        channel)
            for note in tied_notes:
                d = 0
                midi_track.append(mido.Message(
                    "note_off", channel=channel,
                    note=note, velocity=0, time=d))
            tied_notes.clear()

        # Commands we skip for MIDI export:
        # LFOS, LFODL, MODT, TUNE, XCMD, PRIO, REPT

    # Flush remaining note-offs
    _flush_note_offs(midi_track, pending_offs,
                     prev_tick + 9999, prev_tick, channel)
    for note in tied_notes:
        midi_track.append(mido.Message(
            "note_off", channel=channel,
            note=note, velocity=0, time=0))

    midi_track.append(mido.MetaMessage("end_of_track", time=0))


def _flush_note_offs(midi_track, pending_offs, up_to_tick,
                     prev_tick, channel):
    """Emit note-off messages for notes ending at or before up_to_tick."""
    while pending_offs and pending_offs[0][0] <= up_to_tick:
        off_tick, note = pending_offs.pop(0)
        delta = max(0, off_tick - prev_tick)
        midi_track.append(mido.Message(
            "note_off", channel=channel,
            note=note, velocity=0, time=delta))
        prev_tick = off_tick
    return prev_tick


def _rpn_pitch_bend_range(channel, semitones, first_delta):
    """Generate RPN messages to set pitch bend range."""
    return [
        mido.Message("control_change", channel=channel,
                     control=101, value=0, time=first_delta),
        mido.Message("control_change", channel=channel,
                     control=100, value=0, time=0),
        mido.Message("control_change", channel=channel,
                     control=6, value=min(semitones, 127), time=0),
        mido.Message("control_change", channel=channel,
                     control=38, value=0, time=0),
    ]


def _clamp_note(value):
    """Clamp a note value to MIDI range 0-127."""
    return max(0, min(127, value))
