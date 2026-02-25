# api\routes.py
import asyncio
from fastapi import APIRouter, HTTPException
from app.core.commbox_client import CommboxClient
from app.core.opcodes.output import build_output_command
from app.models.schema import CommandRequest

router = APIRouter()

async def tcp_check(ip: str, port: int, timeout: float = 1.5) -> bool:
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port),
            timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False


# Instância global (Em produção, o IP viria de uma config/env)
controller = MIO400Controller(ip="192.168.26.228", port=5000)

# ROTA PARA ATUAÇÃO DE SAÍDAS
@router.post("/control/output")
async def actuate_output(cmd: CommandRequest):
    """
    Envia um comando de atuação para a controladora MIO400.
    """
    result = controller.send_command(
        component_addr=cmd.component_addr,
        action=cmd.action,
        total_time=cmd.total_time,
        memory=cmd.memory
    )
    
    if result["status"] == "success":
        return {"message": "Comando executado", "details": result}
    
    raise HTTPException(status_code=500, detail=result)

# ROTA PARA CHECAGEM DE SAÚDE DA CONEXÃO COM A MIO400
@router.get("/health")
async def health_check():
    ip = controller.ip
    port = controller.port  # porta real da MIO

    if not await tcp_check(ip, port):
        return {
            "status": "error",
            "message": "MIO Desconectada ou com problemas de rede",
            "target_device": ip
        }

    return {
        "status": "online",
        "message": "Conectividade OK",
        "target_device": ip
    }

# ROTA DE TESTE PARA MONTAGEM DE PACOTE
@router.post("/test/packet-build")
async def test_packet_build(cmd: CommandRequest):
    """
    Rota de teste que não envia nada ao hardware, 
    apenas retorna o pacote HEX que seria enviado.
    """
    try:
        # Geramos o pacote binário usando a lógica da classe
        packet = controller._build_packet(
            opcode=1, 
            component_addr=cmd.component_addr, 
            action=cmd.action,
            total_time=cmd.total_time,
            memory=cmd.memory
        )
        
        return {
            "status": "simulation",
            "hex_to_send": packet.hex(),
            "packet_size_bytes": len(packet),
            "interpreted_values": {
                "address": cmd.component_addr,
                "action": cmd.action,
                "memory": cmd.memory
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao montar pacote: {str(e)}")