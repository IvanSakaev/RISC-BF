from config import BLOCK_SIZE
from instructions.baseInstructions import *
from dataclasses import dataclass

from registers import regs


@dataclass
class Label(str):
    name: str


@dataclass
class LabelDefine(Instruction):
    name: str


@dataclass
class Jump(Instruction):
    target: Label

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False, clear: bool = False):
        concater.rem(f"j {self.target}", comments)
        new_nexts = program.find_block(self.target.name)
        for next_, new_next in zip(nexts, new_nexts):
            if clear:
                next_.clear()
            next_.change(new_next)


@dataclass
class JumpRelative(Instruction):  # It isn't an instruction to use in your asm-code
    offset: Immediate

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False, clear: bool = False):
        # TODO: maybe modify current block address instead of next block address?
        concater.rem(f"jmr {self.offset}", comments)
        if self.offset != 1:
            raise NotImplementedError
        new_nexts = program.find_next_block(cur_block)
        for next_, new_next in zip(nexts, new_nexts):
            if clear:
                next_.clear()
            next_.change(new_next)


@dataclass
class JumpRegister(Instruction):
    reg: Register

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"jr {self.reg}", comments)
        if self.reg == ZERO:
            new_nexts = [1, 0, 0, 0]
            for next_, new_next in zip(nexts, new_nexts):
                next_.change(new_next)
            return
        for i in range(8):
            small_reg = self.reg.get_cell(i)
            small_reg.copy(nexts[i // 2], multiplier=16 ** (i % 2))


@dataclass
class Ret(Instruction):
    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem("ret", comments)
        JumpRegister(regs["ra"]).evaluate(program, cur_block)


@dataclass
class JumpAndLink(Instruction):
    src: Register
    label: Label  # TODO: add parsing immediate values

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"jal {self.src} {self.label}", comments)
        if self.src != ZERO:
            new_nexts = program.find_next_block(cur_block)
            new_next_num = 0
            for i, new_next in enumerate(new_nexts):
                new_next_num += new_next * (BLOCK_SIZE ** i)
            self.src.change_big(new_next_num, clear=True)
        Jump(self.label).evaluate(program, cur_block)


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

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False, invert_output: bool = False):
        concater.rem(f"blt {self.src1} {self.src2} {self.label}", comments)
        if self.src1 == self.src2:
            if not invert_output:
                JumpRelative(Immediate(1)).evaluate(program, cur_block)
            else:
                Jump(self.label).evaluate(program, cur_block)
            return
        pos_inverted = False

        if self.src2 == ZERO:
            self.src2 = self.src1
            self.src1 = ZERO
            pos_inverted = True
        if self.src1 == ZERO:
            sign = scraps[0]
            mod = scraps[1]
            if not pos_inverted:
                self.src2.get_cell(7).div_imm(8, mod, sign, invert_output=True)
                mod.move(self.src2.get_cell(7))
                self.src2.get_cell(7).change(8)
                sign.change(1)
                if not invert_output:
                    JumpRelative(Immediate(1)).evaluate(program, cur_block)
                else:
                    Jump(self.label).evaluate(program, cur_block)
                with sign.loop():
                    sign.change(-1)
                    self.src2.get_cell(7).change(-8)
                    if not invert_output:
                        BranchIfNotEqualToZero(self.src2, self.label).evaluate(program, cur_block, jumped_relative=True)
                    else:
                        BranchIfEqualToZero(self.src2, self.label).evaluate(program, cur_block, jumped_absolute=True)
            else:
                self.src2.get_cell(7).div_imm(8, mod, sign)
                mod.move(self.src2.get_cell(7))
                if not invert_output:
                    JumpRelative(Immediate(1)).evaluate(program, cur_block)
                else:
                    Jump(self.label).evaluate(program, cur_block)
                with sign.loop():
                    sign.change(-1)
                    self.src2.get_cell(7).change(8)
                    if not invert_output:
                        Jump(self.label).evaluate(program, cur_block, clear=True)
                    else:
                        JumpRelative(Immediate(1)).evaluate(program, cur_block, clear=True)
            return

        mod = scraps[0]
        self.src1.get_cell(7).change(8)
        self.src1.get_cell(7).div_imm(16, mod, None)
        mod.move(self.src1.get_cell(7))
        self.src2.get_cell(7).change(8)
        self.src2.get_cell(7).div_imm(16, mod, None)
        mod.move(self.src2.get_cell(7))

        BranchIfLessThanUnsigned(self.src1, self.src2, self.label).evaluate(program, cur_block,
                                                                            invert_output=invert_output)

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

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False, invert_output: bool = False):
        concater.rem(f"bltu {self.src1} {self.src2} {self.label}", comments)
        if self.src1 == self.src2 or self.src2 == ZERO:
            if not invert_output:
                JumpRelative(Immediate(1)).evaluate(program, cur_block)
            else:
                Jump(self.label).evaluate(program, cur_block)
            return
        if self.src1 == ZERO:
            if not invert_output:
                BranchIfNotEqualToZero(self.src2, self.label).evaluate(program, cur_block)
            else:
                BranchIfEqualToZero(self.src2, self.label).evaluate(program, cur_block)
            return

        running = scraps[0]
        running.change(1)
        if not invert_output:
            JumpRelative(Immediate(1)).evaluate(program, cur_block)
        else:
            Jump(self.label).evaluate(program, cur_block)
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
                if not invert_output:
                    Jump(self.label).evaluate(program, cur_block, clear=True)
                else:
                    JumpRelative(Immediate(1)).evaluate(program, cur_block, clear=True)
                scrap_src2.move(small_src2)
            running.raw("[")
        running.change(-1)
        running.raw("]]]]]]]]")


