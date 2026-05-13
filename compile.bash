#!/bin/bash

riscv64-elf-gcc \
    -O0 \
    -march=rv32i \
    -mabi=ilp32 \
    -ffreestanding \
    -nostdlib \
    -nostartfiles \
    tests/test.c \
    -lgcc \
    -o test.elf
