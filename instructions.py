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
class Move(Instruction):
    dst: Register
    src: Register

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"mv {self.dst} {self.src}", comments)
        AddI(self.dst, self.src, Immediate(0)).evaluate(program, cur_block, False)


@dataclass
class Neg(Instruction):
    dst: Register
    src: Register

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"neg {self.dst} {self.src}", comments)
        Sub(self.dst, ZERO, self.src).evaluate(program, cur_block, False)


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
            Not.invert_big(self.dst, self.dst, clear=True)
            self.dst.change_big(1)
            self.dst.normalize_big_fast()
        elif self.src1 == ZERO:
            self.dst.clear_big()
            Not.invert_big(self.src2, self.dst, clear=True)
            self.dst.change_big(1)
            self.dst.normalize_big_fast()
        elif self.src1 == self.dst:
            self.dst.clear_big()
            Not.invert_big(self.src2, self.dst, clear=False)
            self.dst.change_big(1)
            self.dst.normalize_big()
        elif self.src2 == ZERO:
            self.dst.clear_big()
            self.src1.copy_big(self.dst)
        elif self.src2 == self.dst:
            Not.invert_big(self.dst, self.dst, clear=True)
            self.dst.change_big(1)
            self.src1.copy_big(self.dst)
            self.dst.normalize_big()
        else:
            self.dst.clear_big()
            self.src1.copy_big(self.dst)
            Not.invert_big(self.src2, self.dst, clear=False)
            self.dst.change_big(1)
            self.dst.normalize_big()


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
        concater.rem(f"sll {self.dst} {self.src} {self.shift}", comments)
        if self.dst == ZERO:
            return

        if self.src == ZERO:
            self.dst.clear_big()
            return

        if self.shift == ZERO:
            if self.src != self.dst:
                self.dst.clear_big()
                self.src.copy_big(self.dst)
                return

        if self.src == self.shift:
            raise NotImplementedError

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

        if self.dst != self.shift:
            shift_small.move(self.shift.get_cell(0))
        else:
            shift_small.clear()
        shift_big.clear()
        self.dst.normalize_big()


