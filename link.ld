ENTRY(_start)

MEMORY
{
    IMEM (rx)  : ORIGIN = 0x01000000, LENGTH = 0xFEFFFFFF
    DMEM (rw)  : ORIGIN = 0x00000000, LENGTH = 1M
}

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