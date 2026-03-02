# main.py

import uvicorn
from fastapi import FastAPI

from app.api.routes_outputs import router as outputs_router
from app.api.routes_inputs import router as inputs_router
from app.api.routes_events import router as events_router
from app.services.socket_listener import SocketListener
from app.api.routes_heartbeat import router as heartbeat_router
from app.api.routes_health import router as health_router



app = FastAPI(title="Commbox MIO400")

app.include_router(outputs_router)
app.include_router(inputs_router)
app.include_router(events_router)
app.include_router(heartbeat_router)
app.include_router(health_router)

# Inicia listener automaticamente
listener = SocketListener(port=4090)
listener.start()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)