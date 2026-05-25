BLOCK_SIZE = 256  # 256 for production

REGISTER_COUNT = 32
SCRAP_COUNT = 32  # TODO: reduce scrap count

PROGRAM_START_ADDRESS = 1  # program (not data) addresses start from PROGRAM_START_ADDRESS * 0x01000000

# TODO: Make 3-bytes addressing, not 2.5-bytes
# Big values (> 3) may not work properly with most interpretators
# You should change DMEM size in link.ld script if you change this value
MEMORY_ADDRESS_HALFBYTES = 6  # Memory cell count will be 16^MEMORY_ADDRESS_HALFBYTES

# Input/output ecall max length value
MAX_OUTPUT_LENGTH_HALFBYTES = 4  # Max output length will be 16^MAX_OUTPUT_LENGTH_HALFBYTES

# Preload .data section
PRELOAD_MEMORY = True

# Next constants are useful only for ibf brainfuck interpretator.
# For other interpretators it's recommended to disable them.
# ibf interpretator: https://github.com/sit-itmo/DoomBF/tree/master/bf/industrial-bf

# Using # symbol for breakpoints.
ALLOW_DEBUG = True  # Allow breakpoints in concater.debug()
BREAKPOINT_EVERY_CYCLE = False
BREAKPOINT_EVERY_INSTRUCTION = False
BREAKPOINT_AFTER_EVERY_INSTRUCTION = False

# Generate .b.addr file with cells in "watch".
GENERATE_ADDRMAP = True
WATCH_REGISTERS = ["x1", "x2", "a0"]

# Allow asserts in brainfuck by using @hex and !hex for location and value assert.
ALLOW_ASSERTS = True

# Save program in compressed format (for ibf with -c option)
COMPRESSED = True


# Don't change!
MEMORY_SCRAPS_COUNT = 2 + MEMORY_ADDRESS_HALFBYTES + max(4, MAX_OUTPUT_LENGTH_HALFBYTES * 2)
assert PROGRAM_START_ADDRESS >= 1
assert PROGRAM_START_ADDRESS <= 0xff
assert BLOCK_SIZE <= 256
assert BLOCK_SIZE % 4 == 0
