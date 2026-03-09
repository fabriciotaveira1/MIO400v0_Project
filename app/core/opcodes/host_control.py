import struct


def build_host_read_request(address: int) -> bytes:
    """
    Opcode 14 - leitura da configuracao de host por endereco.
    """
    return struct.pack(">I", int(address))


def build_host_enable_command(address: int, enabled: int) -> bytes:
    """
    Opcode 26 - habilita/desabilita host por endereco.
    """
    return struct.pack(">IB", int(address), int(enabled))


def build_hosts_enable_read_request() -> bytes:
    """
    Opcode 27 - leitura da mascara de habilitacao dos hosts.
    """
    return b""
