# core/opcodes/host.py

import struct
import socket


def ip_to_int(ip: str) -> int:
    return struct.unpack(">I", socket.inet_aton(ip))[0]


def build_host_configuration(
    host_address: int,
    enabled: int,
    host_id: int,
    protocol: int,
    server_ip: str,
    server_port: int,
    hw_port: int = 1
) -> bytes:

    data = b''

    data += struct.pack(">I", host_address)          # Endereço
    data += struct.pack(">B", enabled)               # Enable
    data += struct.pack(">I", host_id)               # Host ID
    data += struct.pack(">B", protocol)              # IP Protocol (6 = TCP)
    data += struct.pack(">B", 1)                     # Addressing type = 1 (IP)

    ip_int = ip_to_int(server_ip)
    address_bytes = struct.pack(">I", ip_int)

    # Campo Address tem 40 bytes → preencher restante com zeros
    address_field = address_bytes + (b'\x00' * (40 - 4))
    data += address_field

    data += struct.pack(">H", server_port)           # Source Port (2 bytes)
    data += struct.pack(">B", hw_port)               # HW Port (1 = Ethernet)

    return data