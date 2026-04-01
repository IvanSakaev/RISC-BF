#! /bin/python
from __future__ import annotations

import types
from typing import Union, get_args, get_origin, get_type_hints

import config
import instructions.mnemonics
from cell import concater
from config import REGISTER_COUNT
from instructions.mnemonics import (
    MNEMONICS,
    is_block_boundary,
    Block,
    KiloBlock,
)
from registers import SCRAP_COUNT, Immediate, Register, regs, OffsetRegister


def split_program_into_blocks(instrs):
    blocks = []
    cur_block = []
    block_name = None
    for i in instrs:
        if not isinstance(i, instructions.mnemonics.LabelDefine):
            cur_block.append(i)
        if is_block_boundary(i):
            if isinstance(i, instructions.mnemonics.LabelDefine):
                cur_block.append(instructions.mnemonics.JumpRelative(Immediate(1)))

            blocks.append(
                Block(
                    0, KiloBlock(0, []), block_name, cur_block
                )
            )
            cur_block = []
            if isinstance(i, instructions.mnemonics.LabelDefine):
                block_name = i.name
            else:
                block_name = None

    cur_block.append(instructions.mnemonics.JumpRelative(Immediate(1)))
    blocks.append(
        Block(0, KiloBlock(0, []), block_name, cur_block)
    )

    return blocks


def split_blocks_into_kiloblocks(blocks: list[Block]):
    kiloblocks = [KiloBlock(1, [])]
    i = 0
    for block in blocks:
        i += 1
        if i > config.BLOCKS_IN_KILOBLOCK:
            i = 1
            kiloblocks.append(KiloBlock(len(kiloblocks) + 1, []))
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

    def find_next_block(self, block: Block):
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

    def kiloblock_prologue(self, kiloblock: KiloBlock):
        name = f"kiloblock_{kiloblock.myid}"
        name_line = f"{concater.sanitize(name)}:"
        return f"\n{name_line}\n->+<[>-]>[>]<[-<<[>+<-]>\n"

    def kiloblock_epilogue(self, kiloblock: KiloBlock):
        return "\nend_kiloblock -" + "]" * len(kiloblock.blocks) + " >]<["

    def block_prologue(self, block: Block):
        name = block.name
        if name is None:
            name = f"block_{block.myid}"
        name_line = f"{concater.sanitize(name)}:"

        return f"\n{name_line}\n->+<[>-]>[>]<[-"

    def block_epilogue(self):
        return "\n]<["

    def assemble_block(self, block: Block):
        concater.init_block()
        for inst in block.insts:
            inst.evaluate(self, block, True)
        return (
                self.block_prologue(block)
                + concater.get_block_code()
                + self.block_epilogue()
        )

    def assemble_kiloblock(self, kiloblock: KiloBlock):
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


def parse_arg(arg_s: str, expected_type: type):
    """Parse a single argument string to the expected type."""
    arg_s = arg_s.strip()

    if expected_type == Register:
        if arg_s in regs:
            return regs[arg_s]
        raise ValueError(f"Register {arg_s} is unavailable")
    elif expected_type == Immediate:
        return Immediate.from_text(arg_s)
    elif expected_type == OffsetRegister:
        offset, register = arg_s.split("(")
        assert register.endswith(")")
        register = register[:-1]
        return OffsetRegister(regs[register], Immediate.from_text(offset))
    elif expected_type == instructions.mnemonics.Label:
        return instructions.mnemonics.Label(arg_s[1:-1])
    else:
        raise ValueError(f"Unknown expected type: {expected_type}")


def parse(s: str):
    if not hasattr(parse, "_instruction_arg_types"):
        parse._instruction_arg_types = {}
        for mnem, op in MNEMONICS.items():
            hints = get_type_hints(op)
            op_args = list(hints.values())
            arg_types = []
            for op_arg in op_args:
                if get_origin(op_arg) in (Union, types.UnionType):
                    expected_types = get_args(op_arg)
                else:
                    expected_types = (op_arg,)
                arg_types.append(expected_types)
            parse._instruction_arg_types[mnem] = arg_types

    insts: list[instructions.mnemonics.Instruction | instructions.mnemonics.LabelDefine] = []
    for line in s.split("\n"):
        # Удаляем комментарии и метки
        if "#" in line:
            line = line[: line.find("#")]
        if "." in line:
            line = line[: line.find(".")]
        line = line.strip()
        if not line:
            continue
        if line.endswith(":"):
            insts.append(instructions.mnemonics.LabelDefine(line[:-1]))
            continue

        if " " not in line:
            mnemonic = line
            args_str = ""
        else:
            mnemonic = line[: line.find(" ")]
            args_str = line[line.find(" "):].strip(" ")

        mnemonic = mnemonic.lower()
        if mnemonic not in MNEMONICS:
            raise ValueError(f"Unknown mnemonic: {mnemonic}")
        arg_types_list = parse._instruction_arg_types[mnemonic]

        if args_str:
            arg_strings = [a.strip() for a in args_str.split(",")]
        else:
            arg_strings = []

        if len(arg_strings) != len(arg_types_list):
            raise ValueError(
                f"Wrong number of arguments for {mnemonic}, expected {len(arg_types_list)} "
                f"arguments, got {len(arg_strings)}"
            )

        args: list = []
        for arg_s, expected_types in zip(arg_strings, arg_types_list):
            for expected_type in expected_types:
                try:
                    arg = parse_arg(arg_s, expected_type)
                    args.append(arg)
                    break
                except Exception as e:
                    raise ValueError(
                        f"Failed to parse argument '{arg_s}' for {mnemonic}: {e}\n"
                        f"Expected type: {expected_type.__name__}"
                    )

        mnemonic_obj = MNEMONICS[mnemonic](*args)
        insts.append(mnemonic_obj)
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
        f.write(f"a2[{SCRAP_COUNT:x}] scraps\n")  # TODO: print only scraps before registers
        for i in range(4):  # TODO: Replace with REGISTER_COUNT
            f.write(f"a{i * 8 + SCRAP_COUNT + 2:x}[8] x{i + 1}\n")
        f.write(f"a{REGISTER_COUNT * 8 + SCRAP_COUNT + 2:x}[{14:x}] mem_scraps\n")
        f.write(f"a{REGISTER_COUNT * 8 + SCRAP_COUNT + 16:x}[{256:x}] memory\n")
