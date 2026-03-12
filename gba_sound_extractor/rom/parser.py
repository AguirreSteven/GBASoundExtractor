"""Parse MP2K song headers, voice groups, and samples from ROM data."""

import logging
from typing import List, Optional

from .reader import ROMReader
from ..mp2k import commands as cmd
from ..mp2k.structures import Song, Instrument, Sample

logger = logging.getLogger(__name__)


def parse_song_list(rom: ROMReader, table_offset: int,
                    song_count: int) -> List[Song]:
    """Parse the song table and return Song objects with metadata only.

    Does NOT decode track sequences (lazy — done on demand).
    """
    songs = []
    for i in range(song_count):
        entry_offset = table_offset + i * 8
        header_ptr = rom.read_ptr(entry_offset)
        if header_ptr < 0:
            continue

        song = _parse_song_header(rom, header_ptr, i)
        if song is not None:
            songs.append(song)

    logger.info("Parsed %d songs from table at 0x%06X", len(songs), table_offset)
    return songs


def _parse_song_header(rom: ROMReader, offset: int,
                       index: int) -> Optional[Song]:
    """Parse a single song header."""
    if offset + 8 > rom.size:
        return None

    num_tracks = rom.read_u8(offset)
    if num_tracks < 1 or num_tracks > 16:
        return None

    priority = rom.read_u8(offset + 2)
    reverb = rom.read_u8(offset + 3)
    voice_group_ptr = rom.read_ptr(offset + 4)

    track_offsets = []
    for t in range(num_tracks):
        tp = rom.read_ptr(offset + 8 + t * 4)
        if tp < 0:
            return None
        track_offsets.append(tp)

    return Song(
        index=index,
        name=f"Song {index:03d}",
        num_tracks=num_tracks,
        reverb=reverb,
        priority=priority,
        voice_group_offset=voice_group_ptr,
        track_offsets=track_offsets,
        decoded=False,
    )


def parse_voice_group(rom: ROMReader,
                      offset: int) -> List[Instrument]:
    """Parse a voice group (instrument bank) of up to 128 instruments."""
    instruments = []
    for i in range(128):
        inst_offset = offset + i * 12
        if inst_offset + 12 > rom.size:
            break

        inst_type = rom.read_u8(inst_offset)
        base_key = rom.read_u8(inst_offset + 1)
        # byte 2 is unused/length
        pan = rom.read_u8(inst_offset + 3)

        sample_ptr_raw = rom.read_u32(inst_offset + 4)
        attack = rom.read_u8(inst_offset + 8)
        decay = rom.read_u8(inst_offset + 9)
        sustain = rom.read_u8(inst_offset + 10)
        release = rom.read_u8(inst_offset + 11)

        sample = None
        sub_instruments = None
        base_type = inst_type & 0x3F
        is_keysplit = (inst_type & 0x40) != 0
        is_percussion = (inst_type & 0x80) != 0

        if is_keysplit or is_percussion:
            # Keysplit/percussion: sample_ptr points to a sub-instrument table
            # We store the pointer raw for the synth to resolve later
            if rom.is_valid_ptr(sample_ptr_raw):
                sub_offset = rom.ptr_to_offset(sample_ptr_raw)
                sub_instruments = _parse_sub_instruments(
                    rom, sub_offset, is_percussion)
        elif base_type in (cmd.VOICE_DIRECT_SOUND,
                           cmd.VOICE_DIRECT_SOUND_ALT):
            if rom.is_valid_ptr(sample_ptr_raw):
                sample_off = rom.ptr_to_offset(sample_ptr_raw)
                sample = _parse_sample_header(rom, sample_off)
        elif base_type == cmd.VOICE_WAVE:
            # Wave channel: sample_ptr points to 16-byte wavetable
            if rom.is_valid_ptr(sample_ptr_raw):
                wave_off = rom.ptr_to_offset(sample_ptr_raw)
                # Store offset in a Sample object for the synth to find
                sample = Sample(
                    offset=wave_off, loop=True, loop_start=0,
                    length=16, sample_rate=0, data=b"")
        # Square and Noise don't use sample pointers

        instruments.append(Instrument(
            index=i,
            type=inst_type,
            base_key=base_key,
            pan=pan,
            sample=sample,
            adsr=(attack, decay, sustain, release),
            sub_instruments=sub_instruments,
        ))

    return instruments


def _parse_sub_instruments(rom: ROMReader, offset: int,
                           is_percussion: bool) -> List[Instrument]:
    """Parse a keysplit/percussion sub-instrument table (128 entries)."""
    subs = []
    for i in range(128):
        sub_off = offset + i * 12
        if sub_off + 12 > rom.size:
            break

        sub_type = rom.read_u8(sub_off)
        sub_base_key = rom.read_u8(sub_off + 1)
        sub_pan = rom.read_u8(sub_off + 3)
        sub_sample_ptr = rom.read_u32(sub_off + 4)
        sub_attack = rom.read_u8(sub_off + 8)
        sub_decay = rom.read_u8(sub_off + 9)
        sub_sustain = rom.read_u8(sub_off + 10)
        sub_release = rom.read_u8(sub_off + 11)

        sub_sample = None
        sub_base_type = sub_type & 0x3F
        if sub_base_type in (cmd.VOICE_DIRECT_SOUND,
                             cmd.VOICE_DIRECT_SOUND_ALT):
            if rom.is_valid_ptr(sub_sample_ptr):
                sample_off = rom.ptr_to_offset(sub_sample_ptr)
                sub_sample = _parse_sample_header(rom, sample_off)
        elif sub_base_type == cmd.VOICE_WAVE:
            if rom.is_valid_ptr(sub_sample_ptr):
                wave_off = rom.ptr_to_offset(sub_sample_ptr)
                sub_sample = Sample(
                    offset=wave_off, loop=True, loop_start=0,
                    length=16, sample_rate=0, data=b"")

        subs.append(Instrument(
            index=i,
            type=sub_type,
            base_key=sub_base_key,
            pan=sub_pan,
            sample=sub_sample,
            adsr=(sub_attack, sub_decay, sub_sustain, sub_release),
        ))

    return subs


def _parse_sample_header(rom: ROMReader,
                         offset: int) -> Optional[Sample]:
    """Parse a PCM sample header (16 bytes) and optionally load data."""
    if offset + 16 > rom.size:
        return None

    loop_flag = rom.read_u8(offset + 3)
    is_loop = (loop_flag & 0x40) != 0

    pitch_adjust = rom.read_u32(offset + 4)
    loop_start = rom.read_u32(offset + 8)
    sample_length = rom.read_u32(offset + 12)

    # Sanity check
    if sample_length == 0 or sample_length > 0x100000:
        return None

    # Derive approximate sample rate from pitch_adjust
    # pitch_adjust is a fixed-point value; base rate ~= pitch_adjust / 1024
    sample_rate = max(1, pitch_adjust >> 10) if pitch_adjust > 0 else 8000

    data_offset = offset + 16
    if data_offset + sample_length > rom.size:
        sample_length = rom.size - data_offset

    return Sample(
        offset=data_offset,
        loop=is_loop,
        loop_start=loop_start,
        length=sample_length,
        sample_rate=sample_rate,
        data=b"",  # Load on demand to save memory
    )
