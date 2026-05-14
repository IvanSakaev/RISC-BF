#pragma once
#include <stdint.h>

#define X86

unsigned long dbf_seed = 1;

void dbf_srand(const uint32_t seed)
{
    dbf_seed = seed ? seed : 1;
}

unsigned long dbf_rand(void)
{
    unsigned long x = dbf_seed;

    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;

    dbf_seed = x;

    return x;
}

long dbf_write_ecall(char *buf, int len) {
#ifdef X86
    printf("%.*s", len, buf);
    return len;
#else
    long ret;

    register long a0 asm("a0") = 1; // stdout
    register const char *a1 asm("a1") = buf;
    register long a2 asm("a2") = len;
    register long a7 asm("a7") = 64; // write
    asm volatile ("ecall"
                 : "+r"(a0)
                 : "r"(a1), "r"(a2), "r"(a7)
                 : "memory");
    ret = a0;
    return ret;
#endif
}

unsigned long dbf_print(char *str) {
    return dbf_write_ecall(str, sizeof(str));
}

unsigned long dbf_println(char *str) {
    const unsigned long ret = dbf_write_ecall(str, sizeof(str)) + 1;
    dbf_write_ecall("\n", 1);
    return ret;
}
