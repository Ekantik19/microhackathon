"""Builds FactPacks from the MatchState at the moment of a detection. Only events at or before the clock are used,
and every value comes from the deterministic analytics engine."""

from collections.abc import Sequence

from app.ai.models import DetectionSummary, Fact, FactPack, RecapFactPack, RecapMoment, RecentEvent, Trigger
from app.analytics.score import score_at
from app.analytics.state import MatchState
from app.analytics.windows import window_stats, window_stats_between
from app.models.detections import Detection
from app.models.events import EventType, display_clock
from app.models.meta import MatchMeta
from app.models.stats import TeamStats

WINDOW_MINUTES = 5
RECENT_EVENTS = 8
ACTIVE_DETECTION_SECONDS = 600  # live insights only see patterns from the last 10 minutes
NOTABLE = {
    EventType.PASS,
    EventType.CARRY,
    EventType.SHOT,
    EventType.GOAL,
    EventType.TACKLE,
    EventType.INTERCEPTION,
    EventType.RECOVERY,
    EventType.CLEARANCE,
    EventType.FOUL,
    EventType.CARD,
}

TEAM_FACTS = [
    ("possession_pct", "Possession", "%"),
    ("shots", "Shots", ""),
    ("shots_on_target", "Shots on target", ""),
    ("final_third_entries", "Final-third entries", ""),
    ("high_recoveries", "High recoveries", ""),
    ("xg", "Synthetic xG", ""),
    ("pass_accuracy", "Pass accuracy", "%"),
]


def allowed_names(meta: MatchMeta) -> list[str]:
    names = (
        [t.name for t in meta.teams] + [t.short_name for t in meta.teams] + [t.team_id for t in meta.teams]
    )
    names += [p.name for squad in meta.squads.values() for p in squad]
    return sorted(set(names))


def team_facts(stats: TeamStats, team_name: str, suffix: str) -> list[Fact]:
    out = []
    for key, label, unit in TEAM_FACTS:
        metric = getattr(stats, key)
        out.append(
            Fact(
                key=key,
                label=f"{label}{suffix}",
                team=team_name,
                value=metric.value,
                unit=unit,
                event_ids=metric.event_ids,
            )
        )
    return out


def _detection_summaries(
    detections: Sequence[Detection], meta: MatchMeta, t: int, since: int | None = None
) -> list[DetectionSummary]:
    names = {team.team_id: team.name for team in meta.teams}
    h2 = meta.second_half_start
    out = []
    for d in detections:
        if d.kind != "pattern" or d.end_second > t or (since is not None and d.end_second < since):
            continue
        since = display_clock(max(0, d.start_second), 1 if d.start_second < h2 else 2, h2)[0]
        out.append(
            DetectionSummary(
                pattern=d.pattern, team=names.get(d.team_id or ""), since_minute=since, minute=d.minute
            )
        )
    return out


