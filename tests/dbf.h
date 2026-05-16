#pragma once

// #define X86

#ifdef X86
#include <stdio.h>
#endif


unsigned long dbf_seed = 1;

void dbf_srand(const unsigned long seed) {
    dbf_seed = seed ? seed : 1;
}

unsigned long dbf_rand(void) {
    unsigned long x = dbf_seed;

    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;

    dbf_seed = x;

    return x;
}

unsigned long dbf_strlen(const char *str) {
    unsigned long len = 0;
    while (str[len] != '\0') len++;
    return len;
}

long dbf_write_ecall(const char *buf, const int len) {
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

void dbf_read_ecall(char *buf, const int len) {
#ifdef X86
    fgets(buf, len, stdin);
#else
    long ret;

    register long a0 asm("a0") = 0; // stdin
    register const char *a1 asm("a1") = buf;
    register long a2 asm("a2") = len;
    register long a7 asm("a7") = 63; // read

    asm volatile("ecall"
        : "+r"(a0)
        : "r"(a1), "r"(a2), "r"(a7)
        : "memory");

    ret = a0;
    buf[ret] = '\0';
#endif
}

unsigned long dbf_print(const char *str) {
    return dbf_write_ecall(str, dbf_strlen(str));
}

unsigned long dbf_println(char *str) {
    const unsigned long ret = dbf_write_ecall(str, dbf_strlen(str)) + 1;
    dbf_write_ecall("\n", 1);
    return ret;
}

static void dbf_print_num(long num) {
    char buf[10];
    int i = 0;

    if (num < 0) {
        dbf_write_ecall("-", 1);
        num = -num;
    }
    if (num == 0) {
        dbf_write_ecall("0", 1);
        dbf_write_ecall("\n", 1);
        return;
    }
    while (num > 0) {
        buf[i++] = '0' + (char) (num % 10);
        num /= 10;
    }
    while (i > 0) {
        i--;
        dbf_write_ecall(&buf[i], 1);
    }
}
