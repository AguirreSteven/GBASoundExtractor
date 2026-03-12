"""Auto-tagger for MP2K songs — derives category, tempo, duration, loop
status, and instrument profile from decoded song data."""

import logging
from ..mp2k import commands as cmd
from ..mp2k.structures import Song

logger = logging.getLogger(__name__)

# Tempo label thresholds (BPM)
_TEMPO_SLOW = 80
_TEMPO_MEDIUM = 120
_TEMPO_FAST = 160

# Duration thresholds (seconds) for category classification
_DUR_SFX = 1.0
_DUR_JINGLE = 5.0

# Channel count threshold for SFX vs Music
_TRACKS_SFX = 2

# PPQN used by the MP2K engine / our MIDI converter
_PPQN = 24


def tag_song(song: Song) -> None:
    """Analyse a decoded Song and populate its tag fields in-place.

    The song MUST have ``decoded == True`` (tracks filled with Commands)
    before calling this function.
    """
    if not song.decoded:
        return

    bpm = _extract_bpm(song)
    song.tempo_bpm = bpm
    song.tempo_label = _tempo_label(bpm)

    total_ticks = _max_track_ticks(song)
    song.duration_secs = _ticks_to_seconds(total_ticks, bpm)

    song.loop_status = _detect_loop_status(song)
    song.instrument_profile = _detect_instrument_profile(song)
    song.category = _classify_category(song)


# ------------------------------------------------------------------
# BPM extraction
# ------------------------------------------------------------------

def _extract_bpm(song: Song) -> int:
    """Return the first TEMPO value found across all tracks (as BPM).

    MP2K stores tempo as half-BPM, so actual BPM = value * 2.
    Falls back to 120 BPM if no TEMPO command is present.
    """
    for track in song.tracks:
        for command in track.commands:
            if command.cmd_type == cmd.TEMPO and command.args:
                return command.args[0] * 2
    return 120  # sensible default


def _tempo_label(bpm: int) -> str:
    if bpm < _TEMPO_SLOW:
        return "Slow"
    if bpm < _TEMPO_MEDIUM:
        return "Medium"
    if bpm < _TEMPO_FAST:
        return "Fast"
    return "Very Fast"


# ------------------------------------------------------------------
# Duration estimation
# ------------------------------------------------------------------

def _max_track_ticks(song: Song) -> int:
    """Return the largest total_ticks across all tracks."""
    if not song.tracks:
        return 0
    return max(t.total_ticks for t in song.tracks)


def _ticks_to_seconds(ticks: int, bpm: int) -> float:
    """Convert ticks to seconds using PPQN and BPM."""
    if bpm <= 0:
        bpm = 120
    seconds_per_tick = 60.0 / (bpm * _PPQN)
    return ticks * seconds_per_tick


# ------------------------------------------------------------------
# Loop detection
# ------------------------------------------------------------------

def _detect_loop_status(song: Song) -> str:
    """Check if any track contains a GOTO command (= looping)."""
    for track in song.tracks:
        for command in track.commands:
            if command.cmd_type == cmd.GOTO:
                return "Looping"
    # Also check if the track ends with FINE — one-shot
    return "One-shot"


# ------------------------------------------------------------------
# Instrument profile
# ------------------------------------------------------------------

def _detect_instrument_profile(song: Song) -> str:
    """Classify the instrument palette used by the song.

    Looks at VOICE commands across all tracks and cross-references
    with the song's instrument list (if parsed).  Falls back to
    heuristics based on the voice-type constants.
    """
    voice_indices: set[int] = set()
    for track in song.tracks:
        for command in track.commands:
            if command.cmd_type == cmd.VOICE and command.args:
                voice_indices.add(command.args[0])

    if not voice_indices:
        return "Unknown"

    # If we have parsed instruments, classify by type
    if song.instruments:
        direct = 0
        square_wave = 0
        noise = 0
        percussion = 0

        for idx in voice_indices:
            if idx < len(song.instruments):
                inst = song.instruments[idx]
                base_type = inst.type & 0x3F
                if inst.type & 0x80:
                    percussion += 1
                elif base_type in (cmd.VOICE_DIRECT_SOUND,
                                   cmd.VOICE_DIRECT_SOUND_ALT):
                    direct += 1
                elif base_type in (cmd.VOICE_SQUARE_1, cmd.VOICE_SQUARE_2,
                                   cmd.VOICE_WAVE):
                    square_wave += 1
                elif base_type == cmd.VOICE_NOISE:
                    noise += 1
                else:
                    direct += 1  # default
            else:
                direct += 1

        total = direct + square_wave + noise + percussion
        if total == 0:
            return "Unknown"

        if percussion / total >= 0.6:
            return "Percussion-Heavy"
        if square_wave / total >= 0.5:
            return "Synth/Chiptune"
        if noise / total >= 0.4:
            return "Noise/Synth"
        if direct / total >= 0.5:
            return "Melodic"
        return "Mixed"

    # No instrument data available — guess from track count
    if song.num_tracks <= 2:
        return "Simple"
    return "Mixed"


# ------------------------------------------------------------------
# Category classification
# ------------------------------------------------------------------

def _classify_category(song: Song) -> str:
    """Classify a song as Music, SFX, Jingle, or Fanfare."""
    dur = song.duration_secs
    tracks = song.num_tracks
    looping = song.loop_status == "Looping"

    # Very short, few channels → SFX
    if dur < _DUR_SFX and tracks <= _TRACKS_SFX:
        return "SFX"

    # Short one-shot with few channels → Jingle
    if dur < _DUR_JINGLE and not looping and tracks <= 4:
        return "Jingle"

    # Short looping with moderate channels → Fanfare
    if dur < _DUR_JINGLE and looping and tracks <= 4:
        return "Fanfare"

    # Medium/long one-shot → Fanfare (e.g. victory fanfares)
    if _DUR_JINGLE <= dur < 15.0 and not looping:
        return "Fanfare"

    # Everything else → Music
    return "Music"
