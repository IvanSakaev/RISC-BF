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


class Label(str): ...


class Instruction:
    program: Program

    def evaluate(self, program: Program, comments: bool = False) -> None: ...


@dataclass
class LabelDefine(Instruction):
    name: Label


@dataclass
class Jump(Instruction):
    target: Label

    def evaluate(self, program: Program, comments: bool = False):
        concater.rem(f"jmp {self.target}", comments)
        i, j = program.find_block(self.target)
        next1.change(0, i)
        next2.change(0, j)


@dataclass
class JumpConditional(Instruction):
    cond: Register
    target: Label


@dataclass
class JumpRelative(Instruction):
    offset: Immediate


@dataclass
class Move(Instruction):
    dst: Register
    src: RegisterOrImmediate


@dataclass
class Copy(Instruction):
    dst: Register
    src: Register


@dataclass
class MovAdd(Instruction):
    dst: Register
    src: RegisterOrImmediate


@dataclass
class Add(Instruction):
    dst: Register
    src: Register


@dataclass
class MovSub(Instruction):
    dst: Register
    src: RegisterOrImmediate


@dataclass
class Sub(Instruction):
    dst: Register
    src: Register


@dataclass
class Raw(Instruction):
    code: str


@dataclass
class Load(Instruction):
    dst: Register
    addr: RegisterOrImmediate


@dataclass
class Store(Instruction):
    addr: RegisterOrImmediate
    src: RegisterOrImmediate


@dataclass
class Output(Instruction):
    reg: RegisterOrImmediate


@dataclass
class Print(Instruction):
    val: str


@dataclass
class Call(Instruction):
    target: Label


@dataclass
class Return(Instruction): ...


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


MNEMONICS: dict[str, type[Instruction]] = dict()

MNEMONICS["jmp"] = Jump
MNEMONICS["jnz"] = JumpConditional
MNEMONICS["jmr"] = JumpRelative
MNEMONICS["mov"] = Move
MNEMONICS["cpy"] = Copy
MNEMONICS["addm"] = MovAdd
MNEMONICS["add"] = Add
MNEMONICS["subm"] = MovSub
MNEMONICS["sub"] = Sub
MNEMONICS["raw"] = Raw
MNEMONICS["lda"] = Load
MNEMONICS["sta"] = Store
MNEMONICS["out"] = Output
MNEMONICS["prt"] = Print
MNEMONICS["call"] = Call
MNEMONICS["ret"] = Return


def is_block_boundary(inst):
    return isinstance(
        inst,
        (
            LabelDefine,
            JumpRelative,
            JumpConditional,
            Jump,
            Call,
            Return,
        ),
    )
