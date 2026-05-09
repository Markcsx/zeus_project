from dataclasses import dataclass
from typing import Iterable


MIN_LSTM_HISTORY_POINTS = 24
RECOMMENDED_LSTM_HISTORY_POINTS = 36
DEFAULT_LOOKBACK = 12
SHORT_HISTORY_LOOKBACK = 6


@dataclass(frozen=True)
class ForecastResult:
    values: list[float]
    method: str
    lookback: int
    epochs: int
    history_points: int
    training_samples: int = 0
    message: str = ""


class ForecastingDependencyError(RuntimeError):
    pass


def _load_ml_dependencies():
    try:
        import numpy as np
        import tensorflow as tf
    except ImportError as exc:
        raise ForecastingDependencyError(
            "Instala las dependencias de ML con `pip install -r requirements.txt` "
            "para usar el forecast LSTM."
        ) from exc
    return np, tf


def _make_supervised_windows(series, lookback):
    x, y = [], []
    for idx in range(len(series) - lookback):
        x.append(series[idx : idx + lookback])
        y.append(series[idx + lookback])
    return x, y


def _build_lstm_model(tf, lookback: int):
    return tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(lookback, 1)),
            tf.keras.layers.LSTM(32),
            tf.keras.layers.Dropout(0.15),
            tf.keras.layers.Dense(16, activation="relu"),
            tf.keras.layers.Dense(1),
        ]
    )


def lstm_forecast(
    history: Iterable[float],
    horizon: int = 1,
    lookback: int = DEFAULT_LOOKBACK,
    min_history_points: int = MIN_LSTM_HISTORY_POINTS,
) -> ForecastResult:
    np, tf = _load_ml_dependencies()
    tf.keras.utils.set_random_seed(42)

    series = np.array([max(float(value), 0.0) for value in history], dtype=np.float32)
    horizon = max(int(horizon), 1)
    lookback = max(int(lookback), 2)

    if series.size == 0:
        return ForecastResult([0.0] * horizon, "LSTM_FALLBACK_EMPTY_HISTORY", 0, 0, 0)

    if series.size < min_history_points:
        return ForecastResult(
            [float(series[-1])] * horizon,
            "LSTM_INSUFFICIENT_HISTORY",
            0,
            0,
            int(series.size),
            message=f"Se requieren al menos {min_history_points} periodos historicos para entrenar la LSTM.",
        )

    if series.size < RECOMMENDED_LSTM_HISTORY_POINTS:
        lookback = SHORT_HISTORY_LOOKBACK
        message = (
            f"La LSTM se entreno con {series.size} meses. Es util para pruebas, "
            f"pero se recomiendan al menos {RECOMMENDED_LSTM_HISTORY_POINTS} meses para mayor estabilidad."
        )
    else:
        lookback = DEFAULT_LOOKBACK
        message = ""

    lookback = min(lookback, max(2, int(series.size // 2)))
    mean = float(series.mean())
    std = float(series.std()) or 1.0
    normalized = (series - mean) / std

    x_train, y_train = _make_supervised_windows(normalized, lookback)
    x_train = np.array(x_train, dtype=np.float32).reshape((-1, lookback, 1))
    y_train = np.array(y_train, dtype=np.float32)

    model = _build_lstm_model(tf, lookback)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.01),
        loss="mse",
        metrics=["mae"],
    )

    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="loss",
            patience=20,
            restore_best_weights=True,
        )
    ]
    training = model.fit(
        x_train,
        y_train,
        epochs=250,
        batch_size=min(8, len(x_train)),
        verbose=0,
        callbacks=callbacks,
        shuffle=False,
    )

    rolling_window = normalized[-lookback:].astype(np.float32).tolist()
    predictions = []
    for _ in range(horizon):
        model_input = np.array(rolling_window[-lookback:], dtype=np.float32).reshape((1, lookback, 1))
        next_value = float(model.predict(model_input, verbose=0)[0][0])
        predictions.append(max((next_value * std) + mean, 0.0))
        rolling_window.append(next_value)

    tf.keras.backend.clear_session()
    return ForecastResult(
        values=predictions,
        method="LSTM_KERAS_TENSORFLOW",
        lookback=lookback,
        epochs=len(training.history.get("loss", [])),
        history_points=int(series.size),
        training_samples=len(x_train),
        message=message,
    )
