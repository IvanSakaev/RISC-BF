#!/bin/bash

# TODO: add linker script

# Compiling .s file to .elf file
riscv32-elf-as tests/t.s -o test.o
riscv32-elf-ld test.o -o test.elf
