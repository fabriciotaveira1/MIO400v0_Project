import struct

def build_heartbeat_tcp_configuration(
    data_code: int = 4,      # 4 = inputs + outputs
    interval_ms: int = 3000  # intervalo em milissegundos
) -> bytes:

    data = b''
    data += struct.pack(">I", data_code)
    data += struct.pack(">I", interval_ms)

    return data