@dataclass
class ShiftLeftI(Instruction):
    dst: Register
    src: Register
    shift: Immediate

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"slli {self.dst} {self.src} {self.shift}", comments)
        if self.dst == ZERO:
            return

        if self.src == ZERO:
            self.dst.clear_big()
            return

        small_shift = self.shift % 4
        big_shift = (self.shift // 4) % 8

        for i in range(7 - big_shift, -1, -1):
            small_src = self.src.get_cell(i)
            small_dst = self.dst.get_cell(i + big_shift)
            if small_src != small_dst:
                small_dst.clear()
                if self.src == self.dst:
                    small_src.move(small_dst, multiplier=(2**small_shift))
                else:
                    small_src.copy(small_dst, multiplier=(2**small_shift))
            elif small_shift != 0:
                small_dst.move(scraps[0])
                scraps[0].move(small_dst, multiplier=(2**small_shift))

        if small_shift != 0:
            # normalize only changed digits
            mod = scraps[0]  # 2 scraps after MOD are used too in div_imm()
            output = scraps[3]
            for i in range(big_shift, 8):
                small = self.dst.get_cell(i)
                need_output = i < 7
                if need_output:
                    small.div_imm(16, mod, output)
                else:
                    small.div_imm(16, mod, output=None)
                mod.move(small)
                if need_output:
                    small2 = small.cell_rel(1)
                    output.move(small2)

        # set small digits to zero
        for i in range(big_shift):
            small_dst = self.dst.get_cell(i)
            small_dst.clear()


@dataclass
class Or(Instruction):
    dst: Register
    src1: Register
    src2: Register

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"or {self.dst}, {self.src1}, {self.src2}", comments)
        if self.dst == ZERO:
            return
        if self.src1 == ZERO and self.src2 == ZERO:
            self.dst.clear_big()
            return
        if self.src1 == ZERO:
            if self.src2 != self.dst:
                self.dst.clear_big()
                self.src2.copy_big(self.dst)
            return
        if self.src2 == ZERO:
            if self.src1 != self.dst:
                self.dst.clear_big()
                self.src1.copy_big(self.dst)
            return
        if self.src1 == self.src2:
            self.dst.clear_big()
            self.src1.copy_big(self.dst)
            return

        if self.src2 == self.dst:
            self.src2 = self.src1
            self.src1 = self.dst

        mod = scraps[0]
        div_output = scraps[3]
        src1_scrap = scraps[4]
        src2_scrap = scraps[5]
        output = scraps[6]

        for i in range(8):
            src1_small = self.src1.get_cell(i)
            src2_small = self.src2.get_cell(i)
            dst_small = self.dst.get_cell(i)
            if self.src1 != self.dst:
                dst_small.clear()
            for j in range(4):
                # Move first bit to output
                if j == 3:
                    if self.src1 != self.dst:
                        src1_small.move(src1_scrap, output, multiplier=[2**j, 1])
                    else:
                        src1_small.move(output)
                else:
                    src1_small.div_imm(2, mod, div_output)
                    div_output.move(src1_small)
                    if self.src1 != self.dst:
                        mod.move(src1_scrap, output, multiplier=[2**j, 1])
                    else:
                        mod.move(output)

                # Move second bit to output
                if j == 3:
                    with src2_small.loop():
                        src2_scrap.change(2**3)
                        output.clear()
                        output.change(1)
                        src2_small.change(-1)
                else:
                    src2_small.div_imm(2, mod, div_output)
                    div_output.move(src2_small)
                    with mod.loop():
                        src2_scrap.change(2**j)
                        output.clear()
                        output.change(1)
                        mod.change(-1)

                if self.src1 != self.dst:
                    output.move(dst_small, multiplier=2**j)
                else:
                    output.move(src1_scrap, multiplier=2**j)
            # Restoring value
            src1_scrap.move(src1_small)
            src2_scrap.move(src2_small)


@dataclass
class And(Instruction):
    dst: Register
    src1: Register
    src2: Register

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"and {self.dst}, {self.src1}, {self.src2}", comments)
        if self.dst == ZERO:
            return
        if self.src1 == ZERO or self.src2 == ZERO:
            self.dst.clear_big()
            return
        if self.src1 == self.src2:
            self.dst.clear_big()
            self.src1.copy_big(self.dst)
            return

        if self.src2 == self.dst:
            self.src2 = self.src1
            self.src1 = self.dst

        mod = scraps[0]
        div_output = scraps[3]
        src1_scrap = scraps[4]
        src2_scrap = scraps[5]
        output = scraps[6]

        for i in range(8):
            src1_small = self.src1.get_cell(i)
            src2_small = self.src2.get_cell(i)
            if self.src1 != self.dst:
                dst_small = self.dst.get_cell(i)
                dst_small.clear()
            else:
                dst_small = src1_scrap
            for j in range(4):
                # Move first bit to output
                if j == 3:
                    if self.src1 != self.dst:
                        src1_small.move(src1_scrap, output, multiplier=[2**j, 1])
                    else:
                        src1_small.move(output)
                else:
                    src1_small.div_imm(2, mod, div_output)
                    div_output.move(src1_small)
                    if self.src1 != self.dst:
                        mod.move(src1_scrap, output, multiplier=[2**j, 1])
                    else:
                        mod.move(output)

                # Move second bit to output
                if j == 3:
                    with src2_small.loop():
                        src2_scrap.change(2**3)
                        with output.loop():
                            dst_small.change(2**j)
                            output.change(-1)
                        src2_small.change(-1)
                else:
                    src2_small.div_imm(2, mod, div_output)
                    div_output.move(src2_small)
                    with mod.loop():
                        src2_scrap.change(2**j)
                        with output.loop():
                            dst_small.change(2**j)
                            output.change(-1)
                        mod.change(-1)
                output.clear()

            # Restoring value
            src1_scrap.move(src1_small)
            src2_scrap.move(src2_small)


