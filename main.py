# main.py
from fastapi import FastAPI
from app.api.routes_outputs import router as outputs_router
from app.api.routes_inputs import router as inputs_router
from app.api.routes_events import router as events_router
from app.services.socket_listener import SocketListener

app = FastAPI(title="Commbox MIO400")

app.include_router(outputs_router)
app.include_router(inputs_router)
app.include_router(events_router)


@app.on_event("startup")
def start_listener():
    listener = SocketListener(port=4090)
    listener.start()