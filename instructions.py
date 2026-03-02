from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from registers import (
    ZERO,
    Immediate,
    Register,
    concater,
    next1,
    next2,
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
class JumpConditional(Instruction):
    cond: Register
    target: Label

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        next_i, next_j = program.find_next_block(cur_block)
        jump_i, jump_j = program.find_block(self.target)
        concater.rem(f"jnz {self.cond} {self.target}", comments)
        self.cond.copy(scraps[0], scrap=scraps[1])
        next1.change(next_i)  # set the default value
        next2.change(next_j)  # set the default value
        with scraps[0].loop():
            scraps[0].clear()
            next1.change(next_i, jump_i)
            next2.change(next_j, jump_j)


@dataclass
class JumpRelative(Instruction):
    offset: Immediate

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        next_i, next_j = program.find_next_block(cur_block)
        concater.rem(f"jmr {self.offset}", comments)
        next1.change(next_i)
        next2.change(next_j)


@dataclass
class LI(Instruction):
    dst: Register
    src: Immediate

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"li {self.dst} {self.src}", comments)
        if self.dst == ZERO:
            return
        assert self.src < (2**32)
        self.dst.change_big(self.src, clear=True)


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
            scraps[0].move_big(self.dst, multiplier=2)
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
        cls, src: Register, dst: Register, scrap: Register | None = None, clear=False
    ):
        """
        Moves bitwise not src to dst. After this function, src will become zero.
        Initial src value will be restored from scrap if scrap isn't None.

        Src must be normalized. Dst will be NOT normalized.
        If dst was zero or clear=True, every dst cell will be <= 0x10.

        dst.normalize_big_fast() can be used after this function
        """
        for i in range(8):
            if clear:
                dst.clear()
            dst.change(15)
            dst = dst.reg_rel(1)
        dst = dst.reg_rel(-8)

        for i in range(8):
            src.move(dst, multiplier=-1)
            if scrap is not None:
                src.move(scrap)
            src = src.reg_rel(1)
            dst = dst.reg_rel(1)
        src = src.reg_rel(-8)
        dst = dst.reg_rel(-8)

        dst.change(1)
        if scrap is not None:
            scrap.move_big(src)


@dataclass
class Output(Instruction):
    reg: Register

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"out {self.reg}", comments)

        # Division by 10
        mod = scraps[0]
        # 2 scraps after MOD are used too
        output = scraps[3]
        # scrap 4 is used too

        for i in range(8):
            small = self.reg.reg_rel(7 - i)
            small.div_imm(10)

            mod.copy(small, scrap=scraps[4])
            mod.change(48)

            with output.loop():
                output.move(small, multiplier=10)
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

MNEMONICS["li"] = LI
MNEMONICS["add"] = Add
MNEMONICS["addi"] = AddI
MNEMONICS["sub"] = Sub

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