@dataclass
class Xor(Instruction):
    dst: Register
    src1: Register
    src2: Register

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"xor {self.dst}, {self.src1}, {self.src2}", comments)
        if self.dst == ZERO:
            return
        if self.src1 == self.src2:
            self.dst.clear_big()
            return
        if self.src1 == ZERO:
            if self.src2 != self.dst:
                self.dst.clear_big()
                self.src2.copy_big(self.dst)
            return
        if self.src2 == ZERO:
            if self.src1 != self.dst:
                self.dst.clear_big()
                self.src1.copy_big(self.dst)
            return

        if self.src2 == self.dst:
            self.src2 = self.src1
            self.src1 = self.dst

        mod = scraps[0]
        div_output = scraps[3]
        src1_scrap = scraps[4]
        src2_scrap = scraps[5]
        output = scraps[6]

        for i in range(8):
            src1_small = self.src1.get_cell(i)
            src2_small = self.src2.get_cell(i)
            if self.src1 != self.dst:
                dst_small = self.dst.get_cell(i)
                dst_small.clear()
            else:
                dst_small = src1_scrap
            for j in range(4):
                # Move first bit to output
                if j == 3:
                    if self.src1 != self.dst:
                        src1_small.move(src1_scrap, output, multiplier=[2**j, 1])
                    else:
                        src1_small.move(output)
                else:
                    src1_small.div_imm(2, mod, div_output)
                    div_output.move(src1_small)
                    if self.src1 != self.dst:
                        mod.move(src1_scrap, output, multiplier=[2**j, 1])
                    else:
                        mod.move(output)

                # Move second bit to output
                if j == 3:
                    src2_small.move(src2_scrap, output, multiplier=[2**j, -1])
                else:
                    src2_small.div_imm(2, mod, div_output)
                    div_output.move(src2_small)
                    mod.move(src2_scrap, output, multiplier=[2**j, -1])

                with output.loop():
                    if self.src1 != self.dst:
                        dst_small.change(2**j)
                    else:
                        src1_scrap.change(2**j)
                    output.clear()

            # Restoring value
            src1_scrap.move(src1_small)
            src2_scrap.move(src2_small)


@dataclass
class Not(Instruction):
    dst: Register
    src: Register

    def evaluate(self, program, cur_block, comments=False):
        if self.dst == ZERO:
            return
        if self.src == ZERO:
            self.dst.change_big(2**32 - 1, clear=True)
            return
        self.invert_big(self.src, self.dst)

    @classmethod
    def invert_big(cls, src: Register, dst: Register, clear: bool = True):
        scrap = scraps[0]
        for i in range(8):
            small_src = src.get_cell(i)
            small_dst = dst.get_cell(i)
            if src != dst:
                if clear:
                    small_dst.clear()
                small_dst.change(15)
                small_src.move(scrap)
                scrap.move(small_src, small_dst, multiplier=[1, -1])
            else:
                small_src.move(scrap)
                small_src.change(15)
                scrap.move(small_src, multiplier=-1)


