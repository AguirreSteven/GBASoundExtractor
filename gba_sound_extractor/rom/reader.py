"""GBA ROM file reader with binary access helpers."""

import struct


class ROMReader:
    """Loads a GBA ROM and provides helper methods for reading binary data."""

    GBA_PTR_BASE = 0x08000000
    GBA_PTR_MASK = 0x01FFFFFF
    MIN_ROM_SIZE = 256 * 1024       # 256 KB
    MAX_ROM_SIZE = 32 * 1024 * 1024  # 32 MB

    def __init__(self, filepath: str):
        with open(filepath, "rb") as f:
            self.data = bytearray(f.read())
        self.size = len(self.data)
        self.filepath = filepath

    def validate(self) -> bool:
        """Check basic GBA ROM validity."""
        if self.size < self.MIN_ROM_SIZE:
            return False
        if self.size > self.MAX_ROM_SIZE:
            return False
        # Check for fixed GBA header value at offset 0xB2
        # (this byte is always 0x96 in valid GBA ROMs)
        if self.size > 0xB2 and self.data[0xB2] != 0x96:
            return False
        return True

    def game_title(self) -> str:
        """Read the 12-byte game title from the GBA header."""
        if self.size < 0xAC:
            return "Unknown"
        raw = self.data[0xA0:0xAC]
        return raw.decode("ascii", errors="replace").rstrip("\x00 ")

    def game_code(self) -> str:
        """Read the 4-byte game code from the GBA header."""
        if self.size < 0xB0:
            return "????"
        raw = self.data[0xAC:0xB0]
        return raw.decode("ascii", errors="replace").rstrip("\x00")

    def read_u8(self, offset: int) -> int:
        if offset < 0 or offset >= self.size:
            return 0
        return self.data[offset]

    def read_u16(self, offset: int) -> int:
        if offset < 0 or offset + 1 >= self.size:
            return 0
        return struct.unpack_from("<H", self.data, offset)[0]

    def read_u32(self, offset: int) -> int:
        if offset < 0 or offset + 3 >= self.size:
            return 0
        return struct.unpack_from("<I", self.data, offset)[0]

    def read_s8(self, offset: int) -> int:
        if offset < 0 or offset >= self.size:
            return 0
        return struct.unpack_from("<b", self.data, offset)[0]

    def read_ptr(self, offset: int) -> int:
        """Read a 32-bit GBA pointer and convert to ROM file offset.

        GBA pointers are OR'd with 0x08000000. This masks that off
        to get the actual file offset. Returns -1 if the pointer
        is invalid.
        """
        raw = self.read_u32(offset)
        if not self.is_valid_ptr(raw):
            return -1
        return raw & self.GBA_PTR_MASK

    def is_valid_ptr(self, value: int) -> bool:
        """Check if a 32-bit value is a valid GBA ROM pointer."""
        # High byte must be 0x08 or 0x09 (for ROMs > 16MB)
        high_byte = (value >> 24) & 0xFF
        if high_byte not in (0x08, 0x09):
            return False
        file_offset = value & self.GBA_PTR_MASK
        return 0 <= file_offset < self.size

    def read_bytes(self, offset: int, length: int) -> bytes:
        if offset < 0 or offset + length > self.size:
            end = min(offset + length, self.size)
            if offset < 0:
                return b""
            return bytes(self.data[offset:end])
        return bytes(self.data[offset:offset + length])

    def ptr_to_offset(self, ptr: int) -> int:
        """Convert a raw GBA pointer value to a ROM file offset."""
        return ptr & self.GBA_PTR_MASK
