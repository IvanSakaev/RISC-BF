from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from cell import concater, next1, next2
from registers import (
    ZERO,
    Cell,
    Immediate,
    Register,
    scraps,
)

if TYPE_CHECKING:
    from asm import Program


class Instruction:
    def evaluate(self, program: Program, cur_block: Block, comments: bool = False): ...


@dataclass
class Block(Instruction):
    myid: int
    kiloblock: "KiloBlock"
    name: str | None
    insts: list[Instruction]


@dataclass
class KiloBlock(Instruction):
    myid: int
    blocks: list[Block]


class Label(str): ...


@dataclass
class LabelDefine(Instruction):
    name: str


@dataclass
class Jump(Instruction):
    target: Label

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"jmp {self.target}", comments)
        i, j = program.find_block(self.target)
        next1.change(i)
        next2.change(j)


@dataclass
class JumpRelative(Instruction):
    offset: Immediate

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        next_i, next_j = program.find_next_block(cur_block)
        concater.rem(f"jmr {self.offset}", comments)
        next1.change(next_i)
        next2.change(next_j)


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
        inst = LoadI(self.dst, Immediate(self.src * (2**12)))
        inst.evaluate(program, cur_block, False)


@dataclass
class Add(Instruction):
    dst: Register
    src1: Register
    src2: Register

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"add {self.dst} {self.src1} {self.src2}", comments)
        if self.dst == ZERO:
            return

        self.src1, self.src2 = sorted(
            (self.src1, self.src2),
            key=lambda a: 0 if a == ZERO else (1 if a == self.dst else 2),
        )

        if self.src1 == ZERO and self.src2 == ZERO:
            self.dst.clear_big()
        elif self.src1 == ZERO and self.src2 == self.dst:
            pass
        elif self.src1 == self.dst and self.src2 == self.dst:
            self.dst.move_big(scraps[0])
            Register(scraps[0]).move_big(self.dst, multiplier=2)
            self.dst.normalize_big()
        elif self.src1 == ZERO:
            self.dst.clear_big()
            self.src2.copy_big(self.dst)
        elif self.src1 == self.dst:
            self.src2.copy_big(self.dst)
            self.dst.normalize_big()
        elif self.src1 == self.src2:
            self.dst.clear_big()
            self.src1.copy_big(self.dst, multiplier=2)
            self.dst.normalize_big()
        else:
            self.dst.clear_big()
            self.src1.copy_big(self.dst)
            self.src2.copy_big(self.dst)
            self.dst.normalize_big()


@dataclass
class AddI(Instruction):
    dst: Register
    src1: Register
    src2: Immediate

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"addi {self.dst} {self.src1} {self.src2}", comments)
        if self.dst == ZERO:
            return
        if self.src2 < 0:
            self.src2 = Immediate(2**32 + self.src2)

        if self.src1 == ZERO:
            self.dst.change_big(self.src2, clear=True)
        elif self.src1 == self.dst:
            self.dst.change_big(self.src2)
            if self.src2 == 0:
                pass
            elif self.src2 == 1:
                self.dst.normalize_big_fast()
            else:
                self.dst.normalize_big()
        else:
            self.dst.clear_big()
            self.src1.copy_big(self.dst)
            self.dst.change_big(self.src2)
            if self.src2 == 0:
                pass
            elif self.src2 == 1:
                self.dst.normalize_big_fast()
            else:
                self.dst.normalize_big()


@dataclass
class Sub(Instruction):
    dst: Register
    src1: Register
    src2: Register

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"sub {self.dst} {self.src1} {self.src2}", comments)
        if self.dst == ZERO:
            return

        if self.src1 == self.src2:
            self.dst.clear_big()
        elif self.src1 == self.dst and self.src2 == ZERO:
            pass
        elif self.src1 == ZERO and self.src2 == self.dst:
            self.dst.move_big(scraps[0])
            self.move_invert_big(scraps[0], self.dst)
            self.dst.normalize_big_fast()
        elif self.src1 == ZERO:
            self.move_invert_big(self.src2, self.dst, scrap=scraps[0], clear=True)
            self.dst.normalize_big_fast()
        elif self.src1 == self.dst:
            self.move_invert_big(self.src2, self.dst, scrap=scraps[0])
            self.dst.normalize_big()
        elif self.src2 == ZERO:
            self.dst.clear_big()
            self.src1.copy_big(self.dst)
        elif self.src2 == self.dst:
            self.dst.move_big(scraps[0])
            self.move_invert_big(scraps[0], self.dst)
            self.src1.copy_big(self.dst)
            self.dst.normalize_big()
        else:
            self.move_invert_big(self.src2, self.dst, scrap=scraps[0], clear=True)
            self.src1.copy_big(self.dst)
            self.dst.normalize_big()

    @classmethod
    def move_invert_big(
        cls,
        src: Cell | Register,
        dst: Cell | Register,
        scrap: Cell | Register | None = None,
        clear=False,
    ):
        """
        Moves bitwise not src to dst. After this function, src will become zero.
        Initial src value will be restored from scrap if scrap isn't None.

        Src must be normalized. Dst will be NOT normalized.
        If dst was zero or clear=True, every dst cell will be <= 0xf, excluding first cell that can be <=0x10.

        dst.normalize_big_fast() can be used after this function
        """
        src = Register(src)
        dst = Register(dst)
        if scrap is not None:
            scrap = Register(scrap)

        for small in dst.get_cells():
            if clear:
                small.clear()
            small.change(15)

        if scrap is None:
            scrap_cells = [None] * 8
        else:
            scrap_cells = scrap.get_cells()

        for small_src, small_dst, small_scrap in zip(
            src.get_cells(), dst.get_cells(), scrap_cells
        ):
            small_src.move(small_dst, multiplier=-1)
            if small_scrap is not None:
                small_src.move(small_scrap)

        dst.get_cell(0).change(1)
        if scrap is not None:
            scrap.move_big(src)


