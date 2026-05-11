#!/bin/bash

#clang -O0 --target=riscv32-unknown-elf -march=rv32im -mabi=ilp32 -c tests/test.c -o test.o
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

#Декомпиляция
#llvm-strip --strip-all test.o
#llvm-objdump -d test.o --no-addresses --no-show-raw-insn > test.s


#clang -target riscv32 -march=rv32im -S factorial.c
#
#clang \
#  --target=riscv32-unknown-elf \
#  -march=rv32im \
#  -mabi=ilp32 \
#  -nostdlib \
#  -S factorial.c
