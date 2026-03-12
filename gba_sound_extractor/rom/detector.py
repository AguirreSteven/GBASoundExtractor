"""Song table auto-detection for MP2K GBA ROMs."""

import logging
from typing import List, Tuple

from .reader import ROMReader

logger = logging.getLogger(__name__)


class SongTableCandidate:
    """A candidate song table found in the ROM."""

    def __init__(self, offset: int, count: int, confidence: float = 0.0):
        self.offset = offset
        self.count = count
        self.confidence = confidence

    def __repr__(self):
        return (f"SongTableCandidate(offset=0x{self.offset:06X}, "
                f"count={self.count}, confidence={self.confidence:.2f})")


def detect_song_tables(rom: ROMReader,
                       min_songs: int = 4) -> List[SongTableCandidate]:
    """Detect song table candidates in the ROM.

    Uses a pointer-column heuristic: scans for runs of 8-byte entries
    where the first 4 bytes are a valid ROM pointer that targets a
    plausible song header.

    Args:
        rom: The loaded ROM.
        min_songs: Minimum number of consecutive valid entries to
            consider a candidate.

    Returns:
        List of candidates sorted by confidence (highest first).
    """
    candidates = []
    rom_size = rom.size
    checked = set()

    # Scan with 4-byte alignment
    for offset in range(0, rom_size - 8, 4):
        if offset in checked:
            continue

        ptr_raw = rom.read_u32(offset)
        if not rom.is_valid_ptr(ptr_raw):
            continue

        header_off = rom.ptr_to_offset(ptr_raw)
        if not _is_plausible_song_header(rom, header_off):
            continue

        # Found a potential first entry — count consecutive valid entries
        count = 0
        scan = offset
        while scan + 7 < rom_size:
            entry_ptr_raw = rom.read_u32(scan)
            if not rom.is_valid_ptr(entry_ptr_raw):
                break
            target = rom.ptr_to_offset(entry_ptr_raw)
            if not _is_plausible_song_header(rom, target):
                break
            count += 1
            checked.add(scan)
            scan += 8

        if count >= min_songs:
            confidence = _score_candidate(rom, offset, count)
            candidates.append(SongTableCandidate(offset, count, confidence))

    candidates.sort(key=lambda c: c.confidence, reverse=True)
    logger.info("Found %d song table candidate(s)", len(candidates))
    for c in candidates[:5]:
        logger.info("  %s", c)
    return candidates


def _is_plausible_song_header(rom: ROMReader, offset: int) -> bool:
    """Check if the data at offset looks like a valid MP2K song header.

    Song header layout:
        byte 0: num_tracks (1-16)
        byte 1: unknown (usually 0)
        byte 2: priority
        byte 3: reverb
        bytes 4-7: voice_group_ptr (valid ROM pointer)
        bytes 8+: track pointers (num_tracks * 4 bytes)
    """
    if offset < 0 or offset + 8 > rom.size:
        return False

    num_tracks = rom.read_u8(offset)
    if num_tracks < 1 or num_tracks > 16:
        return False

    # byte 1 is typically 0
    unknown = rom.read_u8(offset + 1)
    if unknown != 0:
        return False

    voice_ptr_raw = rom.read_u32(offset + 4)
    if not rom.is_valid_ptr(voice_ptr_raw):
        return False

    # Check that we have enough room for all track pointers
    tracks_end = offset + 8 + num_tracks * 4
    if tracks_end > rom.size:
        return False

    # Validate at least the first track pointer
    first_track_ptr = rom.read_u32(offset + 8)
    if not rom.is_valid_ptr(first_track_ptr):
        return False

    return True


def _score_candidate(rom: ROMReader, offset: int, count: int) -> float:
    """Score a song table candidate by how many entries have valid details.

    Higher scores indicate higher confidence.
    """
    score = 0.0
    valid_detailed = 0

    for i in range(min(count, 50)):  # Sample up to 50 entries
        entry_off = offset + i * 8
        ptr_raw = rom.read_u32(entry_off)
        header_off = rom.ptr_to_offset(ptr_raw)

        num_tracks = rom.read_u8(header_off)
        if num_tracks < 1 or num_tracks > 16:
            continue

        # Check all track pointers are valid
        all_valid = True
        for t in range(num_tracks):
            tp = rom.read_u32(header_off + 8 + t * 4)
            if not rom.is_valid_ptr(tp):
                all_valid = False
                break

        if all_valid:
            valid_detailed += 1

    # Score based on total count and validation rate
    if count > 0:
        validation_rate = valid_detailed / min(count, 50)
        score = count * validation_rate
    return score