@dataclass
class OrI(Instruction):
    dst: Register
    src1: Register
    src2: Immediate

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"ori {self.dst}, {self.src1}, {self.src2}", comments)
        if self.dst == ZERO:
            return
        if self.src1 == ZERO:
            self.dst.change_big(self.src2, clear=True)
            return

        mod = scraps[0]
        div_output = scraps[3]
        src1_scrap = scraps[4]
        output = scraps[5]

        for i in range(8):
            src1_small = self.src1.get_cell(i)
            dst_small = self.dst.get_cell(i)
            if self.src1 != self.dst:
                dst_small.clear()
            src2_small = self.src2 // 2 ** (i * 4)
            src2_small %= 2**4
            if src2_small == 0:
                if self.src1 != self.dst:
                    src1_small.copy(dst_small, scrap=src1_scrap)
            elif src2_small == 15:
                dst_small.clear()
                dst_small.change(15)
            else:
                for j in range(4):
                    need_value = (src2_small & (2**j)) == 0

                    # Move first bit to output
                    if j == 3:
                        if need_value:
                            if self.src1 != self.dst:
                                src1_small.move(
                                    src1_scrap, output, multiplier=[2**j, 1]
                                )
                            else:
                                src1_small.move(output)
                        else:
                            if self.src1 != self.dst:
                                src1_small.move(src1_scrap, multiplier=2**j)
                            else:
                                src1_small.clear()
                    else:
                        src1_small.div_imm(2, mod, div_output)
                        div_output.move(src1_small)
                        if need_value:
                            if self.src1 != self.dst:
                                mod.move(src1_scrap, output, multiplier=[2**j, 1])
                            else:
                                mod.move(output)
                        else:
                            if self.src1 != self.dst:
                                mod.move(src1_scrap, multiplier=2**j)
                            else:
                                mod.clear()

                    if need_value:
                        if self.src1 != self.dst:
                            output.move(dst_small, multiplier=2**j)
                        else:
                            output.move(src1_scrap, multiplier=2**j)
                    else:
                        if self.src1 != self.dst:
                            dst_small.change(2**j)
                        else:
                            src1_scrap.change(2**j)
                # Restoring value
                src1_scrap.move(src1_small)


@dataclass
class AndI(Instruction):
    dst: Register
    src1: Register
    src2: Immediate

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"andi {self.dst}, {self.src1}, {self.src2}", comments)
        if self.dst == ZERO:
            return
        if self.src1 == ZERO:
            self.dst.clear_big()
            return

        mod = scraps[0]
        div_output = scraps[3]
        src1_scrap = scraps[4]
        output = scraps[5]

        for i in range(8):
            src1_small = self.src1.get_cell(i)
            dst_small = self.dst.get_cell(i)
            if self.src1 != self.dst:
                dst_small.clear()
            src2_small = self.src2 // 2 ** (i * 4)
            src2_small %= 2**4
            if src2_small == 0:
                dst_small.clear()
            elif src2_small == 15:
                if self.src1 != self.dst:
                    src1_small.copy(dst_small, scrap=src1_scrap)
            else:
                for j in range(4):
                    need_value = (src2_small & (2**j)) > 0

                    # Move first bit to output
                    if j == 3:
                        if need_value:
                            if self.src1 != self.dst:
                                src1_small.move(
                                    src1_scrap, output, multiplier=[2**j, 1]
                                )
                            else:
                                src1_small.move(output)
                        else:
                            if self.src1 != self.dst:
                                src1_small.move(src1_scrap, multiplier=2**j)
                            else:
                                src1_small.clear()
                    else:
                        src1_small.div_imm(2, mod, div_output)
                        div_output.move(src1_small)
                        if need_value:
                            if self.src1 != self.dst:
                                mod.move(src1_scrap, output, multiplier=[2**j, 1])
                            else:
                                mod.move(output)
                        else:
                            if self.src1 != self.dst:
                                mod.move(src1_scrap, multiplier=2**j)
                            else:
                                mod.clear()

                    if need_value:
                        if self.src1 != self.dst:
                            output.move(dst_small, multiplier=2**j)
                        else:
                            output.move(src1_scrap, multiplier=2**j)
                # Restoring value
                src1_scrap.move(src1_small)


