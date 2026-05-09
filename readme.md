# RISC-BF

**The RISC-V to brainfuck compiler**

It compiles RISCV32IM architecture to brainfuck esoteric language

## Usage

1. Compile your C program to risc-v .elf file
    ```bash
    clang -O0 --target=riscv32-unknown-elf -march=rv32im -mabi=ilp32 -c test.c -o test.o
    riscv32-elf-ld test.o -o test.elf
    ```
2. Compile .elf file to brainfuck
   ```bash
   python asm.py test.elf out.b
   ```
3. Run brainfuck file. I recommend to use ibf interpretator,
   because it's fast and optimized for running this project.
   Also, some functions (like breakpoints and asserts)
   won't work with other interpretators. If you don't use ibf,
   you should disable all debug and asserts options in config.py

   ```bash
   ./ibf -a -d out.b
   ```
   *-a option enables asserts*

   *-d option enables debug*

   [ibf repository](https://github.com/sit-itmo/DoomBF/tree/master/bf/industrial-bf)

## Configuration

Configuration is done by modifying config.py file.

It's recommended to disable all assert and debug options if you don't
use ibf interpretator

## Project status

### What's ready now

- Reading RISC-V .elf file
- Preloading global variables (.data section) to brainfuck memory
- RISC-V instructions, mentioned at the bottom of instructions/mnemonics file
- Ecall
    - Read ecall (63)
    - Write ecall (64)

### Future plans

- Add new risc-v instructions (I think, all remaining):
    - SRL, SRLI
    - SRA, SRAI
    - MULH, MULHSU
    - DIV, DIVU, REM, REMU
    - AUIPC
- Add more ECALLs
- Add more asserts to python and brainfuck
- Fix left shift by 32 (should return zero)
- [Compile and run Doom](https://github.com/sit-itmo/DoomBF)

## Contribution

The project is in an active stage of development, and
contributions to the repository will be reviewed.
