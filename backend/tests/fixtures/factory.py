"""Tiny builder for hand-made event fixtures."""

from app.events.xg import synthetic_xg
from app.models.events import Event


def ev(
    seq: int,
    t: int,
    etype: str,
    team: str = "NBR",
    *,
    poss: str | None = "same",
    pid: int = 1,
    player: str | None = None,
    outcome: str | None = None,
    x: float | None = None,
    y: float | None = 34.0,
    end_x: float | None = None,
    end_y: float | None = None,
    in_play: bool = True,
    related: list[str] | None = None,
    match_id: str = "fx",
) -> Event:
    """`poss="same"` means the possession team is the acting team."""
    xg = synthetic_xg(x or 90.0, y or 34.0) if etype == "shot" else None
    if etype == "shot" and x is None:
        x = 90.0
    return Event(
        match_id=match_id,
        event_id=f"e{seq:05d}",
        seq=seq,
        period=1 if t < 2820 else 2,
        match_second=t,
        minute=t // 60,
        second=t % 60,
        team_id=team,
        player_id=player,
        event_type=etype,  # type: ignore[arg-type]
        outcome=outcome,
        x=x,
        y=y if x is not None else None,
        end_x=end_x,
        end_y=end_y if end_x is not None else None,
        possession_team_id=team if poss == "same" else poss,
        possession_id=pid,
        shot_outcome=outcome if etype == "shot" else None,
        xg=xg,
        in_play=in_play,
        related_event_ids=related or [],
    )