@dataclass
class XorI(Instruction):
    dst: Register
    src1: Register
    src2: Immediate

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"xori {self.dst}, {self.src1}, {self.src2}", comments)
        if self.dst == ZERO:
            return
        if self.src1 == ZERO:
            self.dst.change_big(self.src2, clear=True)
            return

        mod = scraps[0]
        div_output = scraps[3]
        src1_scrap = scraps[4]
        output = scraps[5]

        for i in range(8):
            src1_small = self.src1.get_cell(i)
            dst_small = self.dst.get_cell(i)
            if self.src1 != self.dst:
                dst_small.clear()
            src2_small = self.src2 // 2 ** (i * 4)
            src2_small %= 2**4
            if src2_small == 0:
                if self.src1 != self.dst:
                    src1_small.copy(dst_small, scrap=src1_scrap)
            elif src2_small == 15:
                dst_small.change(15)
                if self.src1 != self.dst:
                    src1_small.copy(dst_small, scrap=src1_scrap, multiplier=-1)
            else:
                for j in range(4):
                    invert = (src2_small & (2**j)) > 0

                    # Move first bit to output
                    if j == 3:
                        if self.src1 != self.dst:
                            src1_small.move(
                                src1_scrap,
                                output,
                                multiplier=[2**j, -1 if invert else 1],
                            )
                        else:
                            src1_small.move(output, multiplier=(-1 if invert else 1))
                    else:
                        src1_small.div_imm(2, mod, div_output)
                        div_output.move(src1_small)
                        if self.src1 != self.dst:
                            mod.move(
                                src1_scrap,
                                output,
                                multiplier=[2**j, -1 if invert else 1],
                            )
                        else:
                            mod.move(output, multiplier=(-1 if invert else 1))

                    if invert:
                        output.change(1)
                    if self.src1 != self.dst:
                        output.move(dst_small, multiplier=2**j)
                    else:
                        output.move(src1_scrap, multiplier=2**j)
                # Restoring value
                src1_scrap.move(src1_small)


@dataclass
class SetLessThanUnsigned(Instruction):
    dst: Register
    src1: Register
    src2: Register

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"sltu {self.dst} {self.src1} {self.src2}", comments)
        if self.dst == ZERO:
            return
        if self.src1 == self.src2:
            self.dst.clear_big()
            return
        if self.src1 == ZERO:
            raise NotImplementedError
        if self.src2 == ZERO:
            self.dst.clear_big()
            return
        
        invert = False
        if self.src2 == self.dst:
            self.src2 = self.src1
            self.src1 = self.dst
            invert = True

        running = scraps[0]
        running.change(1)
        output_value = scraps[1]
        if invert:
            output_value.change(1)
        for i in range(7, -1, -1):
            small_src1 = self.src1.get_cell(i)
            small_src2 = self.src2.get_cell(i)
            if self.src1 == self.dst:
               scrap_src1 = small_src1
               scrap_src2 = scraps[2]
               small_src2.move(scrap_src2) 
            else:
                scrap_src1 = scraps[2]
                scrap_src2 = scraps[3]
                small_src1.move(scrap_src1)
                small_src2.move(scrap_src2)

            with scrap_src1.loop():
                with scrap_src2.ifnot():  # >
                    running.change(-1)
                    if self.src1 == self.dst:
                        scrap_src1.clear()
                    else:
                        scrap_src1.move(small_src1)
                    scrap_src1.change(1)
                    if self.src1 != self.dst:
                        small_src1.change(-1)
                    small_src2.change(-1)
                    scrap_src2.change(1)
                small_src2.change(1)
                if self.src1 != self.dst:
                    small_src1.change(1)
                scrap_src2.change(-1)
                scrap_src1.change(-1)
            with scrap_src2.loop():  # <
                running.change(-1)
                output_value.change(-1 if invert else 1)
                scrap_src2.move(small_src2)

            running.to()
            concater.raw("[")
        running.change(-1)
        concater.raw("]]]]]]]]")
        self.dst.clear_big()
        output_value.move(self.dst.get_cell(0))


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
MNEMONICS["mv"] = Move
MNEMONICS["neg"] = Neg
MNEMONICS["add"] = Add
MNEMONICS["addi"] = AddI
MNEMONICS["sub"] = Sub
MNEMONICS["mul"] = Mul
MNEMONICS["mulhu"] = MulHighUnsigned
MNEMONICS["sll"] = ShiftLeft
MNEMONICS["slli"] = ShiftLeftI
MNEMONICS["or"] = Or
MNEMONICS["and"] = And
MNEMONICS["xor"] = Xor
MNEMONICS["not"] = Not
MNEMONICS["ori"] = OrI
MNEMONICS["andi"] = AndI
MNEMONICS["xori"] = XorI
MNEMONICS["sltu"] = SetLessThanUnsigned

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
