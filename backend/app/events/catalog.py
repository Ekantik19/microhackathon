"""Which matches exist, and their metadata."""

from pathlib import Path

from app.models.meta import MatchMeta


def list_match_ids(data_dir: Path) -> list[str]:
    return sorted(p.name.removesuffix(".meta.json") for p in (data_dir / "matches").glob("*.meta.json"))


def load_meta(data_dir: Path, match_id: str) -> MatchMeta:
    path = data_dir / "matches" / f"{match_id}.meta.json"
    if not path.exists():
        raise FileNotFoundError(f"no metadata for match {match_id!r}")
    return MatchMeta.model_validate_json(path.read_text())
