#! /bin/python
from __future__ import annotations

import types
from typing import Union, get_args, get_origin, get_type_hints

import config
import instructions
from cell import concater
from instructions import (
    MNEMONICS,
    is_block_boundary,
)
from registers import SCRAP_COUNT, Immediate, Register, regs


def split_program_into_blocks(instrs):
    blocks = []
    cur_block = []
    block_name = None
    for i in instrs:
        if not isinstance(i, instructions.LabelDefine):
            cur_block.append(i)
        if is_block_boundary(i):
            if isinstance(i, instructions.LabelDefine):
                cur_block.append(instructions.JumpRelative(Immediate(1)))

            blocks.append(
                instructions.Block(
                    0, instructions.KiloBlock(0, []), block_name, cur_block
                )
            )
            cur_block = []
            if isinstance(i, instructions.LabelDefine):
                block_name = i.name
            else:
                block_name = None

    cur_block.append(instructions.JumpRelative(Immediate(1)))
    blocks.append(
        instructions.Block(0, instructions.KiloBlock(0, []), block_name, cur_block)
    )

    return blocks


def split_blocks_into_kiloblocks(blocks: list[instructions.Block]):
    kiloblocks = [instructions.KiloBlock(1, [])]
    i = 0
    for block in blocks:
        i += 1
        if i > config.BLOCKS_IN_KILOBLOCK:
            i = 1
            kiloblocks.append(instructions.KiloBlock(len(kiloblocks) + 1, []))
        block.myid = i
        block.kiloblock = kiloblocks[-1]
        kiloblocks[-1].blocks.append(block)
    return kiloblocks


class Program:
    def __init__(self, instrs):
        blocks = split_program_into_blocks(instrs)
        self.kiloblocks = split_blocks_into_kiloblocks(blocks)

    def find_block(self, name):
        if name == "exit":
            return 0, 0
        for kiloblock in self.kiloblocks:
            for block in kiloblock.blocks:
                if block.name == name:
                    i = kiloblock.myid
                    j = block.myid
                    return i, j
        raise ValueError(f"Block not found: {name}")

    def find_next_block(self, block: instructions.Block):
        i = block.kiloblock.myid
        j = block.myid
        j += 1
        if j > config.BLOCKS_IN_KILOBLOCK:
            j = 1
            i += 1
            assert i < config.MAX_KILOBLOCK_COUNT
        return i, j

    def program_prologue(self):
        return "+>+<[[>>+<<-]>[>>+<<-]>>"

    def program_epilogue(self):
        out = "\n-" + "]" * len(self.kiloblocks) + "<<<"
        if config.BREAKPOINT_EVERY_CYCLE:
            out += "#"
        out += "]"
        return out

    def kiloblock_prologue(self, kiloblock: instructions.KiloBlock):
        name = f"kiloblock_{kiloblock.myid}"
        name_line = f"{concater.sanitize(name)}:"
        return f"\n{name_line}\n->+<[>-]>[>]<[-<<[>+<-]>\n"

    def kiloblock_epilogue(self, kiloblock: instructions.KiloBlock):
        return "\nend_kiloblock -" + "]" * len(kiloblock.blocks) + " >]<["

    def block_prologue(self, block: instructions.Block):
        name = block.name
        if name is None:
            name = f"block_{block.myid}"
        name_line = f"{concater.sanitize(name)}:"

        return f"\n{name_line}\n->+<[>-]>[>]<[-"

    def block_epilogue(self):
        return "\n]<["

    def assemble_block(self, block: instructions.Block):
        concater.init_block()
        for inst in block.insts:
            inst.evaluate(self, block, True)
        return (
            self.block_prologue(block)
            + concater.get_block_code()
            + self.block_epilogue()
        )

    def assemble_kiloblock(self, kiloblock: instructions.KiloBlock):
        return (
            self.kiloblock_prologue(kiloblock)
            + "\n".join([self.assemble_block(block) for block in kiloblock.blocks])
            + self.kiloblock_epilogue(kiloblock)
        )

    def assemble(self):
        return (
            self.program_prologue()
            + "\n".join(
                [self.assemble_kiloblock(kiloblock) for kiloblock in self.kiloblocks]
            )
            + self.program_epilogue()
        )


def parse_arg(arg_s: str, expected_type: type, mnemonic: str):
    """Parse a single argument string to the expected type."""
    arg_s = arg_s.strip()

    if expected_type == Register:
        if arg_s in regs:
            return regs[arg_s]
        raise ValueError(f"Register {arg_s} is unavailable")

    elif expected_type == instructions.Label:
        return instructions.Label(arg_s[1:-1])

    elif expected_type == Immediate:
        sign = 1
        if arg_s.startswith("-"):
            sign = -1
            arg_s = arg_s[1:]
        arg_s_lower = arg_s.lower()
        if arg_s_lower.startswith("0x"):
            imm = int(arg_s_lower[2:], 16)
        elif arg_s_lower.startswith("0b"):
            imm = int(arg_s_lower[2:], 2)
        elif arg_s.startswith("0") and len(arg_s) > 1:
            imm = int(arg_s[1:], 8)
        else:
            imm = int(arg_s)
        return Immediate(sign * imm)

    else:
        raise ValueError(f"Unknown expected type: {expected_type}")


def parse(s: str):
    insts: list[instructions.Instruction | instructions.LabelDefine] = []
    for line in s.split("\n"):
        if "#" in line:
            line = line[: line.find("#")]
        if "." in line:
            line = line[: line.find(".")]
        if line.isspace() or not line:
            continue
        line = line.strip()
        if line.endswith(":"):
            insts.append(instructions.LabelDefine(line[:-1]))
            continue

        if " " not in line:
            mnemonic = line
            args_str = ""
        else:
            mnemonic = line[: line.find(" ")]
            args_str = line[line.find(" ") :].strip(" ")

        mnemonic = mnemonic.lower()
        op = MNEMONICS[mnemonic]
        op_args = list(get_type_hints(op).values())

        args: list = []
        if args_str:
            arg_strings = [a.strip() for a in args_str.split(",")]
        else:
            arg_strings = []

        if len(arg_strings) != len(op_args):
            raise ValueError(
                f"Wrong number of arguments for {mnemonic}, expected {len(op_args)} "
                f"arguments, got {len(arg_strings)}"
            )

        for arg_s, op_arg in zip(arg_strings, op_args):
            if get_origin(op_arg) in (Union, types.UnionType):
                expected_types = get_args(op_arg)
            else:
                expected_types = (op_arg,)

            for expected_type in expected_types:
                arg = parse_arg(arg_s, expected_type, mnemonic)
                args.append(arg)

        insts.append(op(*args))
    return insts


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("usage: asm in.cbf out.b", file=sys.stderr)
        exit(1)

    with open(sys.argv[1]) as f:
        in_contents = f.read()

    instrs = parse(in_contents)
    prog = Program(instrs)
    out_contents = prog.assemble()

    with open(sys.argv[2], "w") as f:
        f.write(out_contents)
        f.write("\n")

    # Generate addrmap
    with open(sys.argv[2] + ".addr", "w") as f:
        f.write("a0[2] next\n")
        f.write("a2[2] current\n")
        f.write(f"a2[{SCRAP_COUNT:x}] scraps\n")
        for i in range(len(regs)):
            f.write(f"a{i * 8 + SCRAP_COUNT + 2:x}[8] x{i + 1}\n")
