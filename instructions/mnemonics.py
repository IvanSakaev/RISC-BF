from __future__ import annotations

from contextlib import contextmanager

from config import MAX_OUTPUT_LENGTH_HALFBYTES
from instructions.arithmeticInstructions import *
import instructions.bitwiseInstructions
from instructions.comparingInstructions import *
from instructions.jumpInstructions import *
from instructions.storeInstructions import *

from instructions.baseInstructions import Instruction, Block
from dataclasses import dataclass

from instructions.storeInstructions import _go_to_addr, _go_from_addr

if TYPE_CHECKING:
    from asm import Program


@dataclass
class LoadI(Instruction):
    dst: Register
    src: Immediate

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"li {self.dst} {self.src}", comments)
        AddI(self.dst, ZERO, self.src).evaluate(program, cur_block, False)


@dataclass
class LoadUpperI(Instruction):
    dst: Register
    src: Immediate

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"li {self.dst} {self.src}", comments)
        inst = LoadI(self.dst, Immediate(self.src * (2 ** 12)))
        inst.evaluate(program, cur_block, False)


@dataclass
class Move(Instruction):
    dst: Register
    src: Register

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"mv {self.dst} {self.src}", comments)
        AddI(self.dst, self.src, Immediate(0)).evaluate(program, cur_block, False)


@dataclass
class Nop(Instruction):
    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem("nop", comments)


@dataclass
class Debug(Instruction):
    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem("ebreak", comments)
        concater.debug()


@dataclass
class Output(Instruction):
    reg: Register

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"out {self.reg}", comments)
        if self.reg == ZERO:
            return

        # Division by 10
        mod = scraps[0]
        # 2 scraps after MOD are used too
        output = scraps[3]
        # scrap 4 is used too

        for small in reversed(self.reg.get_cells()):
            small.div_imm(10)

            mod.copy(small, scrap=scraps[4])
            mod.change(48)

            with output.loop():
                output.change(-1)
                small.change(10)
                mod.change(48, 65)  # Start at ASCII `A`
            mod.raw(".")
            mod.clear()
        mod.change(10)  # Line feed
        mod.raw(".")
        mod.clear()


@dataclass
class Ecall(Instruction):
    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem("ecall", comments)
        with self.if_number(regs["a7"], Immediate(64)):
            addr_reg = regs["a1"]
            length_reg = regs["a2"]

            Output(addr_reg).evaluate(program, cur_block)
            Output(length_reg).evaluate(program, cur_block)

            mem_scraps = memory_scraps[
                len(memory_scraps) - 2 - MEMORY_ADDRESS_HALFBYTES - (MAX_OUTPUT_LENGTH_HALFBYTES * 2):]
            zero_scrap = mem_scraps[0]
            addr_cells = mem_scraps[1: MEMORY_ADDRESS_HALFBYTES + 1]
            addr_scrap = mem_scraps[MEMORY_ADDRESS_HALFBYTES + 1]
            length_to = mem_scraps[MEMORY_ADDRESS_HALFBYTES + 2: MEMORY_ADDRESS_HALFBYTES + 2 + MAX_OUTPUT_LENGTH_HALFBYTES]
            length_copy = mem_scraps[MEMORY_ADDRESS_HALFBYTES + 2 + MAX_OUTPUT_LENGTH_HALFBYTES:]
            first_mem_cell = mem_scraps[-1].cell_rel(1)

            for i in range(MEMORY_ADDRESS_HALFBYTES):
                addr_reg.get_cell(i).copy(addr_cells[i], scrap=zero_scrap)
            for i in range(MAX_OUTPUT_LENGTH_HALFBYTES):
                if i < MAX_OUTPUT_LENGTH_HALFBYTES:
                    length_reg.get_cell(i).move(length_to[i], length_copy[i])
                else:
                    length_reg.get_cell(i).assert_val(0)
            _go_to_addr(mem_scraps, zero_scrap, addr_cells, addr_scrap)
            concater.debug()
            first_mem_cell.raw(".")
            _go_from_addr(mem_scraps, zero_scrap, addr_cells)

    @contextmanager
    def if_number(self, reg: Register, num: Immediate):
        scrap = scraps[0]
        result = scraps[1]
        result.change(1)

        for i in range(8):
            small_reg = reg.get_cell(i)
            small_num = num // (16 ** i) % 16
            small_reg.change(-small_num)
            small_reg.move(scrap)
            with scrap.loop():
                result.change(-1)
                scrap.move(small_reg)
            small_reg.change(small_num)
            result.raw("[")
        result.change(-1)
        yield
        result.raw("]" * 8)


MNEMONICS: dict[str, type[Instruction]] = dict()

