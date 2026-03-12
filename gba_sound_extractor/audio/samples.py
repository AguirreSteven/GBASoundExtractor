"""Load and cache PCM sample data from GBA ROM as numpy float32 arrays."""

import numpy as np

from ..rom.reader import ROMReader
from ..mp2k.structures import Sample


class SampleCache:
    """Loads 8-bit signed PCM samples from ROM and caches as float32 arrays."""

    def __init__(self, rom: ROMReader):
        self.rom = rom
        self._cache: dict[int, np.ndarray] = {}

    def get(self, sample: Sample) -> np.ndarray:
        """Return float32 array normalised to [-1.0, 1.0] for a Sample."""
        if sample.offset in self._cache:
            return self._cache[sample.offset]
        raw = self.rom.read_bytes(sample.offset, sample.length)
        arr = np.frombuffer(raw, dtype=np.int8).astype(np.float32) / 128.0
        self._cache[sample.offset] = arr
        return arr

    def clear(self):
        self._cache.clear()
