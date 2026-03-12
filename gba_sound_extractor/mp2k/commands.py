"""MP2K (MusicPlayer2000/Sappy) sound engine opcode definitions."""

# Wait/delta-time commands: 0x80 through 0xB0
# Each maps to a tick duration via WAIT_TABLE
WAIT_BASE = 0x80
WAIT_MAX = 0xB0

WAIT_TABLE = [
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
    16, 17, 18, 19, 20, 21, 22, 23, 24, 28, 30, 32, 36, 40,
    42, 44, 48, 52, 54, 56, 60, 64, 66, 68, 72, 76, 78, 80,
    84, 88, 90, 92, 96,
]

# Control commands
FINE = 0xB1      # End of track
GOTO = 0xB2      # Jump to address (4-byte pointer arg)
PATT = 0xB3      # Call subroutine (4-byte pointer arg)
PEND = 0xB4      # Return from subroutine
REPT = 0xB5      # Repeat count (1-byte arg)
MEMACC = 0xB9    # Memory access / conditional (variable args)
PRIO = 0xBA      # Priority (1-byte arg)
TEMPO = 0xBB     # Tempo in half-BPM (1-byte arg); actual BPM = value * 2
KEYSH = 0xBC     # Key shift / transpose (1 signed byte)
VOICE = 0xBD     # Set instrument/program (1-byte arg)
VOL = 0xBE       # Volume (1-byte arg, 0-127)
PAN = 0xBF       # Pan (1-byte: 0=left, 64=center, 127=right)
BEND = 0xC0      # Pitch bend (1-byte, 64=center)
BENDR = 0xC1     # Pitch bend range in semitones (1-byte arg)
LFOS = 0xC2      # LFO speed (1-byte arg)
LFODL = 0xC3     # LFO delay (1-byte arg)
MOD = 0xC4       # LFO depth / modulation (1-byte arg)
MODT = 0xC5      # LFO type (0=pitch, 1=vol, 2=pan)
TUNE = 0xC8      # Fine tuning (1-byte arg)
XCMD = 0xCD      # Extended command (next byte = sub-command)
EOT = 0xCE       # Note off / end of tie
TIE = 0xCF       # Note on with sustain (held until EOT)

# Note commands: 0xD0 through 0xFF
# Duration index = opcode - 0xD0, maps into WAIT_TABLE
NOTE_BASE = 0xD0
NOTE_MAX = 0xFF

# Commands that accept "running status" (repeatable with args < 0x80)
REPEATABLE_COMMANDS = {
    VOL, PAN, BEND, BENDR, LFOS, LFODL, MOD, MODT, TUNE,
    EOT, TIE,
}
# Note commands (0xD0-0xFF) are also repeatable

# Number of arguments for each control command (fixed-arg commands)
COMMAND_ARG_COUNTS = {
    FINE: 0,
    GOTO: 4,      # 4-byte pointer
    PATT: 4,      # 4-byte pointer
    PEND: 0,
    REPT: 1,
    PRIO: 1,
    TEMPO: 1,
    KEYSH: 1,
    VOICE: 1,
    VOL: 1,
    PAN: 1,
    BEND: 1,
    BENDR: 1,
    LFOS: 1,
    LFODL: 1,
    MOD: 1,
    MODT: 1,
    TUNE: 1,
    XCMD: 2,      # sub-command + arg
    EOT: 0,       # optional key arg
    TIE: 0,       # key + optional vel + optional gate
}

# Voice/instrument types
VOICE_DIRECT_SOUND = 0x00
VOICE_DIRECT_SOUND_ALT = 0x08
VOICE_SQUARE_1 = 0x01
VOICE_SQUARE_2 = 0x02
VOICE_WAVE = 0x03
VOICE_NOISE = 0x04
VOICE_KEYSPLIT = 0x40
VOICE_PERCUSSION = 0x80


def wait_duration(opcode):
    """Get tick duration for a wait command (0x80-0xB0)."""
    index = opcode - WAIT_BASE
    if 0 <= index < len(WAIT_TABLE):
        return WAIT_TABLE[index]
    return 0


def note_duration(opcode):
    """Get tick duration for a note command (0xD0-0xFF).

    Note commands use the same wait table, indexed by (opcode - 0xCF).
    Index 0 (opcode 0xD0) maps to WAIT_TABLE[1]=1,
    through index 47 (opcode 0xFF) maps to WAIT_TABLE[48]=96.
    """
    index = opcode - NOTE_BASE + 1
    if 1 <= index < len(WAIT_TABLE):
        return WAIT_TABLE[index]
    return 0
