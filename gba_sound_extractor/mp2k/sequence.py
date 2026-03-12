"""MP2K sequence decoder — converts raw track bytes to Command lists."""

import logging
from typing import List

from ..rom.reader import ROMReader
from . import commands as cmd
from .structures import Command, Track

logger = logging.getLogger(__name__)

MAX_COMMANDS = 50000  # Safety limit per track
MAX_LOOP_UNROLLS = 2


def decode_track(rom: ROMReader, offset: int, track_index: int,
                 loop_unrolls: int = MAX_LOOP_UNROLLS) -> Track:
    """Decode a single track's sequence data into a list of Commands.

    Args:
        rom: The loaded ROM.
        offset: File offset of the track's sequence data.
        track_index: Index of this track within the song.
        loop_unrolls: How many times to unroll GOTO loops.

    Returns:
        A Track with decoded commands and total tick count.
    """
    decoder = _SequenceDecoder(rom, offset, track_index, loop_unrolls)
    decoder.decode()
    return Track(
        index=track_index,
        commands=decoder.commands,
        total_ticks=decoder.current_tick,
    )


class _SequenceDecoder:
    """Internal state machine for sequence decoding."""

    def __init__(self, rom: ROMReader, start_offset: int,
                 track_index: int, loop_unrolls: int):
        self.rom = rom
        self.start_offset = start_offset
        self.track_index = track_index
        self.loop_unrolls = loop_unrolls

        self.commands: List[Command] = []
        self.current_tick = 0
        self.pos = start_offset

        # Running status
        self.last_cmd = 0
        self.last_key = 60
        self.last_vel = 127
        self.last_gate = 0

        # Subroutine call stack (PATT/PEND)
        self.call_stack: List[int] = []

        # Loop detection: maps GOTO target -> times visited
        self.goto_visits: dict = {}

        self.finished = False

    def decode(self):
        while not self.finished and len(self.commands) < MAX_COMMANDS:
            if self.pos < 0 or self.pos >= self.rom.size:
                logger.warning("Track %d: position 0x%06X out of bounds",
                               self.track_index, self.pos)
                break
            self._decode_byte()

    def _read_u8(self) -> int:
        val = self.rom.read_u8(self.pos)
        self.pos += 1
        return val

    def _read_u32(self) -> int:
        val = self.rom.read_u32(self.pos)
        self.pos += 4
        return val

    def _read_ptr(self) -> int:
        val = self.rom.read_ptr(self.pos)
        self.pos += 4
        return val

    def _emit(self, cmd_type: int, *args):
        self.commands.append(Command(
            cmd_type=cmd_type,
            tick=self.current_tick,
            args=args,
        ))

    def _decode_byte(self):
        byte = self._read_u8()

        # --- Delta-time / wait commands (0x80 - 0xB0) ---
        if cmd.WAIT_BASE <= byte <= cmd.WAIT_MAX:
            wait_ticks = cmd.wait_duration(byte)
            self.current_tick += wait_ticks
            return

        # --- Running status: arg byte < 0x80 repeats last command ---
        if byte < 0x80:
            self.pos -= 1  # Put byte back, _handle_repeat will re-read
            self._handle_repeat()
            return

        # --- Control commands (0xB1 - 0xCE) ---
        if byte == cmd.FINE:
            self._emit(cmd.FINE)
            self.finished = True
            return

        if byte == cmd.GOTO:
            target = self._read_ptr()
            if target < 0:
                self.finished = True
                return
            visit_count = self.goto_visits.get(target, 0)
            if visit_count >= self.loop_unrolls:
                self._emit(cmd.FINE)
                self.finished = True
                return
            self.goto_visits[target] = visit_count + 1
            self.pos = target
            return

        if byte == cmd.PATT:
            target = self._read_ptr()
            if target < 0:
                return
            self.call_stack.append(self.pos)
            self.pos = target
            return

        if byte == cmd.PEND:
            if self.call_stack:
                self.pos = self.call_stack.pop()
            return

        if byte == cmd.REPT:
            # Repeat count — not directly usable in MIDI export,
            # but we consume the argument
            self._read_u8()
            return

        if byte == cmd.MEMACC:
            # Memory access: 3 argument bytes + 4-byte pointer
            self._read_u8()  # mem_set/add/sub/etc
            self._read_u8()  # address
            self._read_u8()  # data
            self._read_ptr()  # conditional jump target
            return

        if byte == cmd.PRIO:
            val = self._read_u8()
            self._emit(cmd.PRIO, val)
            return

        if byte == cmd.TEMPO:
            val = self._read_u8()
            self._emit(cmd.TEMPO, val)
            return

        if byte == cmd.KEYSH:
            val = self.rom.read_s8(self.pos)
            self.pos += 1
            self._emit(cmd.KEYSH, val)
            return

        if byte == cmd.VOICE:
            val = self._read_u8()
            self.last_cmd = cmd.VOICE
            self._emit(cmd.VOICE, val)
            return

        if byte == cmd.VOL:
            val = self._read_u8()
            self.last_cmd = cmd.VOL
            self._emit(cmd.VOL, val)
            return

        if byte == cmd.PAN:
            val = self._read_u8()
            self.last_cmd = cmd.PAN
            self._emit(cmd.PAN, val)
            return

        if byte == cmd.BEND:
            val = self._read_u8()
            self.last_cmd = cmd.BEND
            self._emit(cmd.BEND, val)
            return

        if byte == cmd.BENDR:
            val = self._read_u8()
            self.last_cmd = cmd.BENDR
            self._emit(cmd.BENDR, val)
            return

        if byte == cmd.LFOS:
            val = self._read_u8()
            self.last_cmd = cmd.LFOS
            self._emit(cmd.LFOS, val)
            return

        if byte == cmd.LFODL:
            val = self._read_u8()
            self.last_cmd = cmd.LFODL
            self._emit(cmd.LFODL, val)
            return

        if byte == cmd.MOD:
            val = self._read_u8()
            self.last_cmd = cmd.MOD
            self._emit(cmd.MOD, val)
            return

        if byte == cmd.MODT:
            val = self._read_u8()
            self.last_cmd = cmd.MODT
            self._emit(cmd.MODT, val)
            return

        if byte == cmd.TUNE:
            val = self._read_u8()
            self.last_cmd = cmd.TUNE
            self._emit(cmd.TUNE, val)
            return

        if byte == cmd.XCMD:
            sub = self._read_u8()
            arg = self._read_u8()
            self._emit(cmd.XCMD, sub, arg)
            return

        if byte == cmd.EOT:
            # Optional key argument
            key = self._peek_and_consume_arg()
            if key is not None:
                self.last_key = key
            self.last_cmd = cmd.EOT
            self._emit(cmd.EOT, self.last_key)
            return

        if byte == cmd.TIE:
            self._parse_note_args()
            self.last_cmd = cmd.TIE
            self._emit(cmd.TIE, self.last_key, self.last_vel)
            return

        # --- Note commands with duration (0xD0 - 0xFF) ---
        if cmd.NOTE_BASE <= byte <= cmd.NOTE_MAX:
            duration = cmd.note_duration(byte)
            self._parse_note_args()
            self.last_cmd = byte
            self._emit(byte, self.last_key, self.last_vel,
                       duration, self.last_gate)
            return

        # Unknown command — skip
        logger.debug("Track %d: unknown opcode 0x%02X at 0x%06X",
                     self.track_index, byte, self.pos - 1)

    def _peek_and_consume_arg(self):
        """If the next byte is < 0x80, consume and return it."""
        if self.pos < self.rom.size:
            nxt = self.rom.read_u8(self.pos)
            if nxt < 0x80:
                self.pos += 1
                return nxt
        return None

    def _parse_note_args(self):
        """Parse sticky note arguments: key, [velocity], [gate_time]."""
        key = self._peek_and_consume_arg()
        if key is not None:
            self.last_key = key
            vel = self._peek_and_consume_arg()
            if vel is not None:
                self.last_vel = vel
                gate = self._peek_and_consume_arg()
                if gate is not None:
                    self.last_gate = gate

    def _handle_repeat(self):
        """Handle running status — repeat last repeatable command."""
        if self.last_cmd == 0:
            # No previous command to repeat, skip byte
            self._read_u8()
            return

        if self.last_cmd == cmd.EOT:
            key = self._peek_and_consume_arg()
            if key is not None:
                self.last_key = key
            self._emit(cmd.EOT, self.last_key)
            return

        if self.last_cmd == cmd.TIE:
            self._parse_note_args()
            self._emit(cmd.TIE, self.last_key, self.last_vel)
            return

        if cmd.NOTE_BASE <= self.last_cmd <= cmd.NOTE_MAX:
            duration = cmd.note_duration(self.last_cmd)
            self._parse_note_args()
            self._emit(self.last_cmd, self.last_key, self.last_vel,
                       duration, self.last_gate)
            return

        # Single-arg repeatable commands (VOL, PAN, BEND, etc.)
        if self.last_cmd in cmd.REPEATABLE_COMMANDS:
            val = self._read_u8()
            self._emit(self.last_cmd, val)
            return

        # Fallback: consume and discard
        self._read_u8()
