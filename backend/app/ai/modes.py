"""Viewer modes loaded from config/modes.yaml. One generation path; modes are data, not code branches."""

from pathlib import Path

import yaml
from pydantic import BaseModel


class ModeConfig(BaseModel):
    name: str = ""
    label: str
    audience: str
    style: str
    max_words: int
    include_stats: int
    terminology: str
    hidden: bool = False
    requires: str | None = None


def load_modes(config_dir: Path) -> dict[str, ModeConfig]:
    raw = yaml.safe_load((config_dir / "modes.yaml").read_text())
    return {name: ModeConfig(name=name, **cfg) for name, cfg in raw.items()}


def visible_modes(modes: dict[str, ModeConfig]) -> list[str]:
    return [name for name, m in modes.items() if not m.hidden]
