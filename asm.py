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
    is_jump_instruction,
    Block, LoadI,
)
from registers import SCRAP_COUNT, Immediate, Register, regs, OffsetRegister
from elftools.elf.elffile import ELFFile
from capstone import *
from capstone.riscv import RISCVOp


def split_program_into_blocks(instrs: list[Instruction]):
    root_block = Block(None, [], None)
    instr_id = 0
    entry_point_block = None
    for instr in instrs:
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
                mother_block.daughter_blocks.append(Block(idx, [], mother_block))
            mother_block = mother_block.daughter_blocks[val]

        mother_block.daughter_blocks.append(instr)
        if hasattr(instr, "is_entry_point") and instr.is_entry_point:
            if entry_point_block is not None:
                raise RuntimeError("Two entry points found")
            entry_point_block = mother_block
        if not is_jump_instruction(instr):
            mother_block.daughter_blocks.append(instructions.mnemonics.JumpNext())

        instr_id += 1

    if entry_point_block is None:
        raise RuntimeError("No entry point found")
    return root_block, entry_point_block


class Program:
    def __init__(self, instrs):
        self.kiloblock, self.entry_point_block = split_program_into_blocks(instrs)
        print("Entry block id:", self.get_block_full_id(self.entry_point_block))

    def get_block_full_id(self, block: Block):
        myid = []
        cur_block = block
        for i in range(4):
            assert cur_block is not None
            myid.append(cur_block.myid)
            cur_block = cur_block.mother_block
        return myid

    def find_block(self, label: str, root_block=None):
        if root_block is None:
            root_block = self.kiloblock
        for block in root_block.daughter_blocks:
            if isinstance(block.daughter_blocks[0], Instruction):
                if label in block.labels:
                    return [block.myid]
            else:
                out = self.find_block(label, block)
                if out is not None:
                    out.append(block.myid)
                    return out
        if root_block == self.kiloblock:
            raise ValueError(f"Block {label} not found")
        return None

    def find_block_rel(self, block: Block, offset):
        assert offset % 4 == 0
        out = self.get_block_full_id(block)
        out[0] += offset
        for i in range(4):
            if out[i] >= BLOCK_SIZE:
                if i == 3:
                    raise RuntimeError("Too many blocks")
                out[i] = 0
                out[i + 1] += 1
        return out

    def program_prologue(self):
        entry_point_block_id = self.get_block_full_id(self.entry_point_block)
        for next_, new_next in zip(nexts, entry_point_block_id):
            next_.change(new_next)
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
            if config.BREAKPOINT_AFTER_EVERY_INSTRUCTION:
                concater.raw("#")
        else:
            for bl in block.daughter_blocks:
                self.assemble_block(bl, deep + 1)
        self.block_epilogue(block, deep)

    def assemble_program(self):
        LoadI(regs["sp"], Immediate(0xFFFFFFFF))
        self.program_prologue()
        for block in self.kiloblock.daughter_blocks:
            self.assemble_block(block)
        self.program_epilogue()
        out = concater.get_code()
        concater.reset_code()
        return out


def parse_arg(arg: str, expected_type: type):
    """Parse a single argument string to the expected type."""
    arg = arg.strip()
    if expected_type == Register:
        if arg in regs:
            return regs[arg]
        raise ValueError(f"Register {arg} is unavailable")
    elif expected_type == Immediate:
        return Immediate.from_str(arg)
    elif expected_type == OffsetRegister:
        imm, reg = arg.split("(")
        imm = Immediate.from_str(imm)
        assert reg.endswith(")")
        reg = reg[:-1]
        if reg in regs:
            reg = regs[reg]
        else:
            raise ValueError(f"Register {arg} is unavailable")
        return OffsetRegister(reg, imm)
    else:
        raise ValueError(f"Unknown expected type: {expected_type}")


def get_instruction_types(op: type[Instruction]):
    hints = get_type_hints(op)
    op_args = list(hints.values())
    arg_types = []
    for op_arg in op_args:
        if get_origin(op_arg) in (Union, types.UnionType):
            arg_types.append(get_args(op_arg))
        else:
            arg_types.append(op_arg, )
    return arg_types


def parse_elf(path: str):
    memory = {}

    with open(path, "rb") as file:
        elf = ELFFile(file)

        for segment in elf.iter_segments():
            if segment['p_type'] != 'PT_LOAD':
                continue

            vaddr = segment['p_vaddr']
            data = segment.data()
            # segment['p_memsz']

            for i, b in enumerate(data):
                memory[vaddr + i] = b

        text = elf.get_section_by_name(".text")
        code = text.data()
        base = text['sh_addr']

        entry_point_addr = elf.header['e_entry']
        print(f"0x{entry_point_addr:x} - ENTRY_POINT\n")

    md = Cs(CS_ARCH_RISCV, CS_MODE_RISCV32)
    instrs = []
    entry_point_found = False
    for instr in md.disasm(code, base):
        mnemonic = MNEMONICS[instr.mnemonic]
        print(f"0x{instr.address:x}:\t{instr.mnemonic}\t{instr.op_str}")
        args = instr.op_str
        if args == "":
            args = []
        else:
            args = args.split(",")
        types_ = get_instruction_types(mnemonic)

        # Remove prettify from some instructions
        if instr.mnemonic == "jal" and len(args) == 1:
            args.insert(0, "ra")

        if len(args) != len(types_):
            raise ValueError(
                f"Incorrect number of arguments for {mnemonic}. Got {len(args)}, expected {len(types_)}.\nGot {args}")
        for i in range(len(args)):
            try:
                args[i] = parse_arg(args[i], types_[i])
            except ValueError as e:
                raise ValueError(mnemonic, args, e)

        is_entry_point = (instr.address == entry_point_addr)
        if is_entry_point:
            if entry_point_found:
                raise ValueError("Two instructions are entry points")
            entry_point_found = True
        instruction_obj = mnemonic(*args)
        instruction_obj.is_entry_point = is_entry_point
        instrs.append(instruction_obj)
    if not entry_point_found:
        raise ValueError(f"Can't find entry point: No instruction on address 0x{entry_point_addr:x}")
    return instrs, memory


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("usage: asm in.cbf out.b", file=sys.stderr)
        exit(1)

    instrs, memory = parse_elf(sys.argv[1])
    # print(memory)
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
        for j in range(REGISTER_COUNT):  # TODO: Replace with REGISTER_COUNT
            f.write(f"a{j * 8 + SCRAP_COUNT - MEMORY_SCRAPS_COUNT + 4:x}[8] x{j + 1}\n")
        f.write(
            f"a{REGISTER_COUNT * 8 + SCRAP_COUNT - MEMORY_SCRAPS_COUNT + 4:x}[{MEMORY_SCRAPS_COUNT :x}] mem_scraps\n")
        f.write(
            f"a{REGISTER_COUNT * 8 + SCRAP_COUNT - MEMORY_SCRAPS_COUNT + 4 + MEMORY_SCRAPS_COUNT:x}[{256:x}] memory\n")