# Pseudo-instructions
MNEMONICS["li"] = LoadI
MNEMONICS["lui"] = LoadUpperI
MNEMONICS["mv"] = Move
MNEMONICS["neg"] = Neg
MNEMONICS["nop"] = Nop

# Arithmetic
MNEMONICS["add"] = Add
MNEMONICS["addi"] = AddI
MNEMONICS["sub"] = Sub
MNEMONICS["mul"] = Mul
MNEMONICS["mulhu"] = MulHighUnsigned

# bitwise
MNEMONICS["sll"] = instructions.bitwiseInstructions.ShiftLeft  # TODO
MNEMONICS["slli"] = instructions.bitwiseInstructions.ShiftLeftI
MNEMONICS["or"] = instructions.bitwiseInstructions.Or
MNEMONICS["and"] = instructions.bitwiseInstructions.And
MNEMONICS["xor"] = instructions.bitwiseInstructions.Xor
MNEMONICS["not"] = instructions.bitwiseInstructions.Not
MNEMONICS["ori"] = instructions.bitwiseInstructions.OrI
MNEMONICS["andi"] = instructions.bitwiseInstructions.AndI
MNEMONICS["xori"] = instructions.bitwiseInstructions.XorI

# comparing
MNEMONICS["slt"] = SetLessThan
MNEMONICS["slti"] = SetLessThanI
MNEMONICS["sltu"] = SetLessThanUnsigned
MNEMONICS["sltiu"] = SetLessThanIUnsigned
MNEMONICS["seqz"] = SetEqualToZero
MNEMONICS["snez"] = SetNotEqualToZero
MNEMONICS["sltz"] = SetLessThanZero
MNEMONICS["sgtz"] = SetGreaterThanZero

# store/load
MNEMONICS["sw"] = StoreWord
MNEMONICS["sh"] = StoreHalfword
MNEMONICS["sb"] = StoreByte
MNEMONICS["lw"] = LoadWord
MNEMONICS["lh"] = LoadHalfword
MNEMONICS["lhu"] = LoadHalfwordUnsigned
MNEMONICS["lb"] = LoadByte
MNEMONICS["lbu"] = LoadByteUnsigned

# jump
MNEMONICS["j"] = Jump
MNEMONICS["jr"] = JumpRegister
MNEMONICS["jal"] = JumpAndLink
MNEMONICS["jalr"] = JumpAndLinkRegister
MNEMONICS["call"] = Call
MNEMONICS["ret"] = Ret
# conditional jump
MNEMONICS["beq"] = BranchIfEqual
MNEMONICS["bne"] = BranchIfNotEqual
MNEMONICS["blt"] = BranchIfLessThan
MNEMONICS["bltu"] = BranchIfLessThanUnsigned
MNEMONICS["bge"] = BranchIfGreaterThanOrEqual
MNEMONICS["bgeu"] = BranchIfGreaterThanOrEqualUnsigned
MNEMONICS["beqz"] = BranchIfEqualToZero
MNEMONICS["bnez"] = BranchIfNotEqualToZero
# conditional jump pseudo-instructions
MNEMONICS["blez"] = BranchIfLessThanOrEqualToZero
MNEMONICS["bgez"] = BranchIfGreaterThanOrEqualToZero
MNEMONICS["bltz"] = BranchIfLessThanZero
MNEMONICS["bgtz"] = BranchIfGreaterThanZero
MNEMONICS["bgt"] = BranchIfGreaterThan
MNEMONICS["ble"] = BranchIfLessThanOrEqual
MNEMONICS["bgtu"] = BranchIfGreaterThanUnsigned
MNEMONICS["bleu"] = BranchIfLessThanOrEqualUnsigned

# special
MNEMONICS["ebreak"] = Debug
MNEMONICS["out"] = Output
MNEMONICS["ecall"] = Ecall


def is_jump_instruction(instr):
    return isinstance(
        instr,
        (
            Jump,
            JumpRegister,
            JumpAndLink,
            JumpAndLinkRegister,
            Call,
            Ret,

            # branches
            BranchIfEqual,
            BranchIfNotEqual,
            BranchIfLessThan,
            BranchIfLessThanUnsigned,
            BranchIfGreaterThanOrEqual,
            BranchIfGreaterThanOrEqualUnsigned,
            BranchIfEqualToZero,
            BranchIfNotEqualToZero,

            # pseudo-instructions
            BranchIfLessThanOrEqualToZero,
            BranchIfGreaterThanOrEqualToZero,
            BranchIfLessThanZero,
            BranchIfGreaterThanZero,
            BranchIfGreaterThan,
            BranchIfLessThanOrEqual,
            BranchIfGreaterThanUnsigned,
            BranchIfLessThanOrEqualUnsigned,
        ),
    )
