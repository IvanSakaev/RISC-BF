#!/usr/bin/env python3
"""Сборка chess → bpk и пошаговый ibf -d до assert / паники / лимита шагов."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from queue import Empty, Queue
from threading import Thread

ANSI = re.compile(r"\x1b\[[0-9;]*m")
PROMPT = re.compile(r"\x1b\[32m\$ \x1b\[0m")
ROOT = Path(__file__).resolve().parent

REGS_NAMES = {
    **{f"x{i}": f"x{i}" for i in range(32)},
    "zero": "x0",
    "ra": "x1",
    "sp": "x2",
    "gp": "x3",
    "tp": "x4",
    "t0": "x5",
    "t1": "x6",
    "t2": "x7",
    "s0": "x8",
    "fp": "x8",
    "s1": "x9",
    "a0": "x10",
    "a1": "x11",
    "a2": "x12",
    "a3": "x13",
    "a4": "x14",
    "a5": "x15",
    "a6": "x16",
    "a7": "x17",
    "s2": "x18",
    "s3": "x19",
    "s4": "x20",
    "s5": "x21",
    "s6": "x22",
    "s7": "x23",
    "s8": "x24",
    "s9": "x25",
    "s10": "x26",
    "s11": "x27",
    "t3": "x28",
    "t4": "x29",
    "t5": "x30",
    "t6": "x31",
}

q_to_run = Queue(maxsize=10000)


def clean(s: str) -> str:
    return ANSI.sub("", s)


BLOCK_SIZE = 256


def pack_next_bytes(components: list[int]) -> int:
    return sum((v & 0xFF) << (8 * i) for i, v in enumerate(components))


def parse_stop(chunk: str):
    plain = clean(chunk)
    mnemonic = ""
    next_addr = None
    next_components = None
    regs = {}
    nxt = re.search(r"next: (0x[0-9a-f]+(?:, 0x[0-9a-f]+){3})", plain)
    if nxt:
        next_components = [
            int(x, 16) for x in re.findall(r"0x([0-9a-f]+)", nxt.group(1))
        ]
        next_addr = sum((v & 0xFF) << (8 * i) for i, v in enumerate(next_components))

    for m in re.finditer(r"^>?\s*(x\d+):\s*(.+)$", plain, re.M):
        cells = [int(x, 16) for x in re.findall(r"0x([0-9a-f]+)", m.group(2))]
        regs[m.group(1)] = sum((v & 0xF) << (4 * i) for i, v in enumerate(cells))

    mnemonic = re.findall(r">.*\n", plain)[-1]
    mnemonic = mnemonic.strip().lstrip(">").strip()
    return mnemonic, next_addr, regs


class IbfSession:
    """subprocess-сессия ibf: stdout читается в фоне, stdin пишется без ожидания prompt."""

    PIPELINE_DEPTH = 8

    def __init__(self, cmd: list[str], cwd: Path) -> None:
        self.proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )
        self._buf = ""
        self._buf_lock = threading.Lock()
        self._stop_queue: Queue[str] = Queue()
        self._eof = False
        self._failed = False
        self._reader = Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def _read_loop(self) -> None:
        try:
            assert self.proc.stdout is not None
            while True:
                chunk = self.proc.stdout.read(65536)
                if not chunk:
                    break
                text = chunk.decode("utf-8", errors="replace")
                with self._buf_lock:
                    self._buf += text
                    if "assertion failed" in self._buf:
                        self._failed = True
                        print(clean(self._buf))
                        sys.exit(1)
                    self._drain_stops()
        finally:
            self._eof = True

    def _drain_stops(self) -> None:
        while True:
            match = PROMPT.search(self._buf)
            if not match:
                return
            self._stop_queue.put(self._buf[: match.start()])
            self._buf = self._buf[match.end() :]

    def write(self, data: str) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write(data.encode("utf-8"))
        self.proc.stdin.flush()

    def wait_for(self, needle: str, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._buf_lock:
                if needle in self._buf:
                    return
            if self._eof or self._failed:
                print("ibf завершился")
                sys.exit(1)
            time.sleep(0.01)
        raise TimeoutError(f"timeout waiting for {needle!r}")

    def wait_prompt(self, timeout: float | None = None) -> None:
        try:
            if timeout is None:
                self._stop_queue.get()
                return
            self._stop_queue.get(timeout=timeout)
        except Empty:
            raise TimeoutError("timeout waiting for prompt") from None

    def wait_stop(
        self,
        command: str = "w",
        i: int = 0,
        prnt: bool = False,
    ):
        while True:
            try:
                chunk = self._stop_queue.get(timeout=0.05)
                break
            except Empty:
                if self._eof:
                    print("ibf завершился")
                    sys.exit(1)
        if prnt:
            print(f"{command} #{i:08d}")
        mnemonic, next_addr, regs = parse_stop(chunk)
        if prnt:
            print(
                f"  next=0x{next_addr or 0:04x}\n"
                f"  mnemonic={mnemonic}\n"
                f"  ra_after=0x{regs.get(REGS_NAMES['ra'], 0):08x}"
            )
        instr, args = parse_mnemonic(mnemonic)
        return instr, args, next_addr, regs

    def close(self) -> None:
        if self.proc.stdin is not None:
            try:
                self.proc.stdin.close()
            except OSError:
                pass
        self.proc.wait(timeout=5)


def parse_imm(token: str) -> int:
    sign = 1
    if token.startswith("_"):
        sign = -1
        token = token[1:]
    if token.startswith("0x"):
        val = int(token[2:], 16)
    else:
        val = int(token)
    return val * sign


def parse_mnemonic(plain: str):
    l = plain.split()
    l = [a.strip().strip(",").lower() for a in l]
    instr = l[0]
    args = []
    for a in l[1:]:
        if a in REGS_NAMES:
            args.append(REGS_NAMES[a])
        elif "(" in a:
            a, b = a.split("(")
            assert b.endswith(")")
            b = b[:-1]
            args.append(parse_imm(a))
            args.append(REGS_NAMES[b])
        else:
            args.append(parse_imm(a))
    return instr, args


MASK32 = 0xFFFFFFFF
PROGRAM_START_ADDRESS = 16

JUMP_INSTRS = {
    "j",
    "jr",
    "jal",
    "jalr",
    "call",
    "ret",
    "beq",
    "beqz",
    "bne",
    "bnez",
    "blt",
    "bltu",
    "bge",
    "bgeu",
    "blez",
    "bgez",
    "bltz",
    "bgtz",
    "bgt",
    "ble",
    "bgtu",
    "bleu",
}

current_addr = 0
regs = {}
memory = [0] * (16**7)


def u32(v: int) -> int:
    return v & MASK32


def s32(v: int) -> int:
    v = u32(v)
    return v if v < 0x80000000 else v - 0x100000000


def shamt(v: int) -> int:
    return v & 0x1F


def imm12(v: int) -> int:
    v &= 0xFFF
    return v if v < 0x800 else v - 0x1000


def write_reg(rd: str, value: int) -> None:
    if rd != "x0":
        regs[rd] = u32(value)


def mem_write(addr: int, value: int, size: int) -> None:
    addr = u32(addr)
    value = u32(value)
    for i in range(size):
        memory[addr + i] = (value >> (8 * i)) & 0xFF


def mem_read(addr: int, size: int, signed: bool) -> int:
    addr = u32(addr)
    raw = 0
    for i in range(size):
        raw |= memory[addr + i] << (8 * i)
    if signed and raw >= (1 << (size * 8 - 1)):
        raw -= 1 << (size * 8)
    return u32(raw)


def branch_taken(instr: str, args: list) -> bool:
    if instr == "beq":
        return regs[args[0]] == regs[args[1]]
    if instr == "bne":
        return regs[args[0]] != regs[args[1]]
    if instr == "blt":
        return s32(regs[args[0]]) < s32(regs[args[1]])
    if instr == "bltu":
        return u32(regs[args[0]]) < u32(regs[args[1]])
    if instr == "bge":
        return s32(regs[args[0]]) >= s32(regs[args[1]])
    if instr == "bgeu":
        return u32(regs[args[0]]) >= u32(regs[args[1]])
    if instr == "beqz":
        return regs[args[0]] == 0
    if instr == "bnez":
        return regs[args[0]] != 0
    if instr == "blez":
        return s32(regs[args[0]]) <= 0
    if instr == "bgez":
        return s32(regs[args[0]]) >= 0
    if instr == "bltz":
        return s32(regs[args[0]]) < 0
    if instr == "bgtz":
        return s32(regs[args[0]]) > 0
    if instr == "bgt":
        return s32(regs[args[0]]) > s32(regs[args[1]])
    if instr == "ble":
        return s32(regs[args[0]]) <= s32(regs[args[1]])
    if instr == "bgtu":
        return u32(regs[args[0]]) > u32(regs[args[1]])
    if instr == "bleu":
        return u32(regs[args[0]]) <= u32(regs[args[1]])
    raise ValueError(instr)


curr_instr_num = 0


def run_command(instr, args, next_addr_predict, regs_predict):
    global current_addr, regs, curr_instr_num

    assert current_addr is not None
    assert regs != {}

    curr_instr_num += 1
    print(f"w #{curr_instr_num:08d}")
    print(
        f"  next=0x{next_addr_predict or 0:04x}\n"
        f"  mnemonic={instr} {args}\n"
        f"  ra=0x{regs.get(REGS_NAMES['ra'], 0):08x}"
    )

    predicted_next = None
    prev_regs = regs.copy()

    if instr == "add":
        write_reg(args[0], regs[args[1]] + regs[args[2]])
    elif instr == "addi":
        write_reg(args[0], regs[args[1]] + imm12(args[2]))
    elif instr == "sub":
        write_reg(args[0], regs[args[1]] - regs[args[2]])
    elif instr == "li":
        write_reg(args[0], args[1])
    elif instr == "lui":
        write_reg(args[0], args[1] << 12)
    elif instr == "mv":
        write_reg(args[0], regs[args[1]])
    elif instr == "neg":
        write_reg(args[0], -regs[args[1]])
    elif instr == "nop":
        pass
    elif instr == "unimp":
        pass
    elif instr == "ebreak":
        pass
    elif instr == "ecall":
        if regs[REGS_NAMES["a7"]] in [1, 86, 87]:
            pass
        elif regs[REGS_NAMES["a7"]] in [63, 64]:
            regs[REGS_NAMES["a0"]] = regs_predict[REGS_NAMES["a0"]]
        else:
            raise ValueError(f"unknown ecall number {regs[REGS_NAMES['a7']]}")

    elif instr == "sll":
        write_reg(args[0], u32(regs[args[1]] << shamt(regs[args[2]])))
    elif instr == "slli":
        write_reg(args[0], u32(regs[args[1]] << shamt(args[2])))
    elif instr == "srl":
        write_reg(args[0], u32(regs[args[1]] >> shamt(regs[args[2]])))
    elif instr == "srli":
        write_reg(args[0], u32(regs[args[1]] >> shamt(args[2])))
    elif instr == "sra":
        write_reg(args[0], u32(s32(regs[args[1]]) >> shamt(regs[args[2]])))
    elif instr == "srai":
        write_reg(args[0], u32(s32(regs[args[1]]) >> shamt(args[2])))

    elif instr == "or":
        write_reg(args[0], regs[args[1]] | regs[args[2]])
    elif instr == "and":
        write_reg(args[0], regs[args[1]] & regs[args[2]])
    elif instr == "xor":
        write_reg(args[0], regs[args[1]] ^ regs[args[2]])
    elif instr == "not":
        write_reg(args[0], ~regs[args[1]])
    elif instr == "ori":
        write_reg(args[0], regs[args[1]] | u32(imm12(args[2])))
    elif instr == "andi":
        write_reg(args[0], regs[args[1]] & u32(imm12(args[2])))
    elif instr == "xori":
        write_reg(args[0], regs[args[1]] ^ u32(imm12(args[2])))

    elif instr == "slt":
        write_reg(args[0], 1 if s32(regs[args[1]]) < s32(regs[args[2]]) else 0)
    elif instr == "slti":
        write_reg(args[0], 1 if s32(regs[args[1]]) < s32(imm12(args[2])) else 0)
    elif instr == "sltu":
        write_reg(args[0], 1 if u32(regs[args[1]]) < u32(regs[args[2]]) else 0)
    elif instr == "sltiu":
        write_reg(args[0], 1 if u32(regs[args[1]]) < u32(imm12(args[2])) else 0)
    elif instr == "seqz":
        write_reg(args[0], 1 if regs[args[1]] == 0 else 0)
    elif instr == "snez":
        write_reg(args[0], 1 if regs[args[1]] != 0 else 0)
    elif instr == "sltz":
        write_reg(args[0], 1 if s32(regs[args[1]]) < 0 else 0)
    elif instr == "sgtz":
        write_reg(args[0], 1 if s32(regs[args[1]]) > 0 else 0)

    elif instr == "sw":
        mem_write(regs[args[2]] + args[1], regs[args[0]], 4)
    elif instr == "sh":
        mem_write(regs[args[2]] + args[1], regs[args[0]], 2)
    elif instr == "sb":
        mem_write(regs[args[2]] + args[1], regs[args[0]], 1)
    elif instr == "lw":
        write_reg(args[0], mem_read(regs[args[2]] + args[1], 4, signed=True))
    elif instr == "lh":
        write_reg(args[0], mem_read(regs[args[2]] + args[1], 2, signed=True))
    elif instr == "lhu":
        write_reg(args[0], mem_read(regs[args[2]] + args[1], 2, signed=False))
    elif instr == "lb":
        write_reg(args[0], mem_read(regs[args[2]] + args[1], 1, signed=True))
    elif instr == "lbu":
        write_reg(args[0], mem_read(regs[args[2]] + args[1], 1, signed=False))

    elif instr == "auipc":
        write_reg(args[0], u32(current_addr + (args[1] << 12)))
    elif instr == "j":
        predicted_next = current_addr + args[0]
    elif instr == "jr":
        predicted_next = regs[args[0]]
    elif instr == "jal":
        write_reg(args[0], u32(current_addr + 4))
        predicted_next = current_addr + args[-1]
    elif instr == "jalr":
        base, offset = args[2], args[1]
        if base == "x0":
            predicted_next = PROGRAM_START_ADDRESS * (16**3) + offset
        else:
            predicted_next = regs[base] + offset
        write_reg(args[0], u32(current_addr + 4))
    elif instr == "call":
        write_reg("x1", u32(current_addr + 4))
        predicted_next = current_addr + args[-1]
    elif instr == "ret":
        predicted_next = regs["x1"]
    elif instr in JUMP_INSTRS:
        offset = args[-1]
        predicted_next = (
            (current_addr + offset) if branch_taken(instr, args) else (current_addr + 4)
        )

    else:
        raise NotImplementedError(instr)

    if predicted_next is None:
        predicted_next = current_addr + 4

    got = u32(next_addr_predict or 0)
    assert predicted_next == got, (
        f"expected next=0x{predicted_next:08x}, "
        f"got=0x{got:08x} (pc=0x{current_addr:08x})\n\n"
        f"prev_regs={prev_regs}\n\nregs={regs}\n\nregs_brainfuck={regs_predict}"
    )

    current_addr = next_addr_predict
    regs["x0"] = 0
    for i in range(1, 32):
        name = f"x{i}"
        regs[name] = u32(regs[name])
        assert regs[name] == regs_predict[name], (
            f"expected=0x{regs[name]:08x} got=0x{regs_predict[name]:08x} reg_name={name}\n\n"
            f"prev_regs={prev_regs}\n\nregs={regs}\n\nregs_brainfuck={regs_predict}"
        )


def dump_tape(ibf: IbfSession, tmp: Path) -> None:
    print("dumping tape...")
    subprocess.run(("rm", "-f", str(tmp / "tape.bin")), check=False)
    ibf.write("D\n")
    ibf.wait_prompt(timeout=30)
    with open(tmp / "tape.bin", "rb") as file:
        tape = file.read()
    for i, byte in enumerate(tape[0x124 : (0x124 + (16**7))]):
        memory[i] = byte
    print("done")


def runner() -> None:
    while True:
        instr, args, next_addr_predict, regs_predict = q_to_run.get()
        run_command(instr, args, next_addr_predict, regs_predict)


RUN_COUNT = 6


def main() -> int:
    global current_addr, regs

    ap = argparse.ArgumentParser(description="Отладка chess через ibf -d")
    ap.add_argument("--bpk", type=Path, default=Path("../doom.bpk"))
    ap.add_argument("--ibf", type=Path, default=Path("../ibf"))
    ap.add_argument("--tmp", type=Path, default=Path("./tmp"))
    cmd_args = ap.parse_args()

    cmd = [
        str(cmd_args.ibf.resolve()),
        "-acd",
        str(cmd_args.bpk.resolve()),
    ]
    ibf = IbfSession(cmd, cmd_args.tmp)
    try:
        # ibf.wait_for("loading addrmap", timeout=30)
        ibf.wait_prompt(timeout=30)

        if RUN_COUNT > 0:
            for i in range(RUN_COUNT):
                ibf.write("r\n")
                _, _, next_addr_predict, regs_predict = ibf.wait_stop("r", i, True)
                current_addr = next_addr_predict
                regs = {
                    **regs_predict,
                    "x0": 0,
                }
        else:
            ibf.write("w\n")
            _, _, next_addr_predict, regs_predict = ibf.wait_stop("w", -1, True)
            current_addr = next_addr_predict
            regs = {
                **regs_predict,
                "x0": 0,
            }

        dump_tape(ibf, cmd_args.tmp)
        Thread(target=runner).start()

        ibf.write("w\n" * IbfSession.PIPELINE_DEPTH)
        i = 0
        while True:
            instr, args, next_addr_predict, regs_predict = ibf.wait_stop("w", i, False)
            q_to_run.put((instr, args, next_addr_predict, regs_predict))
            ibf.write("w\n")
            i += 1
    finally:
        ibf.close()


if __name__ == "__main__":
    raise SystemExit(main())