@dataclass
class BranchIfGreaterThanOrEqual(Instruction):
    src1: Register
    src2: Register
    label: Label

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"bge {self.src1} {self.src2} {self.label}", comments)
        BranchIfLessThan(self.src1, self.src2, self.label).evaluate(program, cur_block, invert_output=True)


@dataclass
class BranchIfGreaterThanOrEqualUnsigned(Instruction):
    src1: Register
    src2: Register
    label: Label

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"bgeu {self.src1} {self.src2} {self.label}", comments)
        BranchIfLessThanUnsigned(self.src1, self.src2, self.label).evaluate(program, cur_block, invert_output=True)


@dataclass
class BranchIfEqualToZero(Instruction):
    src: Register
    label: Label

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False, jumped_absolute: bool = False):
        concater.rem(f"beqz {self.src} {self.label}", comments)
        if self.src == ZERO:
            if not jumped_absolute:
                Jump(self.label).evaluate(program, cur_block)
            return

        running = scraps[0]
        running.change(1)
        for i in range(8):
            small_src = self.src.get_cell(i)
            scrap_src = scraps[1]
            with small_src.loop():
                running.change(-1)
                JumpRelative(Immediate(1)).evaluate(program, cur_block, clear=jumped_absolute)
                small_src.move(scrap_src)
            scrap_src.move(small_src)
            running.raw("[")
        if not jumped_absolute:
            Jump(self.label).evaluate(program, cur_block)
        running.change(-1)
        running.raw("]]]]]]]]")


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


@dataclass
class BranchIfLessThanOrEqualToZero(Instruction):
    src: Register
    label: Label

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"blez {self.src} {self.label}", comments)
        BranchIfGreaterThanOrEqual(ZERO, self.src, self.label).evaluate(program, cur_block)


@dataclass
class BranchIfGreaterThanOrEqualToZero(Instruction):
    src: Register
    label: Label

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"bgez {self.src} {self.label}", comments)
        BranchIfGreaterThanOrEqual(self.src, ZERO, self.label).evaluate(program, cur_block)


@dataclass
class BranchIfLessThanZero(Instruction):
    src: Register
    label: Label

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"bltz {self.src} {self.label}", comments)
        BranchIfLessThan(self.src, ZERO, self.label).evaluate(program, cur_block)


@dataclass
class BranchIfGreaterThanZero(Instruction):
    src: Register
    label: Label

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"bgtz {self.src} {self.label}", comments)
        BranchIfLessThan(ZERO, self.src, self.label).evaluate(program, cur_block)


@dataclass
class BranchIfGreaterThan(Instruction):
    src1: Register
    src2: Register
    label: Label

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"bgt {self.src1} {self.src2} {self.label}", comments)
        BranchIfLessThan(self.src2, self.src1, self.label).evaluate(program, cur_block)


@dataclass
class BranchIfLessThanOrEqual(Instruction):
    src1: Register
    src2: Register
    label: Label

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"ble {self.src1} {self.src2} {self.label}", comments)
        BranchIfGreaterThanOrEqual(self.src2, self.src1, self.label).evaluate(program, cur_block)


@dataclass
class BranchIfGreaterThanUnsigned(Instruction):
    src1: Register
    src2: Register
    label: Label

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"bgtu {self.src1} {self.src2} {self.label}", comments)
        BranchIfLessThanUnsigned(self.src2, self.src1, self.label).evaluate(program, cur_block)


@dataclass
class BranchIfLessThanOrEqualUnsigned(Instruction):
    src1: Register
    src2: Register
    label: Label

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"bleu {self.src1} {self.src2} {self.label}", comments)
        BranchIfGreaterThanOrEqualUnsigned(self.src2, self.src1, self.label).evaluate(program, cur_block)
