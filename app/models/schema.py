# /models/schema.py
from pydantic import BaseModel, Field

class CommandRequest(BaseModel):
    component_addr: int = Field(..., description="Endereço da saída (ex:1)")
    action: int = Field(..., description="Ação: 0=off, 1=on, 2=toggle")
    total_time: int = Field(0, description="Tempo total em unidades de 10ms")
    memory: int = Field(0, ge=0, le=1, descriptions="1 para salvar no NVRAN")