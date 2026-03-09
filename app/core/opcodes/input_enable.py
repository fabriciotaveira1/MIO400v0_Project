import struct


def build_input_enable_command(address: int, enabled: int) -> bytes:
    """
    Opcode 28 - habilita/desabilita input por endereco.
    """
    return struct.pack(">IB", int(address), int(enabled))


def build_inputs_enable_read_request() -> bytes:
    """
    Opcode 29 - leitura da mascara de habilitacao dos inputs.
    """
    return b""
