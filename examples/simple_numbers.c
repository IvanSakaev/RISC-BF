#define NUM_COUNT 200

static long sys_write(const char *buf, long len) {
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

static long sys_read(const char *buf, long len) {
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

static void write_num(long num) {
    char buf[10];
    int i = 0;

    if (num < 0) {
        sys_write("-", 1);
        num = -num;
    }
    if (num == 0) {
        sys_write("0", 1);
        sys_write("\n", 1);
        return;
    }
    while (num > 0) {
        buf[i++] = '0' + (num % 10);
        num /= 10;
    }
    while (i > 0) {
        i--;
        sys_write(&buf[i], 1);
    }
    sys_write("\n", 1);
}

long simple[NUM_COUNT];

void _start() {
    long i = 0;
    for (long curr_num = 2; i < NUM_COUNT; curr_num++) {
        int is_simple = 1;
        for (long j = 0; j < i; j++) {
            if (curr_num % simple[j] == 0) {
                is_simple = 0;
                break;
            }
        }
        if (is_simple) {
            write_num(curr_num);
            simple[i] = curr_num;
            i++;
        }
    }
}
