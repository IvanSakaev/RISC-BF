#! /bin/python
from __future__ import annotations

import types
from typing import Union, get_args, get_origin, get_type_hints

import config
import instructions.mnemonics
from cell import concater, nexts, currents
from config import REGISTER_COUNT, MEMORY_SCRAPS_COUNT, BLOCK_SIZE
from instructions.baseInstructions import Instruction
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
                if i == 0:
                    val = instr_id % (BLOCK_SIZE // 4)
                else:
                    val = instr_id // (BLOCK_SIZE ** (i - 1)) // (BLOCK_SIZE // 4)
                    val %= BLOCK_SIZE

                idx = val
                if i == 3:
                    idx += 1
                elif i == 0:
                    idx *= 4
                if len(mother_block.daughter_blocks) <= val:
                    assert len(mother_block.daughter_blocks) == val
                    mother_block.daughter_blocks.append(Block(idx, [], mother_block, block_name if i == 0 else None))
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

    def find_block(self, name: Block | str, root_block=None):  # TODO: optimize finding by block obj
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
        out[0] += 4
        for i in range(4):
            if out[i] >= BLOCK_SIZE:
                if i == 3:
                    raise RuntimeError("Too many blocks")
                out[i] = 0
                out[i + 1] += 1
        return out

    def program_prologue(self):
        nexts[-1].change(1)
        nexts[-1].raw("[")
        for i in range(4):
            nexts[i].move(currents[i])

    def program_epilogue(self):
        currents[-1].raw("-]")
        if config.BREAKPOINT_EVERY_CYCLE:
            concater.debug()
        nexts[-1].raw("]")

    def block_prologue(self, block: Block, deep: int):
        assert deep < 4
        name = block.name
        if name is None:
            name = f"block_{block.myid}"
        name_line = f"{concater.sanitize(name)}:"
        concater.raw("\n")
        concater.raw(f"{name_line}\n")
        if block.myid != 0:
            currents[-1].change(-4 if deep == 3 else -1)
        currents[-1].raw(">+<[>-]>[-", pos_offset=1)
        if deep != 3:
            currents[-2 - deep].move(currents[-1])

    def block_epilogue(self, block: Block, deep: int):
        assert deep < 4
        concater.raw("\n")
        if len(block.daughter_blocks) > 0 and deep != 3:
            currents[-1].change(-1)
            currents[-1].raw("]" * len(block.daughter_blocks))
        currents[-1].cell_rel(2).raw("]")
        currents[-1].raw("[")

    def assemble_block(self, block: Block, deep: int = 0):
        self.block_prologue(block, deep)
        if isinstance(block.daughter_blocks[-1], Instruction):
            for inst in block.daughter_blocks:
                inst.evaluate(self, block, True)
                concater.assert_pos()
        else:
            for bl in block.daughter_blocks:
                self.assemble_block(bl, deep + 1)
        self.block_epilogue(block, deep)

    def assemble_program(self):
        self.program_prologue()
        for block in self.kiloblock.daughter_blocks:
            self.assemble_block(block)
        self.program_epilogue()
        out = concater.get_code()
        concater.reset_code()
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


def parse(s: str):  # TODO: Make `label: addi x1, x2, 1` work
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
    out_contents = prog.assemble_program()

    with open(sys.argv[2], "w") as f:
        f.write(out_contents)
        f.write("\n")

    # Generate addrmap
    with open(sys.argv[2] + ".addr", "w") as f:
        f.write("a0[4] next\n")
        f.write("a4[4] current\n")
        f.write(f"a4[{SCRAP_COUNT - MEMORY_SCRAPS_COUNT:x}] scraps\n")
        for j in range(4):  # TODO: Replace with REGISTER_COUNT
            f.write(f"a{j * 8 + SCRAP_COUNT - MEMORY_SCRAPS_COUNT + 4:x}[8] x{j + 1}\n")
        f.write(
            f"a{REGISTER_COUNT * 8 + SCRAP_COUNT - MEMORY_SCRAPS_COUNT + 4:x}[{MEMORY_SCRAPS_COUNT :x}] mem_scraps\n")
        f.write(
            f"a{REGISTER_COUNT * 8 + SCRAP_COUNT - MEMORY_SCRAPS_COUNT + 4 + MEMORY_SCRAPS_COUNT:x}[{256:x}] memory\n")
