"""Detection report for a match: `python -m app.patterns.report demo_01`."""

import sys

from app.config import get_settings
from app.events.catalog import load_meta
from app.models.events import Event
from app.patterns.config import load_patterns_config
from app.patterns.engine import detect_all


def main(match_id: str) -> None:
    settings = get_settings()
    meta = load_meta(settings.data_dir, match_id)
    path = settings.data_dir / "matches" / f"{match_id}.jsonl"
    events = [Event.model_validate_json(line) for line in path.read_text().splitlines() if line.strip()]
    detections = detect_all(
        events, [t.team_id for t in meta.teams], load_patterns_config(settings.config_dir)
    )
    print(f"{match_id}: {len(detections)} detections")
    for d in detections:
        strength = "" if d.rule_strength is None else f"  signal {d.rule_strength:.2f}"
        print(
            f"  {d.minute:>3}:{d.second:02d}  {d.kind:<10} {d.pattern:<20} {d.team_id or '-':<4}{strength}  {d.evidence}"
        )


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "demo_01")
