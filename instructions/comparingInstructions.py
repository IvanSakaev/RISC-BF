from instructions.baseInstructions import *
from dataclasses import dataclass


@dataclass
class SetLessThan(Instruction):
    dst: Register
    src1: Register
    src2: Register

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"slt {self.dst} {self.src1} {self.src2}", comments)
        if self.dst == ZERO:
            return
        if self.src1 == self.src2:
            self.dst.clear_big()
            return
        invert = False

        if self.src2 == ZERO:
            self.src2 = self.src1
            self.src1 = ZERO
            invert = True
        if self.src1 == ZERO:
            sign = scraps[0]
            mod = scraps[1]
            if not invert:
                self.src2.get_cell(7).div_imm(8, mod, sign, invert_output=True)
                if self.src2 == self.dst:
                    mod.clear()
                else:
                    mod.move(self.src2.get_cell(7))
                output = scraps[1]
                if self.src2 != self.dst:
                    self.src2.get_cell(7).change(8)
                sign.change(1)
                with sign.loop():
                    sign.change(-1)
                    if self.src2 != self.dst:
                        self.src2.get_cell(7).change(-8)
                    SetNotEqualToZero(self.dst, self.src2).evaluate(
                        program, cur_block, move_to_dst=False
                    )
                self.dst.clear_big()
                output.move(self.dst.get_cell(0))
            else:
                self.src2.get_cell(7).div_imm(8, mod, sign)
                if self.src2 == self.dst:
                    mod.clear()
                    self.dst.clear_big()
                    sign.move(self.dst.get_cell(0))
                else:
                    mod.move(self.src2.get_cell(7))
                    self.dst.clear_big()
                    sign.move(
                        self.dst.get_cell(0), self.src2.get_cell(7), multiplier=[1, 8]
                    )
            return

        mod = scraps[0]
        self.src1.get_cell(7).change(8)
        self.src1.get_cell(7).div_imm(16, mod, None)
        mod.move(self.src1.get_cell(7))
        self.src2.get_cell(7).change(8)
        self.src2.get_cell(7).div_imm(16, mod, None)
        mod.move(self.src2.get_cell(7))

        SetLessThanUnsigned(self.dst, self.src1, self.src2).evaluate(program, cur_block)

        if self.src1 != self.dst:
            self.src1.get_cell(7).change(8)
            self.src1.get_cell(7).div_imm(16, mod, None)
            mod.move(self.src1.get_cell(7))
        if self.src2 != self.dst:
            self.src2.get_cell(7).change(8)
            self.src2.get_cell(7).div_imm(16, mod, None)
            mod.move(self.src2.get_cell(7))


@dataclass
class SetLessThanI(Instruction):
    dst: Register
    src1: Register
    src2: Immediate

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):  # TODO: optimize?
        concater.rem(f"slti {self.dst} {self.src1} {self.src2}", comments)
        if self.dst == ZERO:
            return
        src2_reg = Register(scraps[6])
        src2_reg.change_big(self.src2)
        SetLessThan(self.dst, self.src1, src2_reg).evaluate(program, cur_block)
        src2_reg.clear_big()


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
            SetNotEqualToZero(self.dst, self.src2).evaluate(program, cur_block)
            return
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

            running.raw("[")
        running.change(-1)
        running.raw("]]]]]]]]")
        self.dst.clear_big()
        output_value.move(self.dst.get_cell(0))


@dataclass
class SetEqualToZero(Instruction):
    dst: Register
    src: Register

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"seqz {self.dst} {self.src}", comments)
        if self.dst == ZERO:
            return
        if self.src == ZERO:
            self.dst.change_big(1, clear=True)
            return

        running = scraps[0]
        running.change(1)
        output = scraps[1]
        for i in range(8):
            small_src = self.src.get_cell(i)
            scrap_src = scraps[2]
            with small_src.loop():
                running.change(-1)
                if self.src == self.dst:
                    small_src.clear()
                else:
                    small_src.move(scrap_src)
            if self.src != self.dst:
                scrap_src.move(small_src)
            running.raw("[")
        output.change(1)
        running.change(-1)
        running.raw("]]]]]]]]")

        self.dst.clear_big()
        output.move(self.dst.get_cell(0))


@dataclass
class SetNotEqualToZero(Instruction):
    dst: Register
    src: Register

    def evaluate(
            self,
            program: Program,
            cur_block: Block,
            comments: bool = False,
            move_to_dst: bool = True,
    ):
        concater.rem(f"snez {self.dst} {self.src}", comments)
        if self.dst == ZERO:
            return
        if self.src == ZERO:
            self.dst.clear_big()
            return
        running = scraps[0]
        running.change(1)
        output = scraps[1]
        for i in range(8):
            small_src = self.src.get_cell(i)
            scrap_src = scraps[2]
            with small_src.loop():
                running.change(-1)
                output.change(1)
                small_src.move(scrap_src)
            scrap_src.move(small_src)
            running.raw("[")
        running.change(-1)
        running.raw("]]]]]]]]")

        if move_to_dst:
            self.dst.clear_big()
            output.move(self.dst.get_cell(0))


@dataclass
class SetLessThanZero(Instruction):
    dst: Register
    src: Register

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"sltz {self.dst} {self.src}", comments)
        SetLessThan(self.dst, self.src, ZERO).evaluate(program, cur_block)


@dataclass
class SetGreaterThanZero(Instruction):
    dst: Register
    src: Register

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"sgtz {self.dst} {self.src}", comments)
        SetLessThan(self.dst, ZERO, self.src).evaluate(program, cur_block)
