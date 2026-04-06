#! /bin/python
from __future__ import annotations

import types
from typing import Union, get_args, get_origin, get_type_hints

import config
import instructions.mnemonics
from cell import concater
from config import REGISTER_COUNT, MEMORY_SCRAPS_COUNT, BLOCK_COUNT
from instructions.baseInstructions import Instruction, Block
from instructions.mnemonics import (
    MNEMONICS,
    is_block_boundary,
    Block,
)
from registers import SCRAP_COUNT, Immediate, Register, regs, OffsetRegister


def split_program_into_blocks(instrs: list[Instruction]):
    root_block = Block(0, [], None, "root_block")
    block_name = None
    instr_id = 0
    for instr in instrs:
        if isinstance(instr, instructions.mnemonics.LabelDefine):
            block_name = instr.name
        else:
            mother_block = root_block
            for i in range(3, -1, -1):
                val = instr_id // (BLOCK_COUNT ** i)
                if i == 0:
                    assert val < (BLOCK_COUNT - 1)

                if len(mother_block.daughter_blocks) <= val:
                    assert len(mother_block.daughter_blocks) == val
                    mother_block.daughter_blocks.append(Block(val, [], mother_block, block_name if i == 0 else None))
                mother_block = mother_block.daughter_blocks[val]

            mother_block.daughter_blocks.append(instr)
            if not is_block_boundary(instr):
                mother_block.daughter_blocks.append(instructions.mnemonics.JumpRelative(Immediate(1)))

            block_name = None
            instr_id += 1
    return root_block


class Program:
    def __init__(self, instrs):
        self.kiloblock = split_program_into_blocks(instrs)
        print(self.find_block("less"))

    def find_block(self, name: Block | str, root_block=None):
        if root_block is None:
            root_block = self.kiloblock
        for block in root_block.daughter_blocks:
            if isinstance(block.daughter_blocks[0], Instruction):
                if (isinstance(name, Block) and name == block) or \
                        (isinstance(name, str) and block.name == name):
                    return [block.myid]
            else:
                out = self.find_block(name, block)
                if out is not None:
                    out.append(block.myid)
                    return out
        if root_block == self.kiloblock:
            raise ValueError(f"Block {name} not found")
        return None

    def find_next_block(self, block: Block):
        out = self.find_block(block)
        out[0] += 1
        for i in range(4):
            if i == 0:
                assert out[i] < (BLOCK_COUNT - 1)
            if out[i] >= BLOCK_COUNT:
                out[i] = 0
                out[i - 1] += 1
        return out

    def program_prologue(self):
        return ">>>+[-<<<[>>>>+<<<<-]>[>>>>+<<<<-]>[>>>>+<<<<-]>[>>>>+<<<<-]>>>>"

    def program_epilogue(self):
        # TODO: Make program not cycling if not found block
        out = "<<<<"
        if config.BREAKPOINT_EVERY_CYCLE:
            out += "#"
        out += "+]"
        return out

    def block_prologue(self, block: Block, deep: int):  # TODO: use concater
        assert deep < 4
        name = block.name
        if name is None:
            name = f"block_{block.myid}"
        name_line = f"{concater.sanitize(name)}:"
        out = f"\n{name_line}\n"
        if block.mother_block.daughter_blocks.index(block) != 0:
            out += "-"
        out += ">+<[>-]>[-"
        if deep != 3:
            deep += 1
            out += "<"
            out += "<" * deep
            out += "["
            out += ">" * deep
            out += "+"
            out += "<" * deep
            out += "-"
            out += "]"
            out += ">" * deep
        return out

    def block_epilogue(self, deep: int):
        assert deep < 4
        out = "\n"
        if deep != 3:
            out += ">"
        out += "<[-]>>]<<"  # clearing address value
        return out  # TODO: add skipping by [

    def assemble_block(self, block: Block, deep: int = 0):
        if isinstance(block.daughter_blocks[-1], Instruction):
            concater.init_block()
            for inst in block.daughter_blocks:
                inst.evaluate(self, block, True)
            inside = concater.get_block_code()
        else:
            inside = "".join([self.assemble_block(bl, deep + 1) for bl in block.daughter_blocks])
        return (
                self.block_prologue(block, deep)
                + inside
                + self.block_epilogue(deep)
        )

    def assemble(self):
        out = self.program_prologue()
        out += "\n".join(
            [self.assemble_block(block) for block in self.kiloblock.daughter_blocks]
        )
        out += self.program_epilogue()
        return out


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
        offset = offset.strip()
        register = register.strip()
        return OffsetRegister(regs[register], Immediate.from_text(offset))
    elif expected_type == instructions.mnemonics.Label:
        return instructions.mnemonics.Label(arg_s)
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
        f.write("a0[4] next\n")
        f.write("a4[4] current\n")
        f.write(f"a4[{SCRAP_COUNT - MEMORY_SCRAPS_COUNT:x}] scraps\n")
        for i in range(4):  # TODO: Replace with REGISTER_COUNT
            f.write(f"a{i * 8 + SCRAP_COUNT - MEMORY_SCRAPS_COUNT + 4:x}[8] x{i + 1}\n")
        f.write(
            f"a{REGISTER_COUNT * 8 + SCRAP_COUNT - MEMORY_SCRAPS_COUNT + 4:x}[{MEMORY_SCRAPS_COUNT :x}] mem_scraps\n")
        f.write(
            f"a{REGISTER_COUNT * 8 + SCRAP_COUNT - MEMORY_SCRAPS_COUNT + 4 + MEMORY_SCRAPS_COUNT:x}[{256:x}] memory\n")
