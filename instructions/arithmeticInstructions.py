from instructions.baseInstructions import *
from instructions.bitwiseInstructions import Not
from dataclasses import dataclass


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
            self.src2 = Immediate(2 ** 32 + self.src2)

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
class Neg(Instruction):
    dst: Register
    src: Register

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"neg {self.dst} {self.src}", comments)
        Sub(self.dst, ZERO, self.src).evaluate(program, cur_block, False)


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

        if self.src1 == self.dst:
            src1.clear_big()
