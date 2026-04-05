from instructions.baseInstructions import *
from dataclasses import dataclass


class Label(str): ...


@dataclass
class LabelDefine(Instruction):
    name: str


@dataclass
class Jump(Instruction):
    target: Label

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False, clear: bool = False):
        concater.rem(f"j {self.target}", comments)
        i, j = program.find_block(self.target)
        if clear:
            next1.clear()
        next1.change(i)
        if clear:
            next2.clear()
        next2.change(j)


@dataclass
class JumpRelative(Instruction):  # It isn't an instruction to use in your asm-code
    offset: Immediate

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False, clear: bool = False):
        concater.rem(f"jmr {self.offset}", comments)
        if self.offset != 1:
            raise NotImplementedError
        next_i, next_j = program.find_next_block(cur_block)
        if clear:
            next1.clear()
        next1.change(next_i)
        if clear:
            next2.clear()
        next2.change(next_j)


@dataclass
class BranchIfEqual(Instruction):
    src1: Register
    src2: Register
    label: Label

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"beq {self.src1} {self.src2} {self.label}", comments)
        if self.src1 == self.src2:
            Jump(self.label).evaluate(program, cur_block)
            return
        if self.src1 == ZERO:
            BranchIfEqualToZero(self.src2, self.label).evaluate(program, cur_block)
            return
        if self.src2 == ZERO:
            BranchIfEqualToZero(self.src1, self.label).evaluate(program, cur_block)
            return

        running = scraps[0]
        running.change(1)
        scrap = scraps[1]
        copy_scrap = scraps[2]
        for i in range(8):
            small_src1 = self.src1.get_cell(i)
            small_src2 = self.src2.get_cell(i)
            small_src1.copy(scrap, scrap=copy_scrap)
            small_src2.copy(scrap, scrap=copy_scrap, multiplier=-1)
            with scrap.loop():
                running.change(-1)
                JumpRelative(Immediate(1)).evaluate(program, cur_block)
                scrap.clear()
            running.raw("[")
        Jump(self.label).evaluate(program, cur_block)
        running.change(-1)
        running.raw("]]]]]]]]")


@dataclass
class BranchIfNotEqual(Instruction):
    src1: Register
    src2: Register
    label: Label

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"bne {self.src1} {self.src2} {self.label}", comments)
        if self.src1 == self.src2:
            JumpRelative(Immediate(1)).evaluate(program, cur_block)
            return
        if self.src1 == ZERO:
            BranchIfNotEqualToZero(self.src2, self.label).evaluate(program, cur_block)
            return
        if self.src2 == ZERO:
            BranchIfNotEqualToZero(self.src1, self.label).evaluate(program, cur_block)
            return

        running = scraps[0]
        running.change(1)
        scrap = scraps[1]
        copy_scrap = scraps[2]
        for i in range(8):
            small_src1 = self.src1.get_cell(i)
            small_src2 = self.src2.get_cell(i)
            small_src1.copy(scrap, scrap=copy_scrap)
            small_src2.copy(scrap, scrap=copy_scrap, multiplier=-1)
            with scrap.loop():
                running.change(-1)
                Jump(self.label).evaluate(program, cur_block)
                scrap.clear()
            running.raw("[")
        JumpRelative(Immediate(1)).evaluate(program, cur_block)
        running.change(-1)
        running.raw("]]]]]]]]")


@dataclass
class BranchIfLessThan(Instruction):
    src1: Register
    src2: Register
    label: Label

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"blt {self.src1} {self.src2} {self.label}", comments)
        if self.src1 == self.src2:
            JumpRelative(Immediate(1)).evaluate(program, cur_block)
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
                mod.move(self.src2.get_cell(7))
                self.src2.get_cell(7).change(8)
                sign.change(1)
                JumpRelative(Immediate(1)).evaluate(program, cur_block)
                with sign.loop():
                    sign.change(-1)
                    self.src2.get_cell(7).change(-8)
                    BranchIfNotEqualToZero(self.src2, self.label).evaluate(program, cur_block, jumped_relative=True)
            else:
                self.src2.get_cell(7).div_imm(8, mod, sign)
                mod.move(self.src2.get_cell(7))
                JumpRelative(Immediate(1)).evaluate(program, cur_block)
                with sign.loop():
                    sign.change(-1)
                    self.src2.get_cell(7).change(8)
                    Jump(self.label).evaluate(program, cur_block, clear=True)
            concater.debug()
            return

        mod = scraps[0]
        self.src1.get_cell(7).change(8)
        self.src1.get_cell(7).div_imm(16, mod, None)
        mod.move(self.src1.get_cell(7))
        self.src2.get_cell(7).change(8)
        self.src2.get_cell(7).div_imm(16, mod, None)
        mod.move(self.src2.get_cell(7))

        BranchIfLessThanUnsigned(self.src1, self.src2, self.label).evaluate(program, cur_block)

        self.src1.get_cell(7).change(8)
        self.src1.get_cell(7).div_imm(16, mod, None)
        mod.move(self.src1.get_cell(7))
        self.src2.get_cell(7).change(8)
        self.src2.get_cell(7).div_imm(16, mod, None)
        mod.move(self.src2.get_cell(7))


