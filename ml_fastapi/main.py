import sys
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend_django"))

from inventory.forecasting import lstm_forecast


app = FastAPI(title="ML Forecast Service", version="0.3.0")


class ForecastRequest(BaseModel):
    sku: str = Field(..., description="Identificador del producto")
    history: List[float] = Field(default_factory=list, description="Serie historica agregada")
    horizon: int = Field(12, gt=0, le=60, description="Numero de periodos a predecir")
    freq: str = Field("M", description="Frecuencia (M mensual, W semanal)")
    exog: Optional[dict] = Field(None, description="Variables externas opcionales")


class ForecastResponse(BaseModel):
    sku: str
    horizon: int
    forecast: List[float]
    model: str
    lookback: int
    epochs: int


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/forecast", response_model=ForecastResponse)
def forecast(req: ForecastRequest):
    if req.horizon <= 0:
        raise HTTPException(status_code=400, detail="El horizonte debe ser positivo.")

    pred = lstm_forecast(req.history, req.horizon)

    return ForecastResponse(
        sku=req.sku,
        horizon=req.horizon,
        forecast=pred.values,
        model=pred.method,
        lookback=pred.lookback,
        epochs=pred.epochs,
    )
