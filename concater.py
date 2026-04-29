from __future__ import annotations

from typing import TYPE_CHECKING

import config

if TYPE_CHECKING:
    from registers import Cell


class _Concater:
    def __init__(self, root: Cell):
        self.current_pos = root
        self.current_program = []
        # Using a list and joining it at the end is much faster than adding string every
        # time, because `a = a + "hello"` creates a new string instead of modifying current, which is very slow.

    @classmethod
    def sanitize(cls, name: str):
        name = (
            name.replace("+", "_")
            .replace("-", "_")
            .replace("<", "_")
            .replace(">", "_")
            .replace("[", "_")
            .replace("]", "_")
            .replace(".", "_")
            .replace(",", "_")
            .replace("#", "_")
        )
        return name

    def raw(self, text: str, pos_offset: int = 0):
        self.current_program.append(text)
        self.current_pos = self.current_pos.cell_rel(pos_offset)

    def rem(self, text: str, comments: bool):
        if comments:
            bp = " #" if config.BREAKPOINT_EVERY_INSTRUCTION else ""
            self.raw("\n        " + self.sanitize(text) + bp + "\n          ")

    def debug(self):
        self.raw("#")

    def assert_pos(self):
        self.raw(f"@{self.current_pos.addr:x}")

    def get_code(self):
        return "".join(self.current_program)

    def reset_code(self, new_pos: Cell | None = None):
        self.current_program = []
        if new_pos is not None:
            self.current_pos = new_pos
