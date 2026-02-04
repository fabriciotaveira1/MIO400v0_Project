import struct
import socket

class MIO400Controller:
    # Constantes do Protocolo
    HEADER = bytes.fromhex("aa55aa55")
    FIXED_FIELDS = bytes.fromhex("000000010000001200000000ffffffff00000000000005fe")
    
    def __init__(self, ip, port=5000):
        self.ip = ip
        self.port = port

    def _build_packet(self, opcode: int, component_addr: int, action: int, 
                      total_time: int = 0, t_on: int = 0, t_off: int = 0, memory: int = 0) -> bytes:
        """
        Monta o pacote binário conforme a especificação da Commbox.
        """
        # O cabeçalho e campos fixos somam 28 bytes iniciais conforme seu exemplo
        packet = self.HEADER + self.FIXED_FIELDS
        
        # Adicionando os campos variáveis (Opcode, Endereço, Atuação, Tempos, Memória)
        # Formato struct: >I (Unsigned Int 32-bit Big-endian), >B (Unsigned Byte)
        packet += struct.pack(">I", opcode)          # 00000001
        packet += struct.pack(">I", component_addr)  # 00000001
        packet += struct.pack(">B", action)          # 01 (1 byte)
        packet += struct.pack(">I", total_time)      # 00000000
        packet += struct.pack(">I", t_on)            # 00000000
        packet += struct.pack(">I", t_off)           # 00000000
        packet += struct.pack(">B", memory)          # 00 (1 byte)
        
        return packet

    def send_command(self, component_addr, action):
        """Envia o comando de atuação e aguarda o ACK.
        action: 0=off, 1=on, 2=toggle"""
        packet = self._build_packet(opcode=1, component_addr=component_addr, action=action)
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3.0)
                s.connect((self.ip, self.port))
                s.sendall(packet)
                
                response = s.recv(1024)
                return self._parse_response(response)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _parse_response(self, data: bytes):
        """
        Analisa a resposta: 0x8... = ACK, 0x4... = NACK
        """
        if not data:
            return {"status": "timeout"}
            
        # O status de resposta começa no byte 28 (conforme o exemplo fornecido)
        status_hex = data[28:32].hex()
        
        if status_hex.startswith("8"):
            return {"status": "success", "code": status_hex}
        elif status_hex.startswith("4"):
            return {"status": "nack", "code": status_hex}
        
        return {"status": "unknown", "raw": data.hex()}