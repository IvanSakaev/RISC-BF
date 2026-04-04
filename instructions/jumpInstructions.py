from instructions.baseInstructions import *


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
        next_i, next_j = program.find_next_block(cur_block)
        if clear:
            next1.clear()
        next1.change(next_i)
        if clear:
            next2.clear()
        next2.change(next_j)


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

        running = scraps[2]
        running.change(1)
        JumpRelative(Immediate(1)).evaluate(program, cur_block)
        for i in range(7, -1, -1):
            small_src1 = self.src1.get_cell(i)
            small_src2 = self.src2.get_cell(i)
            scrap_src1 = scraps[3]
            scrap_src2 = scraps[4]

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
class BranchIfNotEqualToZero(Instruction):
    src: Register
    label: Label

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"bnez {self.src} {self.label}", comments)
        raise NotImplementedError


def is_block_boundary(self):
    return isinstance(
        self,
        (
            LabelDefine,
            Jump,
            BranchIfLessThanUnsigned,
            BranchIfNotEqualToZero,
        ),
    )
