"""Loads config/patterns.yaml into typed settings."""

from pathlib import Path

import yaml
from pydantic import BaseModel


class SustainedPressureConfig(BaseModel):
    window_seconds: int = 300
    min_possession_pct: float = 65
    min_shots: int = 3
    min_final_third_entries: int = 6
    cooldown_seconds: int = 300


class MomentumShiftConfig(BaseModel):
    window_seconds: int = 300
    weights: dict[str, float] = {"shots": 3, "final_third_entries": 1, "high_recoveries": 2, "xg": 5}
    min_index: float = 8
    min_growth: float = 2.0
    cooldown_seconds: int = 480


class HighPressConfig(BaseModel):
    window_seconds: int = 180
    min_high_recoveries: int = 3
    cooldown_seconds: int = 300


class KeyMomentsConfig(BaseModel):
    big_chance_min_xg: float = 0.30


class PatternsConfig(BaseModel):
    strength_scale: float = 1.5
    sustained_pressure: SustainedPressureConfig = SustainedPressureConfig()
    momentum_shift: MomentumShiftConfig = MomentumShiftConfig()
    high_press_sequence: HighPressConfig = HighPressConfig()
    key_moments: KeyMomentsConfig = KeyMomentsConfig()


def load_patterns_config(config_dir: Path) -> PatternsConfig:
    path = config_dir / "patterns.yaml"
    return (
        PatternsConfig.model_validate(yaml.safe_load(path.read_text()) or {})
        if path.exists()
        else PatternsConfig()
    )
