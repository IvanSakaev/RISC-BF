from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from registers import (
    ZERO,
    Immediate,
    Register,
    RegisterOrImmediate,
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
        scraps[0].start_loop()
        next1.change(next_i, jump_i)
        next2.change(next_j, jump_j)
        scraps[0].clear()
        scraps[0].end_loop()


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
        val = int(self.src)
        reg = self.dst
        assert val < (2**32)
        for i in range(8):
            reg.clear()
            reg.change(val % 16)
            val //= 16
            reg = reg.reg_rel(1)


@dataclass
class Add(Instruction):
    dst: Register
    src1: Register
    src2: Register

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"add {self.dst} {self.src1} {self.src2}", comments)
        if self.dst == ZERO:
            return
        if self.dst not in (self.src1, self.src2):
            self.dst.clear()

        self.src1, self.src2 = sorted(
            (self.src1, self.src2),
            key=lambda a: 0 if a == ZERO else (1 if a == self.dst else 2),
            reverse=True,
        )
        if self.src1 is not ZERO and self.src1 != self.dst:
            self.src1.copy(self.dst)
        if self.src2 is not ZERO and self.src2 != self.dst:
            self.src2.copy(self.dst)


@dataclass
class AddI(Instruction):
    dst: Register
    src1: Register
    src2: Immediate

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"addi {self.dst} {self.src1} {self.src2}", comments)
        if self.dst == ZERO:
            return
        self.dst.clear()
        if self.src1 is not ZERO:
            self.src1.copy(self.dst)
        self.src2.move(self.dst)


@dataclass
class Sub(Instruction):
    dst: Register
    src1: Register
    src2: Register

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"sub {self.dst} {self.src1} {self.src2}", comments)
        if self.dst == ZERO:
            return
        self.dst.clear()
        if self.src1 is not ZERO:
            self.src1.copy(self.dst, multiplier=-1)
        if self.src2 is not ZERO:
            self.src2.copy(self.dst, multiplier=-1)


@dataclass
class SubI(Instruction):
    dst: Register
    src1: Register
    src2: Immediate

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"subi {self.dst} {self.src1} {self.src2}", comments)
        if self.dst == ZERO:
            return
        self.dst.clear()
        if self.src1 is not ZERO:
            self.src1.copy(self.dst, multiplier=-1)
        self.src2.move(self.dst, multiplier=-1)


@dataclass
class Output(Instruction):
    reg: RegisterOrImmediate

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"out {self.reg}", comments)

        if isinstance(self.reg, Immediate):
            self.reg.move(scraps[0])
            scraps[0].to()
            concater.raw(".")
            scraps[0].clear()
        else:
            self.reg.to()
            concater.raw(".")


MNEMONICS: dict[str, type[Instruction]] = dict()

MNEMONICS["li"] = LI
MNEMONICS["add"] = Add
MNEMONICS["addi"] = AddI
MNEMONICS["sub"] = Sub
MNEMONICS["subi"] = SubI

MNEMONICS["out"] = Output


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