def build_factpack(
    state: MatchState, detection: Detection, meta: MatchMeta, detections: Sequence[Detection]
) -> FactPack:
    t = detection.end_second
    received = [e for e in state.events if e.match_second <= t]
    names = {team.team_id: team.name for team in meta.teams}
    players = meta.player_names()
    team_id = detection.team_id
    opp_id = next((x.team_id for x in meta.teams if x.team_id != team_id), None) if team_id else None

    stats = window_stats(received, t, "last_5", state.teams, with_players=False)
    facts: list[Fact] = []
    for tid in [x for x in (team_id, opp_id) if x] or state.teams:
        facts += team_facts(stats.teams[tid], names[tid], " (last 5)")
    facts.append(Fact(key="window_minutes", label="Window length", value=WINDOW_MINUTES, unit="min"))

    ev = detection.evidence
    if detection.pattern == "momentum_shift":
        for key, label in (
            ("attacking_index_last_5", "Attacking index (last 5)"),
            ("attacking_index_previous_5", "Attacking index (previous 5)"),
        ):
            for tid, value in ev[key].items():
                facts.append(Fact(key=key, label=label, team=names[tid], value=value))
    elif detection.pattern == "high_press_sequence":
        facts.append(
            Fact(
                key="high_recoveries_window",
                label="High recoveries in the press window",
                team=names[team_id or ""],
                value=ev["high_recoveries_last_180s"],
                event_ids=detection.event_ids,
            )
        )
        facts.append(Fact(key="press_window_seconds", label="Press window", value=180, unit="s"))
    elif detection.pattern == "big_chance":
        facts.append(
            Fact(
                key="shot_xg",
                label="Shot synthetic xG",
                team=names[team_id or ""],
                value=ev["xg"],
                event_ids=detection.event_ids,
            )
        )

    goal_ids = {e.event_id for e in received if e.event_type == EventType.GOAL}
    after = {names[k]: int(m.value or 0) for k, m in score_at(received, t, state.teams).items()}
    before = dict(after)
    if detection.pattern == "goal" and team_id:
        before[names[team_id]] -= 1

    recent = [e for e in received if e.event_type in NOTABLE][-RECENT_EVENTS:]
    player_id = ev.get("player_id") if isinstance(ev, dict) else None
    trigger = Trigger(
        detection_id=detection.detection_id,
        type=detection.pattern,
        kind=detection.kind,
        minute=detection.minute,
        second=detection.second,
        match_second=t,
        team=names.get(team_id or ""),
        opponent=names.get(opp_id or ""),
        player=players.get(player_id or ""),
        event_ids=detection.event_ids,
    )
    citable = set(detection.event_ids) | {e.event_id for e in recent} | goal_ids
    for f in facts:
        citable |= set(f.event_ids)
    seconds = {e.event_id: e.match_second for e in received if e.event_id in citable}
    return FactPack(
        match_id=detection.match_id,
        trigger=trigger,
        score_before=before,
        score_after=after,
        facts=facts,
        detections=_detection_summaries(detections, meta, t, since=t - ACTIVE_DETECTION_SECONDS),
        recent_events=[
            RecentEvent(
                event_id=e.event_id,
                minute=e.minute,
                type=e.event_type.value,
                team=names[e.team_id],
                player=players.get(e.player_id or ""),
                outcome=e.outcome,
            )
            for e in recent
        ],
        allowed_names=allowed_names(meta),
        event_seconds=seconds,
        clock_second=t,
    )


def build_recap_factpack(
    state: MatchState, meta: MatchMeta, detections: Sequence[Detection], scope: str, t: int
) -> RecapFactPack:
    """Everything up to `t` (never later): full-match stats, key moments and detected patterns."""
    received = [e for e in state.events if e.match_second <= t]
    names = {team.team_id: team.name for team in meta.teams}
    players = meta.player_names()
    stats = window_stats_between(received, None, t, state.teams, window="full", with_players=False)
    facts: list[Fact] = []
    for tid in state.teams:
        facts += team_facts(stats.teams[tid], names[tid], "")
    moments = [
        RecapMoment(
            minute=d.minute,
            type=d.pattern,
            team=names.get(d.team_id or ""),
            player=players.get(str(d.evidence.get("player_id", "")), None),
            event_ids=d.event_ids,
        )
        for d in detections
        if d.kind == "key_moment" and d.pattern in ("goal", "big_chance", "card") and d.end_second <= t
    ]
    last = received[-1] if received else None
    minute = display_clock(t, last.period if last else 1, meta.second_half_start)[0]
    citable = {i for m in moments for i in m.event_ids} | {i for f in facts for i in f.event_ids}
    return RecapFactPack(
        match_id=meta.match_id,
        scope=scope,
        minute=minute,
        clock_second=t,
        score={names[k]: int(m.value or 0) for k, m in score_at(received, t, state.teams).items()},
        home=names[meta.home_team_id],
        away=names[meta.away_team_id],
        key_moments=moments,
        detections=_detection_summaries(detections, meta, t),
        facts=facts,
        allowed_names=allowed_names(meta),
        event_seconds={e.event_id: e.match_second for e in received if e.event_id in citable},
    )
