import random
import subprocess

for i in range(100):
    num1 = random.randrange(2**32)
    num2 = random.randrange(2**32)
    # num1 = random.randrange(32)
    # num2 = random.randrange(32)

    with open("tests/t.s", "w") as file:
        file.write(
            f"""
li x1, 0x{num1:x}
ori x3, x1, 0x{num2:x}
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
    predict = (
        subprocess.run(
            [
                "./tmp/ibf",
                "-a",
                "out.b",
            ],
            stdout=subprocess.PIPE,
            timeout=1,
        )
        .stdout.decode()
        .rstrip("\n")
    )

    num3 = num1 | num2
    num3_str = f"{num3:08X}"

    if predict != num3_str:
        print(
            f"num1: {num1:08X}\nnum2: {num2:08X}\ncorrect: {num3_str}\npredicted: {predict}"
        )
        exit()
    if i % 10 == 0:
        print(f"tested {i} times")
