from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from registers import (
    ROOT,
    Immediate,
    Register,
    RegisterOrImmediate,
    addressing,
    concater,
    next1,
    next2,
    regs,
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
        self.cond.move(scraps[0], scraps[1])
        scraps[1].move(self.cond)
        next1.change(next_i)  # set the default value
        next2.change(next_j)  # set the default value
        scraps[0].to()
        concater.raw("[")  # condition is true
        next1.change(next_i, jump_i)
        next2.change(next_j, jump_j)
        scraps[0].to()
        concater.raw("[-]]")


@dataclass
class JumpRelative(Instruction):
    offset: Immediate

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        next_i, next_j = program.find_next_block(cur_block)
        concater.rem(f"jmr {self.offset}", comments)
        next1.change(next_i)
        next2.change(next_j)


@dataclass
class Move(Instruction):
    dst: Register
    src: RegisterOrImmediate

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"mov {self.dst} {self.src}", comments)
        self.dst.clear()
        self.src.move(self.dst)


@dataclass
class Copy(Instruction):
    dst: Register
    src: Register

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"cpy {self.dst} {self.src}", comments)
        self.dst.clear()
        self.src.move(self.dst, scraps[0])
        scraps[0].move(self.src)


@dataclass
class Add(Instruction):
    dst: Register
    src: RegisterOrImmediate

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"add {self.dst} {self.src}", comments)
        if isinstance(self.src, Immediate):
            self.src.move(self.dst)
        else:
            self.src.move(self.dst, scraps[0])
            scraps[0].move(self.src)


@dataclass
class Sub(Instruction):
    dst: Register
    src: RegisterOrImmediate

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"sub {self.dst} {self.src}", comments)
        if isinstance(self.src, Immediate):
            self.src.move(self.dst, multiplier=-1)
        else:
            self.src.move(self.dst, scraps[0], multiplier=(-1, 1))
            scraps[0].move(self.src)


@dataclass
class Raw(Instruction):
    code: str

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        ROOT.to()
        concater.raw(self.code)


@dataclass
class Load(Instruction):
    dst: Register
    addr: RegisterOrImmediate

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"lda {self.dst} {self.addr}", comments)

        if isinstance(self.addr, Immediate):
            src = Register(13 + self.addr)
            self.dst.clear()
            src.move(self.dst, scraps[0])
            scraps[0].move(src)
        else:
            self.addr.move(addressing[0], addressing[1], scraps[0])
            scraps[0].move(self.addr)
            self.dst.clear()
            addressing[0].to()
            concater.raw(
                "[>>[>+<-]<[>+<-]<[>+<-]>>>>[<<<<+>>>>-]<<<-] "
                ">>>>[<+<+>>-]<[>+<-]<<"
                " [<<[>>>>+<<<<-]>>[<+>-]>[<+>-]<<-]<"
            )
            addressing[2].move(self.dst)


@dataclass
class Store(Instruction):
    addr: RegisterOrImmediate
    src: RegisterOrImmediate

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"sta {self.addr} {self.src}", comments)

        if isinstance(self.addr, Immediate):
            dst = Register(13 + self.addr)
            dst.clear()
            if isinstance(self.src, Immediate):
                self.src.move(dst)
            else:
                self.src.move(dst, scraps[0])
                scraps[0].move(self.src)
        else:
            self.addr.move(addressing[0], addressing[1], scraps[0])
            scraps[0].move(self.addr)
            if isinstance(self.src, Register):
                self.src.move(addressing[2], scraps[0])
                scraps[0].move(self.src)
            addressing[0].to()
            concater.raw("[>>[>+<-]<[>+<-]<[>+<-]>>>>[<<<<+>>>>-]<<<-] ")
            if isinstance(self.src, Immediate):
                concater.raw(">>>>")
                concater.current_pos.clear()
                concater.current_pos.change(self.src)
                concater.raw("<<<")
            else:
                concater.raw(">>>>[-]<<[>>+<<-]<")
            concater.raw(" [<<[>>>>+<<<<-]>>[<+>-]<-]<")


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


@dataclass
class Print(Instruction):
    val: str

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"prt {self.val}", comments)
        for value in self.val:
            scraps[0].change(ord(value))
            scraps[0].to()
            concater.raw(".")
            scraps[0].clear()


@dataclass
class Call(Instruction):
    target: Label

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        next_i, next_j = program.find_next_block(cur_block)
        concater.rem(f"call {self.target}", comments)
        Store(regs["SP"], Immediate(next_i)).evaluate(program, cur_block)
        regs["SP"].change(1)
        Store(regs["SP"], Immediate(next_j)).evaluate(program, cur_block)
        regs["SP"].change(1)
        Jump(self.target).evaluate(program, cur_block)


@dataclass
class Return(Instruction):
    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem("ret", comments)
        regs["SP"].change(-1)
        Load(next2, regs["SP"]).evaluate(program, cur_block)
        regs["SP"].change(-1)
        Load(next1, regs["SP"]).evaluate(program, cur_block)


MNEMONICS: dict[str, type[Instruction]] = dict()

MNEMONICS["jmp"] = Jump
MNEMONICS["jnz"] = JumpConditional
MNEMONICS["jmr"] = JumpRelative
MNEMONICS["mov"] = Move
MNEMONICS["cpy"] = Copy
MNEMONICS["add"] = Add
MNEMONICS["sub"] = Sub
MNEMONICS["raw"] = Raw
MNEMONICS["lda"] = Load
MNEMONICS["sta"] = Store
MNEMONICS["out"] = Output
MNEMONICS["prt"] = Print
MNEMONICS["call"] = Call
MNEMONICS["ret"] = Return


def is_block_boundary(self):
    return isinstance(
        self,
        (
            LabelDefine,
            JumpRelative,
            JumpConditional,
            Jump,
            Call,
            Return,
        ),
    )
