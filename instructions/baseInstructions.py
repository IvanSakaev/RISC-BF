from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from cell import Cell, scraps, concater, next1, next2, memory_scraps
from registers import (
    ZERO,
    Cell,
    Immediate,
    Register,
    OffsetRegister,
    scraps,
)

if TYPE_CHECKING:
    from asm import Program


class Instruction:
    def evaluate(self, program: Program, cur_block: Block, comments: bool = False): ...


@dataclass
class Block:
    myid: int
    daughter_blocks: list[Block] | list[Instruction]
    mother_block: Block | None
    name: str | None
