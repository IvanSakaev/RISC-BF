from __future__ import annotations

from typing import TYPE_CHECKING

import config
from config import ALLOW_ASSERTS, ALLOW_DEBUG, COMPRESSED

if TYPE_CHECKING:
    from registers import Cell


class _Concater:
    def __init__(self, root: Cell):
        self.current_pos = root
        self.current_program = []
        # Using a list and joining it at the end is much faster than adding string every
        # time, because `a = a + "hello"` creates a new string instead of modifying current, which is very slow.
        self.last_char = None
        self.last_char_count = 0

    @classmethod
    def sanitize(cls, name: str):
        name = (
            name
            .replace("+", "_")
            .replace("-", "_")
            .replace("<", "_")
            .replace(">", "_")
            .replace("[", "_")
            .replace("]", "_")
            .replace(".", "_")
            .replace(",", "_")
            .replace("#", "_")
            .replace("@", "_")
            .replace("!", "_")
        )
        return name

    @classmethod
    def is_repeatable(cls, char: str | None):
        return char == "+" or char == "-" or char == "<" or char == ">"

    def _apply_char(self):
        if COMPRESSED and self.last_char is not None:
            if self.last_char_count == 1:
                self.current_program.append(f"{self.last_char}")
            elif self.last_char_count > 1:
                self.current_program.append(f"{self.last_char}{{{self.last_char_count:x}}}")
            self.last_char = None
            self.last_char_count = 0

    def raw(self, text: str, pos_offset: int = 0):
        if len(text) != 0:
            if COMPRESSED and self.is_repeatable(self.last_char):
                while len(text) > 0 and text[0] == self.last_char:
                    self.last_char_count += 1
                    text = text[1:]
            if len(text) != 0:
                self._apply_char()
                self.current_program.append(text)
        self.current_pos = self.current_pos.cell_rel(pos_offset)

    def raw_char(self, char: str, count: int):
        assert len(char) == 1
        if COMPRESSED and self.is_repeatable(char):
            if char != self.last_char:
                self._apply_char()
                self.last_char = char
            self.last_char_count += count
        else:
            self._apply_char()
            self.current_program.append(char * count)

    def rem(self, text: str, comments: bool):
        if comments:
            self._apply_char()
            bp = " #" if config.BREAKPOINT_EVERY_INSTRUCTION else ""
            self.raw("\n        " + self.sanitize(text) + bp + "\n          ")

    def debug(self):
        if ALLOW_DEBUG:
            self._apply_char()
            self.raw("#")

    def assert_pos(self):
        if ALLOW_ASSERTS:
            self._apply_char()
            self.raw(f"@{self.current_pos.addr:x}")

    def assert_val(self, value: int):
        if ALLOW_ASSERTS:
            self._apply_char()
            self.raw(f"!{value:x}")

    def get_code(self):
        self._apply_char()
        return "".join(self.current_program)

    def reset_code(self, new_pos: Cell | None = None):
        self.current_program = []
        if new_pos is not None:
            self.current_pos = new_pos
