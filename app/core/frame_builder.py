# core/frame_builder.py
import struct
import threading


class FrameBuilder:
    HEADER_SYMBOL = 0xAA55AA55
    PROTOCOL_VERSION = 0x00000001

    def __init__(self, source_id: int = 1, destiny_id: int = 1):
        self.source_id = source_id
        self.destiny_id = destiny_id
        self._sequence = 0
        self._lock = threading.Lock()

    def _next_sequence(self) -> int:
        with self._lock:
            self._sequence += 1
            return self._sequence

    def build_frame(self, opcode: int, application_data: bytes) -> bytes:
        """
        Monta frame completo conforme especificação oficial.
        """

        frame_sequence = self._next_sequence()
        data_size = len(application_data)

        # Header sem checksum
        header_without_checksum = (
            struct.pack(">I", self.HEADER_SYMBOL) +
            struct.pack(">I", self.PROTOCOL_VERSION) +
            struct.pack(">I", data_size) +
            struct.pack(">I", self.source_id) +
            struct.pack(">I", self.destiny_id) +
            struct.pack(">I", frame_sequence) +
            b'\x00\x00\x00\x00' +  # placeholder checksum
            struct.pack(">I", opcode)
        )

        frame_without_checksum = header_without_checksum + application_data

        # Calcula checksum (soma de todos os bytes exceto o campo checksum)
        checksum = self._calculate_checksum(frame_without_checksum)

        # Reconstrói header com checksum correto
        header = (
            struct.pack(">I", self.HEADER_SYMBOL) +
            struct.pack(">I", self.PROTOCOL_VERSION) +
            struct.pack(">I", data_size) +
            struct.pack(">I", self.source_id) +
            struct.pack(">I", self.destiny_id) +
            struct.pack(">I", frame_sequence) +
            struct.pack(">I", checksum) +
            struct.pack(">I", opcode)
        )

        return header + application_data

    @staticmethod
    def _calculate_checksum(frame: bytes) -> int:
        return sum(frame) & 0xFFFFFFFF