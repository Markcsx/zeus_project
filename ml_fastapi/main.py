from typing import List, Optional

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


app = FastAPI(title="ML Forecast Service", version="0.1.0")


class ForecastRequest(BaseModel):
    sku: str = Field(..., description="Identificador del producto")
    history: List[float] = Field(default_factory=list, description="Serie histórica agregada")
    horizon: int = Field(12, gt=0, le=60, description="Número de periodos a predecir")
    freq: str = Field("M", description="Frecuencia (M mensual, W semanal)")
    exog: Optional[dict] = Field(None, description="Variables externas opcionales")


class ForecastResponse(BaseModel):
    sku: str
    horizon: int
    forecast: List[float]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/forecast", response_model=ForecastResponse)
def forecast(req: ForecastRequest):
    if req.horizon <= 0:
        raise HTTPException(status_code=400, detail="El horizonte debe ser positivo.")

    hist = np.array(req.history, dtype=float)
    if hist.size == 0:
        pred = [0.0] * req.horizon
    else:
        k = min(6, hist.size)
        avg = float(hist[-k:].mean())
        pred = [avg] * req.horizon

    return ForecastResponse(sku=req.sku, horizon=req.horizon, forecast=pred)