@dataclass
class Mul(Instruction):
    dst: Register
    src1: Register
    src2: Register

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"mul {self.dst} {self.src1} {self.src2}", comments)
        if self.dst == ZERO:
            return

        if self.src1 == ZERO or self.src2 == ZERO:
            self.dst.clear_big()
            return

        self.src1, self.src2 = sorted(
            (self.src1, self.src2),
            key=lambda a: 0 if a == self.dst else 1,
        )

        src1 = self.src1
        src2 = self.src2
        if self.src1 == self.dst:
            src1 = Register(scraps[6])
            if self.src2 == self.dst:
                src2 = Register(scraps[6])
            self.dst.move_big(src1)
        else:
            self.dst.clear_big()

        for i in range(8):
            is_first = i == 0
            is_last = i == 7

            output_scrap = scraps[0]
            scrap1 = digit1_cell_copy = scraps[1]
            digit2_cell_copy = scraps[2]
            # scrap2 and scrap3 is used for div_imm()
            next_translator = scraps[4]
            digit_scrap = scraps[5]  # used when src1 == src2
            final_output = self.dst.get_cell(i)

            if not is_first:
                next_translator.move(final_output)

            # final_output <= 0x70

            for digit1_num in range(0, i + 1):
                digit2_num = i - digit1_num

                digit1 = Cell(src1.addr + digit1_num)
                digit2 = Cell(src2.addr + digit2_num)
                if digit1 == digit2:
                    digit2.copy(digit_scrap, scrap=scrap1)
                    digit2 = digit_scrap

                # Multiply digits
                with digit2.loop():
                    digit1.copy(output_scrap, scrap=digit1_cell_copy)
                    if digit2 != digit_scrap:
                        digit2_cell_copy.change(1)
                    digit2.change(-1)

                if digit2 != digit_scrap:
                    digit2_cell_copy.move(digit2)

                # digit_output = digit1 * digit2
                # digit_output <= 0xe1

                output_scrap.div_imm(16, scrap1, None if is_last else next_translator)
                # scr1 <= 0xf
                # next_translator <= 0xe
                # next_translator <= 0x62 (summary)
                scrap1.move(final_output)
                # final_output <= 0xe8

            if not is_first:
                final_output.div_imm(16, scrap1, None if is_last else next_translator)
                scrap1.move(final_output)
                # next_translator <= 0x70

        if self.src1 == self.dst:
            src1.clear_big()


