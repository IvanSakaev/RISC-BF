static inline long sys_write(const char *buf, long len) {
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
}

static inline long sys_read(const char *buf, long len) {
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
    return ret;
}

void _start() {
    sys_write("Write your name: ", 17);
    char input[50] = "";
    long read_count = sys_read(input, 50);
    sys_write("\n", 1);
    sys_write("Hello, ", 7);
    sys_write(input, read_count);
    sys_write("\n", 1);
}
