from rac.strategies.models import StrategyManifest


class StrategyValidator:
    def validate_manifest(self, manifest: StrategyManifest) -> list[str]:
        reasons: list[str] = []
        if manifest.stop_loss_pct <= 0:
            reasons.append("missing_stop_loss")
        if manifest.take_profit_pct <= 0:
            reasons.append("missing_take_profit")
        if manifest.max_position_pct <= 0:
            reasons.append("missing_sizing")
        if not manifest.invalidation_rules:
            reasons.append("missing_invalidation_rules")
        if not manifest.required_features:
            reasons.append("missing_required_features")
        return reasons

    def validate_features(self, manifest: StrategyManifest, feature_values: dict[str, object]) -> list[str]:
        missing = [name for name in manifest.required_features if feature_values.get(name) is None]
        return [f"missing_feature:{name}" for name in missing]

