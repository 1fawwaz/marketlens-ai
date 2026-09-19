"""Runtime checks for scikit-learn Isolation Forest."""

from __future__ import annotations

import os


class IsolationForestUnavailable(RuntimeError):
    """Raised when Isolation Forest cannot be executed in the current environment."""


_ISOLATION_FOREST_OK: bool | None = None
_ISOLATION_FOREST_ERROR: str | None = None


def isolation_forest_available(*, probe: bool = False) -> bool:
    global _ISOLATION_FOREST_OK, _ISOLATION_FOREST_ERROR
    if _ISOLATION_FOREST_OK is not None and not probe:
        return _ISOLATION_FOREST_OK
    try:
        from sklearn.ensemble import IsolationForest

        model = IsolationForest(random_state=42, n_estimators=10)
        model.fit([[1.0], [2.0], [3.0], [4.0], [100.0]])
        pred = int(model.predict([[100.0]])[0])
        if pred != -1:
            raise RuntimeError("Isolation Forest probe did not flag obvious outlier")
        _ISOLATION_FOREST_OK = True
        _ISOLATION_FOREST_ERROR = None
    except Exception as exc:  # pragma: no cover - environment specific
        _ISOLATION_FOREST_OK = False
        _ISOLATION_FOREST_ERROR = str(exc)
    return bool(_ISOLATION_FOREST_OK)


def require_isolation_forest() -> None:
    if isolation_forest_available():
        return
    msg = _ISOLATION_FOREST_ERROR or "Isolation Forest unavailable"
    if os.getenv("ANOMALY_DETECTOR_FALLBACK", "").lower() == "zscore":
        return
    raise IsolationForestUnavailable(
        f"{msg}. Run anomaly detection inside Docker (docker compose run backend ...) "
        "or set ANOMALY_DETECTOR_FALLBACK=zscore for explicit fallback only."
    )


def active_detector_name() -> str:
    if isolation_forest_available():
        return "isolation_forest"
    if os.getenv("ANOMALY_DETECTOR_FALLBACK", "").lower() == "zscore":
        return "zscore_fallback"
    return "unavailable"
