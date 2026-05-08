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
        with self.if_number(regs["a7"], Immediate(63)):
            self.ecall63_64(",")
        with self.if_number(regs["a7"], Immediate(64)):
            self.ecall63_64(".")

    def ecall63_64(self, command):
        # Maybe not ignore a0?
        output_reg = regs["a0"]
        addr_reg = regs["a1"]
        length_reg = regs["a2"]

        mem_scraps = memory_scraps[
            len(memory_scraps) - 2 - MEMORY_ADDRESS_HALFBYTES - (MAX_OUTPUT_LENGTH_HALFBYTES * 2):]
        zero_scrap = mem_scraps[0]
        addr_cells = mem_scraps[1: MEMORY_ADDRESS_HALFBYTES + 1]
        addr_scrap = mem_scraps[MEMORY_ADDRESS_HALFBYTES + 1]
        length_to = mem_scraps[
            MEMORY_ADDRESS_HALFBYTES + 2: MEMORY_ADDRESS_HALFBYTES + 2 + MAX_OUTPUT_LENGTH_HALFBYTES]
        length_copy = mem_scraps[MEMORY_ADDRESS_HALFBYTES + 2 + MAX_OUTPUT_LENGTH_HALFBYTES:]

        for i in range(MEMORY_ADDRESS_HALFBYTES):
            addr_reg.get_cell(i).copy(addr_cells[i], scrap=zero_scrap)
        for i in range(MAX_OUTPUT_LENGTH_HALFBYTES):
            if i < MAX_OUTPUT_LENGTH_HALFBYTES:
                length_reg.get_cell(i).copy(length_to[i], scrap=zero_scrap)
            else:
                length_reg.get_cell(i).assert_val(0)

        _go_to_addr(mem_scraps, zero_scrap, addr_cells, addr_scrap)

        # Move zero_scrap to right
        for small_addr_cell in addr_cells:
            small_addr_cell.move(small_addr_cell.cell_rel(-1))
        addr_cells = mem_scraps[0: MEMORY_ADDRESS_HALFBYTES]
        zero_scrap = mem_scraps[MEMORY_ADDRESS_HALFBYTES]

        self._write_str(zero_scrap, addr_scrap, length_to, length_copy, command)

        # Move zero_scrap back
        for small_addr_cell in reversed(addr_cells):
            small_addr_cell.move(small_addr_cell.cell_rel(1))
        addr_cells = mem_scraps[1: MEMORY_ADDRESS_HALFBYTES + 1]
        zero_scrap = mem_scraps[0]

        _go_from_addr(mem_scraps, zero_scrap, addr_cells)

        output_reg.clear_big()
        for small_length_copy, small_output in zip(length_copy, output_reg.get_cells()):
            small_length_copy.move(small_output)
        concater.debug()

    def _write_str(self, zero_scrap: Cell, addr_scrap: Cell, length_to: list[Cell], length_copy: list[Cell],
                   command: str = "."):
        assert zero_scrap.cell_rel(1) == addr_scrap
        assert addr_scrap.cell_rel(1) == length_to[0]
        assert length_to[-1].cell_rel(1) == length_copy[0]
        mem_scraps = [zero_scrap, addr_scrap, *length_to, *length_copy]
        first_mem_cell = mem_scraps[-1].cell_rel(1)

        for small_length_copy in length_copy:
            small_length_copy.change(-15)

        # Coming right and printing
        self._sub_length(length_to, None, zero_scrap, addr_scrap)
        zero_scrap.change(1)  # It can be -1 before this command
        with zero_scrap.loop():
            zero_scrap.change(-1)
            first_mem_cell.raw(command)
            first_mem_cell.move(zero_scrap)
            for i in range(len(mem_scraps) - 1, 0, -1):
                mem_scraps[i].move(mem_scraps[i].cell_rel(1))
            concater.raw("", -1)

            self._sub_length(length_copy, None, zero_scrap, addr_scrap, is_negative=True)
            if command == ".":
                self._sub_length(length_to, zero_scrap, zero_scrap, addr_scrap)
                zero_scrap.change(1)  # It can be -1 before this command
            else:
                printed_mem_cell = zero_scrap.cell_rel(-1)
                printed_mem_cell.change(-10)  # \n
                with printed_mem_cell.loop():
                    self._sub_length(length_to, zero_scrap, zero_scrap, addr_scrap)
                    zero_scrap.change(1)  # It can be -1 before this command
                    printed_mem_cell.move(addr_scrap)
                addr_scrap.move(printed_mem_cell)
                printed_mem_cell.change(10)

        for small_length_to, small_length_copy in zip(length_to, length_copy):
            small_length_to.clear()
            small_length_copy.change(15)
            small_length_copy.copy(small_length_to, scrap=addr_scrap)

        # Coming back
        self._sub_length(length_to, None, zero_scrap, addr_scrap)
        zero_scrap.change(1)  # It can be -1 before this command
        with zero_scrap.loop():
            zero_scrap.change(-1)
            for i in range(1, len(mem_scraps)):
                mem_scraps[i].move(mem_scraps[i].cell_rel(-1))
            zero_scrap.cell_rel(-1).move(mem_scraps[-1])
            concater.raw("", 1)

            self._sub_length(length_to, zero_scrap, zero_scrap, addr_scrap)
            zero_scrap.change(1)  # It can be -1 before this command

        for small_length_to in length_to:
            small_length_to.clear()

    def _sub_length(self, length: list[Cell], output: Cell | None, scrap1: Cell, scrap2: Cell,
                    is_negative: bool = False):
        """
        Output and scrap1 can be the same. Output can be None.
        """
        scrap2.change(1)
        with length[0].loop():
            length[0].move(scrap1)
            scrap2.change(-1)
        scrap1.move(length[0])
        with scrap2.loop():
            scrap2.change(-1)
            if len(length) == 1:
                if output is not None:
                    output.change(-1)
            else:
                self._sub_length(length[1:], output, scrap1, scrap2, is_negative=is_negative)
            length[0].change(-16 if is_negative else 16)
        length[0].change(1 if is_negative else -1)

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
MNEMONICS["sll"] = instructions.bitwiseInstructions.ShiftLeft  # TODO: srl
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
