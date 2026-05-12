"""Live ML confidence — replaces hand-crafted strategy formulas.

MLConfidenceService loads the persisted RandomForest model and returns
P(win) for any feature vector. Falls back to None if model unavailable;
callers should then use the strategy's rule-based confidence.
"""
import logging
import pickle
from pathlib import Path
from typing import Any

from rac.ml.dataset import FEATURE_NAMES, extract_features
from rac.ml.trainer import MODEL_PATH

log = logging.getLogger("rac.ml.confidence")


class MLConfidenceService:
    """Singleton-style: load once, predict many."""

    def __init__(self) -> None:
        self._model: Any = None
        self._loaded = False

    def load(self, path: Path = MODEL_PATH) -> bool:
        try:
            with path.open("rb") as f:
                data = pickle.load(f)
            self._model = data["model"]
            self._loaded = True
            log.info("ML confidence model loaded from %s", path)
            return True
        except FileNotFoundError:
            log.info("No ML model found at %s — using rule-based confidence", path)
            return False
        except Exception as exc:
            log.warning("ml_model_load_error: %s", exc)
            return False

    @property
    def available(self) -> bool:
        return self._loaded and self._model is not None

    def predict(self, values: dict[str, Any], direction: str) -> float | None:
        """Return P(win) in [0,1], or None if model unavailable."""
        if not self.available:
            return None
        try:
            features = extract_features(values, direction)
            X = [[features.get(f, 0.0) for f in FEATURE_NAMES]]
            proba = self._model.predict_proba(X)[0]
            # class index 1 = win
            classes = list(self._model.classes_)
            win_idx = classes.index(1) if 1 in classes else 1
            return float(proba[win_idx])
        except Exception as exc:
            log.warning("ml_confidence_predict_error: %s", exc)
            return None
