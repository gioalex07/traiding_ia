"""Train and evaluate a signal quality classifier.

Uses scikit-learn RandomForest. Falls back gracefully if not installed.
"""
import logging
from typing import Any

from rac.config import Settings
from rac.ml.dataset import FEATURE_NAMES, TrainingDatasetBuilder

log = logging.getLogger("rac.ml.trainer")


def _to_matrix(X: list[dict[str, float]]) -> list[list[float]]:
    return [[row.get(f, 0.0) for f in FEATURE_NAMES] for row in X]


class ModelTrainer:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def train(
        self,
        include_timeout: bool = False,
        n_estimators: int = 100,
        test_size: float = 0.2,
    ) -> dict[str, Any]:
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.metrics import classification_report
            from sklearn.model_selection import cross_val_score, train_test_split
        except ImportError:
            return {"error": "scikit-learn not installed — run: pip install scikit-learn"}

        builder = TrainingDatasetBuilder(self._settings)
        X_dicts, y, ids = builder.build(include_timeout=include_timeout)

        if len(X_dicts) < 10:
            return {"error": f"not_enough_labeled_data: {len(X_dicts)} samples"}

        X = _to_matrix(X_dicts)
        wins = sum(y)
        losses = len(y) - wins
        log.info("training on %d samples (%d wins, %d losses)", len(y), wins, losses)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y if wins > 1 and losses > 1 else None
        )

        model = RandomForestClassifier(
            n_estimators=n_estimators,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X_train, y_train)

        # Cross-val on train set
        cv_scores = cross_val_score(model, X_train, y_train, cv=min(5, len(X_train)), scoring="roc_auc")

        y_pred = model.predict(X_test)
        report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

        importance = sorted(
            zip(FEATURE_NAMES, model.feature_importances_),
            key=lambda x: x[1],
            reverse=True,
        )

        return {
            "samples_train":    len(X_train),
            "samples_test":     len(X_test),
            "wins":             wins,
            "losses":           losses,
            "win_rate_pct":     round(wins / len(y) * 100, 1),
            "accuracy":         round(float(report.get("accuracy", 0)), 3),
            "precision_win":    round(float(report.get("1", {}).get("precision", 0)), 3),
            "recall_win":       round(float(report.get("1", {}).get("recall", 0)), 3),
            "f1_win":           round(float(report.get("1", {}).get("f1-score", 0)), 3),
            "cv_roc_auc_mean":  round(float(cv_scores.mean()), 3),
            "cv_roc_auc_std":   round(float(cv_scores.std()),  3),
            "feature_importance": {k: round(float(v), 4) for k, v in importance},
        }
