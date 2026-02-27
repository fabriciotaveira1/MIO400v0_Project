import struct


def build_input_configuration(
    address: int,
    enabled: int = 1,
    activation_level: int = 1,
    on_delay: int = 0,
    off_delay: int = 0,
    host_report_mode: int = 0b00000111,   # habilita + atuar + desatuar
    host_report_mask: int = 0x00000001,   # host 1
    log_mode: int = 0,
    info_type: int = 1,
    name: str = "input"
) -> bytes:

    data = b''

    data += struct.pack(">I", address)
    data += struct.pack(">B", enabled)
    data += struct.pack(">B", activation_level)
    data += struct.pack(">I", on_delay)
    data += struct.pack(">I", off_delay)

    data += struct.pack(">H", host_report_mode)
    data += struct.pack(">I", host_report_mask)
    data += struct.pack(">H", log_mode)

    data += struct.pack(">B", info_type)

    name_bytes = name.encode("ascii")
    name_bytes = name_bytes[:24]
    name_bytes += b'\x00' * (24 - len(name_bytes))

    data += name_bytes

    return data