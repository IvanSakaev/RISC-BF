import random
import subprocess

for i in range(1, 101):
    # num1 = 0
    # num2 = 0
    # num1 = random.randrange(-127, 128)
    # num2 = random.randrange(-127, 128)
    # num1 = random.randrange(256)
    # num2 = random.randrange(256)
    # num1 = random.randint(-2**31, 2**31)
    # num2 = random.randint(-2**31, 2**31)
    num1 = random.randrange(2 ** 32)
    num2 = random.randrange(2 ** 32)

    # if random.randint(0, 1) == 0:
    #     num1 = num2
    if random.randint(0, 10) == 0:
        num2 = num1

    num1text = num1 & 0xFFFFFFFF
    num2text = num2 & 0xFFFFFFFF

    with open("tests/t.s", "w") as file:
        file.write(
            f"""
li x1, 0x{num1text:x}
li x2, 0x{num2text:x}
li x3, 0
bleu x1, x2, less
j final
less:
li x3, 1
final:
out x3
""".lstrip()
        )

    subprocess.run(
        [
            "python",
            "asm.py",
            "tests/t.s",
            "out.b",
        ]
    )
    predict_byte = subprocess.run(
        [
            "./tmp/ibf",
            "-a",
            "out.b",
        ],
        stdout=subprocess.PIPE,
        timeout=1,
    ).stdout

    try:
        predict = predict_byte.decode().rstrip("\n")
    except UnicodeDecodeError:
        predict = predict_byte

    num3 = 1 if num1 <= num2 else 0

    num3 &= 0xFFFFFFFF
    num3_str = f"{num3:08X}"

    if predict != num3_str:
        print(f"passed test count: {i - 1}")
        print()
        print(f"num1:\t\t{num1text:08X} ({num1:08X})")
        print(f"num2:\t\t{num2text:08X} ({num2:08X})")
        print(f"correct:\t{num3_str}")
        print(f"predicted:\t{predict}")
        exit()
    if i % 10 == 0:
        print(f"tested {i} times")
