from typing import List, Optional

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


app = FastAPI(title="ML Forecast Service", version="0.2.0")


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


def seasonal_mean_forecast(history: np.ndarray, horizon: int, season_length: int = 12) -> List[float]:
    """
    Forecast con estacionalidad mensual:
    - Si hay >= 1 temporada completa, calcula la media por mes y repite el patrón.
    - Si no, usa media móvil de las últimas k observaciones.
    """
    n = history.size
    if n >= season_length:
        usable = history[-(n // season_length * season_length) :]
        seasons = usable.reshape(-1, season_length)
        month_means = seasons.mean(axis=0)
        reps = int(np.ceil(horizon / season_length))
        forecast = np.tile(month_means, reps)[:horizon]
    elif n > 0:
        k = min(6, n)
        avg = float(history[-k:].mean())
        forecast = np.full(horizon, avg)
    else:
        forecast = np.zeros(horizon)
    return forecast.tolist()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/forecast", response_model=ForecastResponse)
def forecast(req: ForecastRequest):
    if req.horizon <= 0:
        raise HTTPException(status_code=400, detail="El horizonte debe ser positivo.")

    hist = np.array(req.history, dtype=float)
    pred = seasonal_mean_forecast(hist, req.horizon, season_length=12 if req.freq.upper() == "M" else 4)

    return ForecastResponse(sku=req.sku, horizon=req.horizon, forecast=pred)
