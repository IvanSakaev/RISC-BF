import random
import subprocess

for i in range(100):
    num1 = random.randrange(2**32)
    num2 = random.randrange(2**32)

    with open("examples/test.s", "w") as file:
        file.write(
            f"""
li x1, 0x{num1:x}
li x2, 0x{num2:x}
mulhu x3, x1, x2
out x3
""".lstrip()
        )

    subprocess.run(
        [
            "python",
            "asm.py",
            "examples/test.s",
            "out.b",
        ]
    )
    predict = subprocess.run(
        [
            "./tmp/ibf",
            "-a",
            "out.b",
        ],
        stdout=subprocess.PIPE,
    ).stdout.decode().rstrip("\n")

    num3 = num1 * num2
    num3 //= 2**32
    num3 %= 2**32
    num3_str = f"{num3:08X}"

    if predict != num3_str:
        print(f"num1: {num1}\nnum2: {num2}\ncorrect: {num3_str}\npredicted: {predict}")
    if i % 10 == 0:
        print(f"tested {i} times")