@dataclass
class BranchIfLessThanUnsigned(Instruction):
    src1: Register
    src2: Register
    label: Label

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"bltu {self.src1} {self.src2} {self.label}", comments)
        if self.src1 == self.src2 or self.src2 == ZERO:
            JumpRelative(Immediate(1)).evaluate(program, cur_block)
            return
        if self.src1 == ZERO:
            BranchIfNotEqualToZero(self.src2, self.label).evaluate(program, cur_block)
            return

        running = scraps[0]
        running.change(1)
        JumpRelative(Immediate(1)).evaluate(program, cur_block)
        for i in range(7, -1, -1):
            small_src1 = self.src1.get_cell(i)
            small_src2 = self.src2.get_cell(i)
            scrap_src1 = scraps[1]
            scrap_src2 = scraps[2]

            small_src1.move(scrap_src1)
            small_src2.move(scrap_src2)

            with scrap_src1.loop():
                with scrap_src2.ifnot():  # >
                    running.change(-1)
                    scrap_src1.move(small_src1)
                    scrap_src1.change(1)
                    small_src1.change(-1)
                    small_src2.change(-1)
                    scrap_src2.change(1)
                scrap_src2.change(-1)
                small_src2.change(1)
                small_src1.change(1)
                scrap_src1.change(-1)
            with scrap_src2.loop():  # <
                running.change(-1)
                Jump(self.label).evaluate(program, cur_block, clear=True)
                scrap_src2.move(small_src2)
            running.raw("[")
        running.change(-1)
        running.raw("]]]]]]]]")


@dataclass
class BranchIfEqualToZero(Instruction):
    src: Register
    label: Label

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"beqz {self.src} {self.label}", comments)
        if self.src == ZERO:
            Jump(self.label).evaluate(program, cur_block)
            return

        running = scraps[0]
        running.change(1)
        for i in range(8):
            small_src = self.src.get_cell(i)
            scrap_src = scraps[1]
            with small_src.loop():
                running.change(-1)
                JumpRelative(Immediate(1)).evaluate(program, cur_block)
                small_src.move(scrap_src)
            scrap_src.move(small_src)
            running.raw("[")
        Jump(self.label).evaluate(program, cur_block)
        running.change(-1)
        running.raw("]]]]]]]]")
        concater.debug()


@dataclass
class BranchIfNotEqualToZero(Instruction):
    src: Register
    label: Label

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False, jumped_relative: bool = False):
        concater.rem(f"bnez {self.src} {self.label}", comments)
        if self.src == ZERO:
            if not jumped_relative:
                JumpRelative(Immediate(1)).evaluate(program, cur_block)
            return

        running = scraps[0]
        running.change(1)
        for i in range(8):
            small_src = self.src.get_cell(i)
            scrap_src = scraps[1]
            with small_src.loop():
                running.change(-1)
                Jump(self.label).evaluate(program, cur_block, clear=jumped_relative)
                small_src.move(scrap_src)
            scrap_src.move(small_src)
            running.raw("[")
        if not jumped_relative:
            JumpRelative(Immediate(1)).evaluate(program, cur_block)
        running.change(-1)
        running.raw("]]]]]]]]")


def is_block_boundary(self):
    return isinstance(
        self,
        (
            LabelDefine,
            Jump,
            BranchIfEqual,
            BranchIfNotEqual,
            BranchIfLessThan,
            BranchIfLessThanUnsigned,
            BranchIfEqualToZero,
            BranchIfNotEqualToZero,
        ),
    )
