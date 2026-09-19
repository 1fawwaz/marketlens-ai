"""Demand forecasting: naive baseline, XGBoost, Prophet."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import numpy as np
import pandas as pd
from sqlalchemy import text
from xgboost import XGBRegressor

from backend.app.database import get_engine
from backend.app.ml.features import compute_daily_category_sales

try:
    from sklearn.metrics import mean_absolute_error

    SKLEARN_METRICS = True
except ImportError:
    SKLEARN_METRICS = False


def _mean_absolute_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if SKLEARN_METRICS:
        return float(mean_absolute_error(y_true, y_pred))
    return float(np.mean(np.abs(y_true - y_pred)))

HORIZONS = (7, 30, 90)
EXPERIMENTAL_HORIZON = 90


@dataclass
class ForecastPoint:
    category: str
    model_name: str
    horizon_days: int
    forecast_date: pd.Timestamp
    predicted_value: float
    is_experimental: bool


def _mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = y_true != 0
    if mask.sum() == 0:
        return 0.0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def _prepare_category_series(df: pd.DataFrame, category: str) -> pd.DataFrame:
    cat = df[df["category"] == category].copy()
    cat["sales_date"] = pd.to_datetime(cat["sales_date"])
    cat = cat.set_index("sales_date").sort_index()
    numeric = cat[["revenue", "order_count", "quantity", "profit"]].astype(float)
    numeric = numeric.asfreq("D", fill_value=0.0).reset_index()
    numeric["category"] = category
    return numeric


def _build_lag_features(series: pd.DataFrame, lags: list[int]) -> pd.DataFrame:
    out = series.copy()
    for lag in lags:
        out[f"lag_{lag}"] = out["revenue"].shift(lag)
    out["dow"] = pd.to_datetime(out["sales_date"]).dt.dayofweek
    out["month"] = pd.to_datetime(out["sales_date"]).dt.month
    return out.dropna()


def naive_forecast(series: pd.DataFrame, horizon: int) -> pd.Series:
    """Seasonal naive: same weekday average over last 4 weeks."""
    rev = series.set_index("sales_date")["revenue"]
    preds = []
    idx = rev.index
    for step in range(1, horizon + 1):
        target_day = idx[-1] + timedelta(days=step)
        same_dow = rev[rev.index.dayofweek == target_day.dayofweek]
        preds.append(float(same_dow.tail(28).mean() if len(same_dow) else rev.tail(7).mean()))
    return pd.Series(preds)


def xgboost_forecast(series: pd.DataFrame, horizon: int) -> pd.Series:
    feats = _build_lag_features(series, lags=[1, 7, 14, 28])
    if len(feats) < 20:
        return naive_forecast(series, horizon)
    x_cols = [c for c in feats.columns if c.startswith("lag_") or c in ("dow", "month")]
    model = XGBRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        objective="reg:squarederror",
        random_state=42,
    )
    model.fit(feats[x_cols], feats["revenue"])
    working = series.copy()
    preds = []
    for _ in range(horizon):
        tmp = _build_lag_features(working, lags=[1, 7, 14, 28]).iloc[-1:]
        pred = float(model.predict(tmp[x_cols])[0])
        pred = max(pred, 0.0)
        preds.append(pred)
        next_date = pd.to_datetime(working["sales_date"].iloc[-1]) + timedelta(days=1)
        working = pd.concat(
            [
                working,
                pd.DataFrame(
                    {
                        "sales_date": [next_date],
                        "revenue": [pred],
                        "category": [working["category"].iloc[0]],
                    }
                ),
            ],
            ignore_index=True,
        )
    return pd.Series(preds)


def prophet_forecast(series: pd.DataFrame, horizon: int) -> pd.Series:
    try:
        from prophet import Prophet
    except ImportError:
        return naive_forecast(series, horizon)

    pdf = series[["sales_date", "revenue"]].rename(columns={"sales_date": "ds", "revenue": "y"})
    pdf["ds"] = pd.to_datetime(pdf["ds"])
    if len(pdf) < 30:
        return naive_forecast(series, horizon)
    model = Prophet(
        yearly_seasonality=False,
        weekly_seasonality=True,
        daily_seasonality=False,
    )
    model.fit(pdf)
    future = model.make_future_dataframe(periods=horizon)
    forecast = model.predict(future).tail(horizon)
    return pd.Series(np.maximum(forecast["yhat"].values, 0.0))


def evaluate_model(
    series: pd.DataFrame,
    horizon: int,
    model_name: str,
    forecaster,
) -> tuple[float, float, int]:
    """Rolling-origin evaluation on last 20% of days."""
    n = len(series)
    min_train = max(30, int(n * 0.5))
    test_start = max(min_train, int(n * 0.8))
    y_true, y_pred = [], []
    for i in range(test_start, n - horizon, max(1, horizon // 2)):
        train = series.iloc[:i].copy()
        actual = float(series.iloc[i : i + horizon]["revenue"].sum())
        pred_series = forecaster(train, horizon)
        predicted = float(pred_series.sum())
        y_true.append(actual)
        y_pred.append(predicted)
    if not y_true:
        return 0.0, 0.0, 0
    return (
        _mean_absolute_error(np.array(y_true), np.array(y_pred)),
        _mape(np.array(y_true), np.array(y_pred)),
        len(y_true),
    )


MODELS = {
    "naive_baseline": naive_forecast,
    "xgboost": xgboost_forecast,
    "prophet": prophet_forecast,
}


def run_forecasting_pipeline() -> dict:
    engine = get_engine()
    daily = compute_daily_category_sales()
    categories = sorted(daily["category"].unique())
    all_forecasts: list[ForecastPoint] = []
    evaluations: list[dict] = []

    for category in categories:
        series = _prepare_category_series(daily, category)
        last_date = pd.to_datetime(series["sales_date"].iloc[-1])
        for horizon in HORIZONS:
            for model_name, fn in MODELS.items():
                mae, mape, samples = evaluate_model(series, horizon, model_name, fn)
                evaluations.append(
                    {
                        "category": category,
                        "model_name": model_name,
                        "horizon_days": horizon,
                        "mae": mae,
                        "mape": mape,
                        "eval_samples": samples,
                    }
                )
                pred_series = fn(series, horizon)
                for step, value in enumerate(pred_series, start=1):
                    all_forecasts.append(
                        ForecastPoint(
                            category=category,
                            model_name=model_name,
                            horizon_days=horizon,
                            forecast_date=last_date + timedelta(days=step),
                            predicted_value=float(value),
                            is_experimental=horizon == EXPERIMENTAL_HORIZON,
                        )
                    )

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE forecast_results RESTART IDENTITY"))
        conn.execute(text("TRUNCATE TABLE forecast_evaluations RESTART IDENTITY"))
        for ev in evaluations:
            conn.execute(
                text(
                    """
                    INSERT INTO forecast_evaluations
                    (category, model_name, horizon_days, mae, mape, eval_samples)
                    VALUES (:category, :model_name, :horizon_days, :mae, :mape, :eval_samples)
                    """
                ),
                ev,
            )
        for fp in all_forecasts:
            conn.execute(
                text(
                    """
                    INSERT INTO forecast_results
                    (category, model_name, horizon_days, forecast_date, predicted_value, is_experimental)
                    VALUES (:category, :model_name, :horizon_days, :forecast_date, :predicted_value, :is_experimental)
                    """
                ),
                {
                    "category": fp.category,
                    "model_name": fp.model_name,
                    "horizon_days": fp.horizon_days,
                    "forecast_date": fp.forecast_date.date(),
                    "predicted_value": fp.predicted_value,
                    "is_experimental": fp.is_experimental,
                },
            )

    return {
        "categories": categories,
        "forecasts": len(all_forecasts),
        "evaluations": len(evaluations),
    }


def get_forecast(category: str, horizon_days: int, model_name: str = "xgboost") -> list[dict]:
    engine = get_engine()
    query = text(
        """
        SELECT forecast_date, predicted_value, is_experimental, model_name
        FROM forecast_results
        WHERE category = :category
          AND horizon_days = :horizon_days
          AND model_name = :model_name
        ORDER BY forecast_date
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(
            query,
            {
                "category": category,
                "horizon_days": horizon_days,
                "model_name": model_name,
            },
        ).mappings().all()
    return [dict(r) for r in rows]