@dataclass
class MulHighUnsigned(Instruction):
    dst: Register
    src1: Register
    src2: Register

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"mulhu {self.dst} {self.src1} {self.src2}", comments)
        if self.dst == ZERO:
            return

        if self.src1 == ZERO or self.src2 == ZERO:
            self.dst.clear_big()
            return

        self.src1, self.src2 = sorted(
            (self.src1, self.src2),
            key=lambda a: 0 if a == self.dst else 1,
        )

        src1 = self.src1
        src2 = self.src2
        if self.src1 == self.dst:
            src1 = Register(scraps[7])
            if self.src2 == self.dst:
                src2 = src1
            self.dst.move_big(src1)
        else:
            self.dst.clear_big()

        for i in range(16):
            is_first = i == 0
            is_last = i == 15

            output_scrap = scraps[0]
            scrap1 = digit1_cell_copy = scraps[1]
            digit2_cell_copy = scraps[2]
            # scrap2 and scrap3 is used for div_imm()
            next_translator = scraps[4]
            digit_scrap = scraps[5]  # used when src1 == src2
            if i >= 8:
                final_output = self.dst.get_cell(i - 8)
            else:
                final_output = scraps[6]
                # we don't need to save output of first 8 digits

            if not is_first:
                next_translator.move(final_output)

            # final_output <= 0x70

            for digit1_num in range(0, i + 1):
                digit2_num = i - digit1_num
                if digit1_num >= 8:
                    continue
                if digit2_num >= 8:
                    continue

                digit1 = Cell(src1.addr + digit1_num)
                digit2 = Cell(src2.addr + digit2_num)
                if digit1 == digit2:
                    digit2.copy(digit_scrap, scrap=scrap1)
                    digit2 = digit_scrap

                # Multiply digits
                with digit2.loop():
                    digit1.copy(output_scrap, scrap=digit1_cell_copy)
                    if digit2 != digit_scrap:
                        digit2_cell_copy.change(1)
                    digit2.change(-1)

                if digit2 != digit_scrap:
                    digit2_cell_copy.move(digit2)

                # output_scrap = digit1 * digit2
                # output_scrap <= 0xe1

                output_scrap.div_imm(16, scrap1, None if is_last else next_translator)
                # scr1 <= 0xf
                # next_translator <= 0xe
                # next_translator <= 0x62 (summary)
                if not is_first:
                    scrap1.move(final_output)
                else:
                    scrap1.clear()
                # final_output <= 0xe8

            if not is_first:
                final_output.div_imm(16, scrap1, None if is_last else next_translator)
                if i >= 8:
                    scrap1.move(final_output)
                else:
                    scrap1.clear()
                # next_translator <= 0x70

            concater.debug()

        if self.src1 == self.dst:
            src1.clear_big()


@dataclass
class ShiftLeft(Instruction):
    dst: Register
    src: Register
    shift: Register

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"shl {self.dst} {self.src} {self.shift}", comments)
        if self.dst == ZERO:
            return

        if self.src == ZERO:
            self.dst.clear_big()
            return

        shift_big = scraps[0]  # shift / 4
        shift_small = scraps[1]  # shift % 4
        shift_big_scrap = scraps[2]
        shift_scrap = scraps[3]
        shift_verybig_unused = mul_scrap = scraps[4]
        # scraps 3 and 4 are used for div_imm()

        self.shift.get_cell(0).div_imm(4, shift_small, shift_big)
        shift_big.copy(self.shift.get_cell(0), multiplier=4, scrap=shift_big_scrap)
        self.shift.get_cell(1).div_imm(2, shift_scrap, shift_verybig_unused)
        shift_verybig_unused.move(self.shift.get_cell(1), multiplier=2)
        shift_scrap.move(shift_big, self.shift.get_cell(1), multiplier=(4, 1))
        shift_big.copy(shift_big_scrap, scrap=shift_scrap)

        concater.debug()

        if self.src == self.dst:
            raise NotImplementedError

        for i in range(7, -1, -1):
            # custom ifnot
            shift_big_scrap.to()
            concater.raw(">+<[->-]>[>]<", pos_offset=1)
            #                 ^
            with shift_big_scrap.cell_rel(1).loop():
                shift_big_scrap.cell_rel(1).change(-1)

                small_dst = self.dst.get_cell(i)
                if self.src != self.dst:
                    small_src = self.src.get_cell(i)
                    small_dst.clear()
                    small_src.copy(small_dst, scrap=mul_scrap)

                with shift_small.loop():
                    small_dst.move(mul_scrap, multiplier=2)
                    mul_scrap.move(small_dst)
                    shift_scrap.change(1)
                    shift_small.change(-1)
                shift_scrap.move(shift_small)

        with shift_big.loop():
            self.dst.get_cell(7).clear()
            for i in range(6, -1, -1):
                small_src = self.dst.get_cell(i)
                small_dst = self.dst.get_cell(i + 1)
                small_src.move(small_dst)
            shift_big.change(-1)

        shift_big_scrap.to()
        concater.raw("!0")

        shift_small.move(self.shift.get_cell(0))
        shift_big.clear()
        self.dst.normalize_big()

        # TODO: save original register values


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
            mod.to()
            concater.raw(".")
            mod.clear()
        mod.change(10)  # Line feed
        concater.raw(".")
        mod.clear()


@dataclass
class Debug(Instruction):
    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem("dbg", comments)
        concater.debug()


MNEMONICS: dict[str, type[Instruction]] = dict()

MNEMONICS["li"] = LoadI
MNEMONICS["lui"] = LoadUpperI
MNEMONICS["add"] = Add
MNEMONICS["addi"] = AddI
MNEMONICS["sub"] = Sub
MNEMONICS["mul"] = Mul
MNEMONICS["mulhu"] = MulHighUnsigned
MNEMONICS["sll"] = ShiftLeft

# debug commands
MNEMONICS["out"] = Output
MNEMONICS["dbg"] = Debug


def is_block_boundary(self):
    return isinstance(
        self,
        (
            # LabelDefine,
            # JumpRelative,
            # JumpConditional,
            # Jump,
            # Call,
            # Return,
        ),
    )
