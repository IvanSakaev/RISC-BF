from __future__ import annotations

from instructions.arithmeticInstructions import *
import instructions.bitwiseInstructions
from instructions.comparingInstructions import *
from instructions.jumpInstructions import *
from instructions.baseInstructions import Instruction, Block

if TYPE_CHECKING:
    from asm import Program


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
        inst = LoadI(self.dst, Immediate(self.src * (2 ** 12)))
        inst.evaluate(program, cur_block, False)


@dataclass
class Move(Instruction):
    dst: Register
    src: Register

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"mv {self.dst} {self.src}", comments)
        AddI(self.dst, self.src, Immediate(0)).evaluate(program, cur_block, False)


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
            mod.raw(".")
            mod.clear()
        mod.change(10)  # Line feed
        mod.raw(".")
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
MNEMONICS["sll"] = instructions.bitwiseInstructions.ShiftLeft
MNEMONICS["slli"] = instructions.bitwiseInstructions.ShiftLeftI
MNEMONICS["or"] = instructions.bitwiseInstructions.Or
MNEMONICS["and"] = instructions.bitwiseInstructions.And
MNEMONICS["xor"] = instructions.bitwiseInstructions.Xor
MNEMONICS["not"] = instructions.bitwiseInstructions.Not
MNEMONICS["ori"] = instructions.bitwiseInstructions.OrI
MNEMONICS["andi"] = instructions.bitwiseInstructions.AndI
MNEMONICS["xori"] = instructions.bitwiseInstructions.XorI
MNEMONICS["slt"] = SetLessThan
MNEMONICS["sltu"] = SetLessThanUnsigned
MNEMONICS["seqz"] = SetEqualToZero
MNEMONICS["snez"] = SetNotEqualToZero
MNEMONICS["sltz"] = SetLessThanZero
MNEMONICS["sgtz"] = SetGreaterThanZero

# debug commands
MNEMONICS["out"] = Output
MNEMONICS["dbg"] = Debug
