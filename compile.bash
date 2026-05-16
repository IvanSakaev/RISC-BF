#!/bin/bash

riscv64-elf-gcc \
    -O3 \
    -march=rv32i \
    -mabi=ilp32 \
    -ffreestanding \
    -nostdlib \
    tests/test.c \
    -lgcc \
    -o test.elf
