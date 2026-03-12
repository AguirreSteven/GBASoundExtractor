"""Data structures for parsed MP2K song data."""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Sample:
    offset: int
    loop: bool
    loop_start: int
    length: int
    sample_rate: int
    data: bytes = field(default=b"", repr=False)


@dataclass
class Instrument:
    index: int
    type: int
    base_key: int
    pan: int
    sample: Optional[Sample]
    adsr: Tuple[int, int, int, int]  # (attack, decay, sustain, release)
    sub_instruments: Optional[List['Instrument']] = None


@dataclass
class Command:
    cmd_type: int       # Opcode
    tick: int           # Absolute tick position in the track
    args: tuple = ()    # Variable arguments per command type


@dataclass
class Track:
    index: int
    commands: List[Command] = field(default_factory=list)
    total_ticks: int = 0


@dataclass
class Song:
    index: int
    name: str
    num_tracks: int
    reverb: int
    priority: int
    voice_group_offset: int
    track_offsets: List[int] = field(default_factory=list)
    tracks: List[Track] = field(default_factory=list)
    instruments: List[Instrument] = field(default_factory=list)
    decoded: bool = False

    # --- Tag fields (populated by analysis.tagger) ---
    category: str = ""              # Music / SFX / Jingle / Fanfare
    tempo_bpm: int = 0              # Beats per minute
    tempo_label: str = ""           # Slow / Medium / Fast / Very Fast
    duration_secs: float = 0.0      # Estimated duration in seconds
    loop_status: str = ""           # Looping / One-shot
    instrument_profile: str = ""    # Melodic / Percussion-Heavy / Synth / Mixed / etc.
