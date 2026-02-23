from __future__ import annotations

from typing import TYPE_CHECKING

import config

if TYPE_CHECKING:
    from registers import Register


class _Concater:
    def __init__(self, root: Register):
        self.root = root
        self.current_pos = self.root
        self.current_program = ""

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

    def raw(self, text: str):
        self.current_program += text

    def rem(self, text: str, comments: bool):
        if comments:
            bp = " #" if config.BREAKPOINT_EVERY_INSTRUCTION else ""
            self.current_program += "\n  " + self.sanitize(text) + bp + "\n    "
    
    def debug(self):
        self.raw("#")

    def init_block(self):
        self.current_pos = self.root
        self.current_program = ""

    def get_block_code(self):
        self.root.to()
        return self.current_program
