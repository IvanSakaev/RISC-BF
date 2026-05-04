BLOCK_SIZE = 256  # 256 for production

BREAKPOINT_EVERY_CYCLE = False
BREAKPOINT_EVERY_INSTRUCTION = False
BREAKPOINT_AFTER_EVERY_INSTRUCTION = False

assert BLOCK_SIZE <= 256
assert BLOCK_SIZE % 4 == 0

REGISTER_COUNT = 32
SCRAP_COUNT = 32  # TODO: reduce scrap count

# TODO: Make 3-bytes addressing, not 2.5-bytes
# Big values may not work properly with most interpretators
MEMORY_ADDRESS_HALFBYTES = 5  # Memory cell count will be 16^MEMORY_ADDRESS_HALFBYTES

PRELOAD_MEMORY = True


MEMORY_SCRAPS_COUNT = 6 + MEMORY_ADDRESS_HALFBYTES  # Don't change!
