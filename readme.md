# RISC-BF

**The RISC-V to brainfuck compiler**

It compiles RISCV32IM architecture to brainfuck esoteric language

## Usage

You can find example programs in `examples` folder.

1. Install python3.8+ and install dependencies
    ```bash
    pip install -r requirements.txt
    ```
2. Install `riscv64-elf-gcc` or `riscv64-unknown-elf-gcc`
3. Compile your C program to compressed brainfuck:
   ```bash
   ./compile -c examples/snake.c out.bpk
   ```
   If you don't use ibf or you want to get normal (not compressed) brainfuck,
   you should run this:
   ```bash
   ./compile examples/snake.c out.b
   ```
   Or if you have .elf riscv32 file, you can compile it with
   ```bash
   python asm.py [-c] file.elf out.bpk
   ```
4. Run brainfuck file. I recommend to use ibf interpretator,
   because it's fast and optimized for running this project.
   Also, some features (like breakpoints and asserts)
   won't work with other interpretators. If you don't use ibf,
   you should disable all debug and asserts options in config.py

   ```bash
   ./ibf -ac out.bpk
   ```
   
   or you can run not compressed brainfuck if you compiled without compression
   
   ```bash
   ./ibf -a out.b
   ```

   *-a option enables asserts*

   *-d option enables debug*

   *-c option enables compression* - you must enable it if you
   enabled compressing in this project on step 3

[ibf repository](https://github.com/sit-itmo/DoomBF/tree/master/bf/industrial-bf)

## Configuration

Configuration is done by modifying config.py file.

It's recommended to disable all assert and debug options if you don't
use ibf interpretator

### Options

-c Enables compressed brainfuck output. You can run it with ibf.
Compiling a program with MEMORY_ADDRESS_HALFBYTES > 5 (in config.py) will take up
a very large amount of your disk and RAM without compression (>20GB).
Otherwise, it will only take up a few megabytes.

## Project status

### What's ready now

- Script for compiling C to .elf file (using gcc)
- Reading RISC-V .elf file
- Preloading global variables (.data section) to brainfuck memory
- RISC-V instructions, mentioned at the bottom of instructions/mnemonics file
- Ecall
   - Read ecall (63)
   - Write ecall (64)

### Future plans

- Add new risc-v instructions (I think, all remaining):
   - AUIPC
- Add M (multiplication) risc-v extension
   - MULH, MULHSU
   - DIV, REM (signed)
- Fix TODOs and NotImplementedErrors
- Add more ECALLs
- Add more asserts to python and brainfuck
- [Compile and run Doom](https://github.com/sit-itmo/DoomBF)

## Contribution

Make pull requests or create issues here or [contact me via telegram](https://t.me/sakaevx).
