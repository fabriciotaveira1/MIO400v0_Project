# core/opcodes/output.py
import struct


def build_output_command(
    component_addr: int,
    action: int,
    total_time: int = 0,
    t_on: int = 0,
    t_off: int = 0,
    memory: int = 0
) -> bytes:
    """
    Opcode 01 - Atuação nas saídas
    """

    data = b''
    data += struct.pack(">I", component_addr)
    data += struct.pack(">B", action)
    data += struct.pack(">I", total_time)
    data += struct.pack(">I", t_on)
    data += struct.pack(">I", t_off)
    data += struct.pack(">B", memory)

    return data