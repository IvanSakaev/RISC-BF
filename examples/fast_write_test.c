long fast_write(const char *buf) {
    register const char *a1 asm("a1") = buf;
    register long a7 asm("a7") = 86; // fast_write
    asm volatile ("ecall"
        :
        : "r"(a1), "r"(a7)
        : "memory");
}

void _start() {
    char* str = "\0hello world\n";
    fast_write(str);
}
