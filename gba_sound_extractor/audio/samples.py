"""Load and cache PCM sample data from GBA ROM as numpy float32 arrays."""

import logging

import numpy as np

from ..rom.reader import ROMReader
from ..mp2k.structures import Sample

logger = logging.getLogger(__name__)


class SampleCache:
    """Loads 8-bit signed PCM samples from ROM and caches as float32 arrays."""

    def __init__(self, rom: ROMReader):
        self.rom = rom
        self._cache: dict[int, np.ndarray | None] = {}

    def get(self, sample: Sample) -> np.ndarray | None:
        """Return float32 array normalised to [-1.0, 1.0] for a Sample.

        Returns None if the sample cannot be read from ROM.
        """
        if sample.offset in self._cache:
            return self._cache[sample.offset]
        try:
            raw = self.rom.read_bytes(sample.offset, sample.length)
            if not raw:
                self._cache[sample.offset] = None
                return None
            arr = np.frombuffer(raw, dtype=np.int8).astype(np.float32) / 128.0
            self._cache[sample.offset] = arr
            return arr
        except Exception as e:
            logger.debug("Failed to load sample at 0x%X: %s",
                         sample.offset, e)
            self._cache[sample.offset] = None
            return None

    def clear(self):
        self._cache.clear()
