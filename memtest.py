import random
import subprocess

OPS = [
    ("sw", "lw", 4, True),
    ("sb", "lb", 1, True),
    ("sb", "lbu", 1, False),
    ("sh", "lh", 2, True),
    ("sh", "lhu", 2, False),
]


def store(memory, addr, value, size):
    for k in range(size):
        memory[addr + k] = (value >> (8 * k)) & 0xFF


def load_expected(memory, addr, size, signed):
    raw = 0
    for k in range(size):
        raw |= memory.get(addr + k, 0) << (8 * k)
    if signed and raw >= (1 << (size * 8 - 1)):
        raw -= 1 << (size * 8)
    return raw & 0xFFFFFFFF


for i in range(100):
    store_op, load_op, size, signed = OPS[i % len(OPS)]
    max_addr = 0x10000000 - size

    out = """
.global _start
_start:
"""
    memory = {}
    addresses = []

    for j in range(10):
        addr = random.randrange(0, max_addr)
        value = random.randrange(0, 2 ** 32)
        addresses.append(addr)
        store(memory, addr, value, size)
        out += f"li x1, 0x{addr:x}\n"
        out += f"li x2, 0x{value:x}\n"
        out += f"{store_op} x2, 0(x1)\n"

    random.shuffle(addresses)

    for addr in addresses:
        read_addr = addr + random.randint(-4, 4)
        if read_addr < 0:
            read_addr = 0
        expected = load_expected(memory, read_addr, size, signed)
        out += f"li x1, 0x{read_addr:x}\n"
        out += f"li x2, 0x{expected:x}\n"
        out += "li x3, 0xdeaddead\n"
        out += f"{load_op} x3, 0(x1)\n"
        out += "bne x2, x3, wrong\n"

    out += """
li a7, 1
li a0, 1
ecall
j end
wrong:
li a7, 1
li a0, 0
ecall
j end
end:
"""

    with open("tests/t.s", "w") as file:
        file.write(out)

    subprocess.run([
        "./compile",
        "tests/t.s",
        "out.bpk",
        "-c",
    ])
    predict_byte = subprocess.run(
        [
            "./bin/ibf",
            "-ac",
            "out.bpk",
        ],
        stdout=subprocess.PIPE,
        timeout=1,
    ).stdout

    try:
        predict = predict_byte.decode().rstrip("\n")
    except UnicodeDecodeError:
        predict = predict_byte

    correct = "00000001"

    if predict != correct:
        print(f"failed at test {i} ({store_op}/{load_op})")
        print()
        print(f"correct:\t{correct}")
        print(f"predicted:\t{predict}")
        exit()
    if (i + 1) % 5 == 0:
        print(f"tested {i + 1} times")

print("all tests passed")
