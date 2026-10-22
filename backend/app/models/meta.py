"""Match metadata: `data/matches/{match_id}.meta.json`. Clubs and players are fictional."""

from pydantic import BaseModel, ConfigDict


class PlayerMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player_id: str
    name: str
    shirt_number: int
    position: str  # GK, RB, CB, LB, DM, CM, AM, RW, LW, ST
    starter: bool


class TeamMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team_id: str
    name: str
    short_name: str
    primary_color: str
    secondary_color: str
    formation: str


class PeriodMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: int
    start_second: int
    end_second: int


class MatchMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_id: str
    competition: str
    venue: str
    kickoff: str  # ISO 8601
    seed: int
    home_team_id: str
    away_team_id: str
    teams: list[TeamMeta]
    squads: dict[str, list[PlayerMeta]]
    periods: list[PeriodMeta]
    final_score: dict[str, int]

    def team(self, team_id: str) -> TeamMeta:
        return next(t for t in self.teams if t.team_id == team_id)

    def player_names(self) -> dict[str, str]:
        return {p.player_id: p.name for squad in self.squads.values() for p in squad}

    @property
    def second_half_start(self) -> int:
        return next(p.start_second for p in self.periods if p.period == 2)
