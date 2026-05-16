# RISC-BF

**The RISC-V to brainfuck compiler**

It compiles RISCV32IM architecture to brainfuck esoteric language

## Usage

You can find example programs in `examples` folder.

1. Compile your C program to risc-v .elf file:
   Move your program to `tests/test.c` and run `compile.bash`
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

- Test instructions:
    - JALR
    - AUIPC
- Add new risc-v instructions (I think, all remaining):
    - SRA, SRAI
    - MULH, MULHSU
    - DIV, REM (signed)
- Fix linker script (now JR and JALR may jump to 0x10000)
- Fix TODOs and NotImplementedErrors
- Add more ECALLs
- Add more asserts to python and brainfuck
- [Compile and run Doom](https://github.com/sit-itmo/DoomBF)

## Contribution

The project is in an active stage of development, and
contributions to the repository will be reviewed.

If you find a bug, please create an issue or [contact me via telegram](https://t.me/sakaevx).
