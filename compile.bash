#!/bin/bash

riscv64-elf-gcc \
    -O3 \
    -march=rv32i \
    -mabi=ilp32 \
    -ffreestanding \
    -nostdlib \
    -T link.ld \
    tests/test.c \
    -lgcc \
    -o test.elf


# Adding this may fix some bugs:
#    -fno-jump-tables \
#    -fno-tree-switch-conversion \