# main.py

import uvicorn
from fastapi import FastAPI
from app.api.routes_outputs import router as outputs_router
from app.api.routes_inputs import router as inputs_router

app = FastAPI(title="Commbox MIO400")

app.include_router(outputs_router)
app.include_router(inputs_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)