#! /bin/python
from config import PROGRAM_START_ADDRESS, MEMORY_ADDRESS_HALFBYTES

imem_start = PROGRAM_START_ADDRESS * 0x01000000
imem_length = 0xffffffff - imem_start

dmem_length = min(16 ** MEMORY_ADDRESS_HALFBYTES, imem_start)

output = "ENTRY(_start)"

output += f"""

MEMORY
{{
    IMEM (rx)  : ORIGIN = 0x{imem_start:x}, LENGTH = 0x{imem_length:x}
    DMEM (rw)  : ORIGIN = 0x00000000, LENGTH = 0x{dmem_length:x}
}}
"""

output += """
SECTIONS
{
    .text :
    {
        *(.text.init)
        *(.text*)
    } > IMEM

    .rodata :
    {
        *(.rodata*)
    } > DMEM

    .data :
    {
        *(.data*)
    } > DMEM

    .bss (NOLOAD) :
    {
        *(.bss*)
        *(COMMON)
    } > DMEM
}
"""

with open("dst/link.ld", "w") as f:
    f.write(output)
