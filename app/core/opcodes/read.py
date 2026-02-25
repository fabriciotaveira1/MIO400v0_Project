# core/opcodes/read.py

def build_read_request() -> bytes:
    """
    Opcode 02 e 06 não utilizam Application Data.
    """
    return b''