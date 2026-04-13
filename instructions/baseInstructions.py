from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from cell import Cell, scraps, concater, nexts, memory_scraps
from registers import (
    ZERO,
    Cell,
    Immediate,
    Register,
    OffsetRegister,
    scraps,
)

if TYPE_CHECKING:
    from instructions.jumpInstructions import LabelDefine
    from asm import Program


class Instruction:
    def evaluate(self, program: Program, cur_block: Block, comments: bool = False): ...


@dataclass
class Block:
    myid: int | None
    daughter_blocks: list[Block] | list[Instruction]
    mother_block: Block | None
    labels: list[str]
