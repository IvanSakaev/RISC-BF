from instructions.baseInstructions import *


@dataclass
class StoreWord(Instruction):
    src: Register
    addr: OffsetRegister
    
    def execute(self):
        pass
    