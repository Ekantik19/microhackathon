"""Seeded synthetic match generator (INGEST).

    python -m app.events.generator --seed 42 --match-id demo_01

Writes `data/matches/{match_id}.jsonl` + `.meta.json` and `data/schema/event.schema.json`.
The same seed always produces byte-identical output.

How it works, in plain terms:
- A match is a sequence of possession chains. Background chains are random but steered by a per-segment table
  (`SEGMENTS`): how long each team keeps the ball, how far it progresses, how often it shoots, how often a
  turnover in the opponent's own third becomes a high recovery.
- The storyline (`demo_01.storyline.md`) is scripted as "beats" at exact clock times: goals, the high press,
  the sustained-pressure shots, the momentum swing, the big chance, cards and substitutions. Background play
  pauses for each beat, so the beats always happen when the storyline says.
- Background shots are never goals and are kept below xG 0.28, so the only goals and big chances are scripted.
"""

import argparse
import json
import math
import random
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings
from app.events.xg import synthetic_xg
from app.models.events import Event, EventType, display_clock
from app.models.meta import MatchMeta, PeriodMeta, PlayerMeta, TeamMeta

E = EventType
HOME, AWAY = "NBR", "RVA"
FIRST_HALF_STOPPAGE = 120
SECOND_HALF_STOPPAGE = 240
H1_END = 2700 + FIRST_HALF_STOPPAGE
H2_START = H1_END
FULL_TIME = H2_START + 2700 + SECOND_HALF_STOPPAGE
BACKGROUND_MAX_XG = 0.28
_KEEP = object()  # sentinel: keep the current possession team


def at(minute: int, second: int = 0) -> int:
    """Display clock → match_second. Minutes ≥ 45 refer to the 2nd half."""
    if minute < 45:
        return minute * 60 + second
    return H2_START + (minute - 45) * 60 + second


def other(team: str) -> str:
    return AWAY if team == HOME else HOME


def mirror(x: float, y: float) -> tuple[float, float]:
    """Switch a location between the two teams' attacking frames."""
    return 105.0 - x, 68.0 - y


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


# --- Fictional teams and squads ---------------------------------------------------------------------------

TEAMS = [
    TeamMeta(
        team_id=HOME,
        name="Northbridge FC",
        short_name="Northbridge",
        primary_color="#1B3A6B",
        secondary_color="#F2B705",
        formation="4-3-3",
    ),
    TeamMeta(
        team_id=AWAY,
        name="Riverside Athletic",
        short_name="Riverside",
        primary_color="#0F8B8D",
        secondary_color="#F4F1E8",
        formation="4-2-3-1",
    ),
]

# (shirt, name, position, starter)
SQUADS: dict[str, list[tuple[int, str, str, bool]]] = {
    HOME: [
        (1, "Elias Brandt", "GK", True),
        (2, "Marcus Holloway", "RB", True),
        (4, "Jonah Achterberg", "CB", True),
        (5, "Kofi Danso", "CB", True),
        (3, "Luca Ferrandi", "LB", True),
        (6, "Owen Prentice", "DM", True),
        (8, "Rafael Quintero", "CM", True),
        (10, "Sami Ilunga", "AM", True),
        (7, "Ilya Vossberg", "RW", True),
        (11, "Theo Marchetti", "LW", True),
        (9, "Tomas Reyes", "ST", True),
        (12, "Callum Ridley", "GK", False),
        (14, "Aaron Whitlock", "CM", False),
        (15, "Niko Saarinen", "RB", False),
        (17, "Jamal Okoro", "LW", False),
        (19, "Ben Castellanos", "CM", False),
    ],
    AWAY: [
        (1, "Viktor Lindqvist", "GK", True),
        (2, "Dario Mendes", "RB", True),
        (5, "Patrick Oyelaran", "CB", True),
        (6, "Hugo Delacorte", "CB", True),
        (3, "Finn Albrecht", "LB", True),
        (4, "Mateo Szabo", "DM", True),
        (8, "Kwabena Harlow", "CM", True),
        (10, "Leon Vasquez-Aldana", "AM", True),
        (7, "Ciaran Fennimore", "RW", True),
        (11, "Yusuf Brightwater", "LW", True),
        (9, "Andrei Kovalski", "ST", True),
        (13, "Joel Pemberton", "GK", False),
        (14, "Emil Rasmussen-Toft", "CM", False),
        (16, "Grady Nwosu", "LB", False),
        (18, "Santi Oberlin", "ST", False),
        (20, "Rory Castellane", "CM", False),
    ],
}

GROUP = {
    "GK": "GK",
    "RB": "DF",
    "CB": "DF",
    "LB": "DF",
    "DM": "MF",
    "CM": "MF",
    "AM": "MF",
    "RW": "FW",
    "LW": "FW",
    "ST": "FW",
}


def pid(team: str, shirt: int) -> str:
    return f"{team}_{shirt:02d}"


# --- Background tendencies per match segment --------------------------------------------------------------


@dataclass(frozen=True)
class Segment:
    period: int
    start: int  # display minute, inclusive
    end: int  # display minute, exclusive
    ctrl: tuple[float, float]  # (NBR, RVA) chain-length tendency, 0-1
    attack: tuple[float, float]  # forward progress per action, 0-1
    shot: tuple[float, float]  # P(shot | chain ends in the final third)
    press: tuple[float, float]  # P(a turnover in the opponent's own third becomes this team's high recovery)


SEGMENTS = [
    Segment(1, 0, 18, (0.55, 0.50), (0.18, 0.14), (0.12, 0.08), (0.08, 0.06)),
    Segment(1, 18, 40, (0.48, 0.55), (0.14, 0.20), (0.08, 0.10), (0.06, 0.10)),
    Segment(1, 40, 48, (0.40, 0.55), (0.12, 0.25), (0.05, 0.10), (0.05, 0.05)),
    Segment(2, 45, 55, (0.55, 0.48), (0.22, 0.15), (0.12, 0.08), (0.08, 0.06)),
    Segment(2, 55, 62, (0.65, 0.40), (0.40, 0.10), (0.20, 0.05), (0.10, 0.04)),
    Segment(2, 62, 70, (0.92, 0.12), (0.80, 0.10), (0.00, 0.00), (0.15, 0.00)),
    Segment(2, 70, 76, (0.45, 0.45), (0.15, 0.15), (0.00, 0.00), (0.05, 0.05)),
    Segment(2, 76, 80, (0.40, 0.60), (0.10, 0.50), (0.00, 0.00), (0.00, 0.00)),
    Segment(2, 80, 95, (0.42, 0.58), (0.12, 0.20), (0.05, 0.12), (0.04, 0.08)),
]


class MatchBuilder:
    def __init__(self, match_id: str, seed: int):
        self.match_id = match_id
        self.seed = seed
        self.rng = random.Random(seed)
        self.events: list[dict] = []
        self.t = 0
        self.period = 1
        self.possession_id = 0
        self.poss_team: str | None = None
        self.ball = (52.5, 34.0)  # in the possession team's attacking frame
        self.score = {HOME: 0, AWAY: 0}
        self.on_pitch = {
            team: [pid(team, s) for s, _, _, starter in squad if starter] for team, squad in SQUADS.items()
        }
        self.position = {pid(team, s): pos for team, squad in SQUADS.items() for s, _, pos, _ in squad}

    # --- low-level emission ---

    def emit(
        self,
        etype: EventType,
        team: str,
        player: str | None = None,
        *,
        x: float | None = None,
        y: float | None = None,
        end_x: float | None = None,
        end_y: float | None = None,
        outcome: str | None = None,
        recipient: str | None = None,
        xg: float | None = None,
        in_play: bool = True,
        related: list[str] | None = None,
        poss: object = _KEEP,
        dt: int = 0,
        when: int | None = None,
    ) -> str:
        if when is not None:
            if when < self.t:
                raise ValueError(f"scripted time {when} is before current clock {self.t}")
            self.t = when
        self.t += dt
        if player is not None and etype != E.SUBSTITUTION and player not in self.on_pitch[team]:
            raise ValueError(f"{player} is not on the pitch at {self.t}")
        new_poss = self.poss_team if poss is _KEEP else poss
        if new_poss != self.poss_team:
            self.possession_id += 1
            self.poss_team = new_poss  # type: ignore[assignment]
        minute, second = display_clock(self.t, self.period, H2_START)
        seq = len(self.events) + 1
        event_id = f"e{seq:05d}"
        self.events.append(
            {
                "match_id": self.match_id,
                "event_id": event_id,
                "seq": seq,
                "period": self.period,
                "match_second": self.t,
                "minute": minute,
                "second": second,
                "team_id": team,
                "player_id": player,
                "event_type": etype.value,
                "outcome": outcome,
                "x": _r(x),
                "y": _r(y),
                "end_x": _r(end_x),
                "end_y": _r(end_y),
                "possession_team_id": self.poss_team,
                "possession_id": self.possession_id,
                "recipient_id": recipient,
                "shot_outcome": outcome if etype == E.SHOT else None,
                "xg": xg,
                "under_pressure": False,
                "in_play": in_play,
                "related_event_ids": list(related or []),
            }
        )
        return event_id

    def pick(self, team: str, x: float, exclude: str | None = None) -> str:
        """Choose a plausible on-pitch outfield player for a ball location (in that team's frame)."""
        if x < 35:
            weights = {"DF": 5, "MF": 3, "FW": 1}
        elif x < 70:
            weights = {"DF": 2, "MF": 5, "FW": 2}
        else:
            weights = {"DF": 1, "MF": 4, "FW": 5}
        players = [p for p in self.on_pitch[team] if GROUP[self.position[p]] != "GK" and p != exclude]
        return self.rng.choices(players, weights=[weights[GROUP[self.position[p]]] for p in players])[0]

    def goalkeeper(self, team: str) -> str:
        return next(p for p in self.on_pitch[team] if self.position[p] == "GK")

    def segment(self) -> Segment:
        minute, _ = display_clock(self.t, self.period, H2_START)
        return next(s for s in SEGMENTS if s.period == self.period and s.start <= minute < s.end)

    def ball_is_live(self) -> bool:
        return bool(self.events) and self.events[-1]["in_play"]

    # --- shared building blocks ---

    def ball_out(
        self, team: str, x: float, y: float, restart_team: str, gap: tuple[int, int], limit: int
    ) -> None:
        """The ball leaves the pitch off `team`; `restart_team` restarts after a dead-ball gap."""
        dt = 1 if self.t < limit else 0
        self.emit(
            E.OUT_OF_PLAY,
            team,
            x=clamp(x, 0, 105),
            y=clamp(y, 0, 68),
            in_play=False,
            poss=restart_team,
            dt=dt,
        )
        self.ball = (x, y) if restart_team == team else mirror(x, y)
        self.t = min(self.t + self.rng.randint(*gap), max(self.t, limit))

    def prepare(self, team: str, when: int) -> None:
        """Make way for a scripted beat: stop live play so `team` can take the ball at `when`."""
        if self.ball_is_live() and self.poss_team != team:
            holder = self.poss_team or other(team)
            self.emit(E.OUT_OF_PLAY, holder, in_play=False, poss=team)
        elif not self.ball_is_live() and self.poss_team != team:
            self.possession_id += 1
            self.poss_team = team
        if when < self.t:
            raise ValueError(f"beat at {when} starts before current clock {self.t}")
        self.t = when

    def pass_(
        self, team: str, player: str, x: float, y: float, ex: float, ey: float, to: str, when: int
    ) -> str:
        return self.emit(
            E.PASS, team, player, x=x, y=y, end_x=ex, end_y=ey, outcome="complete", recipient=to, when=when
        )

    def shot(self, team: str, player: str, x: float, y: float, outcome: str, when: int) -> str:
        """A shot and its immediate aftermath (save, goal kick, block, or goal + kickoff)."""
        opp = other(team)
        shot_id = self.emit(E.SHOT, team, player, x=x, y=y, outcome=outcome, xg=synthetic_xg(x, y), when=when)
        if outcome == "goal":
            self.score[team] += 1
            self.emit(E.GOAL, team, player, x=105.0, y=34.0, in_play=False, related=[shot_id], poss=opp, dt=1)
            self.t += self.rng.randint(35, 45)
            self.emit(E.KICKOFF, opp, self.pick(opp, 52.5), x=52.5, y=34.0)
            self.ball = (52.5, 34.0)
        elif outcome == "saved":
            gx, gy = 3.0, clamp(68 - y + self.rng.uniform(-2, 2), 28, 40)
            self.emit(E.RECOVERY, opp, self.goalkeeper(opp), x=gx, y=gy, poss=opp, dt=2)
            self.ball = (gx, gy)
        elif outcome == "off_target":
            self.emit(E.OUT_OF_PLAY, team, x=105.0, y=clamp(y, 20, 48), in_play=False, poss=opp, dt=1)
            self.t += self.rng.randint(15, 25)
            self.ball = (6.0, 34.0)
        else:  # blocked → cleared, then picked up by the defending team
            cx, cy = mirror(min(x + 3, 103), y)
            self.emit(E.CLEARANCE, opp, self.pick(opp, cx), x=cx, y=cy, poss=None, dt=1)
            rx, ry = self.rng.uniform(30, 42), self.rng.uniform(15, 53)
            self.emit(E.RECOVERY, opp, self.pick(opp, rx), x=rx, y=ry, poss=opp, dt=3)
            self.ball = (rx, ry)
        return shot_id

    def win_ball(
        self,
        winner: str,
        how: EventType,
        loser_x: float,
        loser_y: float,
        seg: Segment,
        related: list[str],
        limit: int,
    ) -> None:
        """`winner` takes the ball where the other team lost it. In the opponent's own third this is a high
        recovery, which only happens with probability `seg.press`; otherwise the ball is put out of play."""
        wx, wy = mirror(loser_x, loser_y)
        if wx >= 70 and self.rng.random() >= seg.press[_idx(winner)]:
            loser = other(winner)
            self.ball_out(loser, loser_x, loser_y, restart_team=winner, gap=(5, 10), limit=limit)
            return
        player = self.pick(winner, wx)
        outcome = "won" if how == E.TACKLE else None
        self.emit(how, winner, player, x=wx, y=wy, outcome=outcome, poss=winner, related=related, dt=2)
        self.ball = (wx, wy)

    # --- background play ---

    def background_possession(self, limit: int) -> None:
        team = self.poss_team or HOME
        if self.poss_team is None:
            self.poss_team = team
        opp, i, seg, rng = other(team), _idx(team), self.segment(), self.rng
        x, y = self.ball
        player = self.pick(team, x)
        n_actions = rng.randint(1 + int(seg.ctrl[i] * 4), 2 + int(seg.ctrl[i] * 12))

        for _ in range(n_actions):
            if self.t >= limit - 14:  # worst case: pressure 2 s + pass 8 s + turnover 2 s
                if self.ball_is_live():
                    self.ball_out(team, x, y, restart_team=opp, gap=(5, 10), limit=limit)
                return
            pressure_id = None
            if rng.random() < 0.2:
                px, py = mirror(clamp(x + rng.uniform(-3, 3), 1, 104), clamp(y + rng.uniform(-3, 3), 1, 67))
                pressure_id = self.emit(E.PRESSURE, opp, self.pick(opp, px), x=px, y=py, dt=rng.randint(1, 2))
            if rng.random() < 0.03:  # foul: free kick to the team in possession
                fx, fy = mirror(x, y)
                self.emit(E.FOUL, opp, self.pick(opp, fx), x=fx, y=fy, in_play=False, poss=team, dt=1)
                self.t = min(self.t + rng.randint(10, 20), max(self.t, limit))
                continue

            nx = clamp(x + rng.gauss(3 + 9 * seg.attack[i], 9), 2, 103)
            ny = clamp(y + rng.gauss(0, 12), 2, 66)
            if x >= 85 and seg.attack[i] >= 0.6 and rng.random() < 0.4:
                # A dominant side recycles the ball out of a crowded box, then goes again.
                nx, ny = rng.uniform(55, 68), clamp(y + rng.gauss(0, 10), 5, 63)
            if rng.random() < 0.25:
                nx = clamp(x + rng.uniform(2, 12), 2, 103)
                ny = clamp(y + rng.uniform(-5, 5), 2, 66)
                self.emit(E.CARRY, team, player, x=x, y=y, end_x=nx, end_y=ny, dt=rng.randint(1, 3))
                x, y = nx, ny
                continue

            p_complete = 0.88 - (0.12 if pressure_id else 0) - (0.12 if nx >= 88 else 0)
            dt = 1 + int(math.hypot(nx - x, ny - y) / 15) + rng.randint(0, 1)
            if rng.random() < p_complete:
                receiver = self.pick(team, nx, exclude=player)
                self.emit(
                    E.PASS,
                    team,
                    player,
                    x=x,
                    y=y,
                    end_x=nx,
                    end_y=ny,
                    outcome="complete",
                    recipient=receiver,
                    dt=dt,
                )
                player, x, y = receiver, nx, ny
                continue
            self.emit(
                E.PASS, team, player, x=x, y=y, end_x=nx, end_y=ny, outcome="incomplete", poss=None, dt=dt
            )
            how = E.INTERCEPTION if rng.random() < 0.6 else E.RECOVERY
            self.win_ball(opp, how, nx, ny, seg, related=[pressure_id] if pressure_id else [], limit=limit)
            return

        self.ball = (x, y)
        if limit - self.t < 32:
            self.ball_out(team, x, y, restart_team=opp, gap=(5, 10), limit=limit)
        elif x >= 75 and rng.random() < seg.shot[i]:
            self.background_shot(team, player, x, y)
        elif rng.random() < 0.35:
            self.win_ball(opp, E.TACKLE, x, y, seg, related=[], limit=limit)
        elif x >= 70 and rng.random() < 0.5:
            cx, cy = mirror(x, y)
            self.emit(E.CLEARANCE, opp, self.pick(opp, cx), x=cx, y=cy, poss=None, dt=2)
            if rng.random() < 0.6:
                rx, ry = rng.uniform(25, 45), rng.uniform(5, 63)
                self.emit(E.RECOVERY, opp, self.pick(opp, rx), x=rx, y=ry, poss=opp, dt=3)
            else:
                rx, ry = rng.uniform(50, 65), rng.uniform(5, 63)
                self.emit(E.RECOVERY, team, self.pick(team, rx), x=rx, y=ry, poss=team, dt=3)
            self.ball = (rx, ry)
        else:
            self.ball_out(team, x, y, restart_team=opp, gap=(6, 12), limit=limit)

    def background_shot(self, team: str, player: str, x: float, y: float) -> None:
        rng = self.rng
        sx, sy = clamp(x + rng.uniform(0, 6), 78, 99), clamp(y + rng.gauss(0, 6), 14, 54)
        while synthetic_xg(sx, sy) >= BACKGROUND_MAX_XG:
            sx -= 2
        shooter = player if GROUP[self.position[player]] != "DF" else self.pick(team, sx)
        outcome = rng.choices(["saved", "off_target", "blocked"], weights=[35, 40, 25])[0]
        self.shot(team, shooter, sx, sy, outcome, when=self.t + rng.randint(2, 3))

    # --- scripted storyline beats (see data/matches/demo_01.storyline.md) ---

    def beat_rva_goal(self) -> None:
        """23': Riverside Athletic score. Kovalski finishes a move through Vasquez-Aldana (0-1)."""
        self.prepare(AWAY, at(22, 40))
        self.pass_(AWAY, "RVA_04", 38, 30, 50, 46, "RVA_02", at(22, 40))
        self.pass_(AWAY, "RVA_02", 50, 46, 60, 40, "RVA_10", at(22, 45))
        self.emit(E.CARRY, AWAY, "RVA_10", x=60, y=40, end_x=76, end_y=38, when=at(22, 50))
        self.emit(E.PRESSURE, HOME, "NBR_06", x=28, y=30, when=at(22, 53))
        self.pass_(AWAY, "RVA_10", 76, 38, 92, 35, "RVA_09", at(22, 56))
        self.shot(AWAY, "RVA_09", 93, 35, "goal", at(23, 4))

    def beat_rva_high_press(self) -> None:
        """40'-44': Riverside press Northbridge's build-up and win the ball high four times in ~160 s."""
        plays = [
            (at(40, 50), "NBR_04", "NBR_02", (12, 30), (20, 10), "RVA_11", "tackle"),
            (at(41, 40), "NBR_05", "NBR_03", (12, 38), (20, 58), "RVA_07", "recovery"),
            (at(42, 35), "NBR_04", "NBR_06", (14, 32), (24, 30), "RVA_10", "recovery"),
            (at(43, 25), "NBR_05", "NBR_02", (12, 30), (21, 9), "RVA_11", "tackle"),
        ]
        for k, (start, cb, receiver, (x0, y0), (x1, y1), presser, how) in enumerate(plays):
            self.prepare(HOME, start)
            self.pass_(HOME, cb, x0, y0, x1, y1, receiver, start)
            px, py = mirror(x1 + 1, y1)
            pressure_id = self.emit(E.PRESSURE, AWAY, presser, x=px, y=py, when=start + 3)
            if how == "tackle":
                wx, wy = mirror(x1 + 1, y1)
                self.emit(
                    E.TACKLE,
                    AWAY,
                    presser,
                    x=wx,
                    y=wy,
                    outcome="won",
                    poss=AWAY,
                    related=[pressure_id],
                    when=start + 5,
                )
            else:
                ex, ey = x1 + 9, clamp(y1 + 8, 2, 66)
                self.emit(
                    E.PASS,
                    HOME,
                    receiver,
                    x=x1,
                    y=y1,
                    end_x=ex,
                    end_y=ey,
                    outcome="incomplete",
                    poss=None,
                    when=start + 5,
                )
                wx, wy = mirror(ex, ey)
                self.emit(
                    E.RECOVERY, AWAY, "RVA_08", x=wx, y=wy, poss=AWAY, related=[pressure_id], when=start + 7
                )
            # The quick attack that follows the turnover.
            self.pass_(AWAY, "RVA_08" if how == "recovery" else presser, wx, wy, 90, 30, "RVA_09", self.t + 4)
            if k == 1:
                self.shot(AWAY, "RVA_09", 91, 30, "off_target", self.t + 3)
            else:
                self.emit(
                    E.PASS,
                    AWAY,
                    "RVA_09",
                    x=90,
                    y=30,
                    end_x=99,
                    end_y=20,
                    outcome="incomplete",
                    poss=None,
                    dt=3,
                )
                self.emit(E.RECOVERY, HOME, self.goalkeeper(HOME), x=5, y=46, poss=HOME, dt=2)
                self.ball = (5, 46)

    def beat_card(
        self, fouler: str, victim_team: str, victim: str, minute: int, second: int, x: float, y: float
    ) -> None:
        """A cynical foul stops an attack and earns a yellow card."""
        team = other(victim_team)
        when = at(minute, second)
        self.prepare(victim_team, when - 6)
        self.emit(E.CARRY, victim_team, victim, x=x - 8, y=y, end_x=x, end_y=y, when=when - 6)
        fx, fy = mirror(x, y)
        foul_id = self.emit(E.FOUL, team, fouler, x=fx, y=fy, in_play=False, poss=victim_team, when=when)
        self.emit(
            E.CARD,
            team,
            fouler,
            x=fx,
            y=fy,
            outcome="yellow",
            in_play=False,
            related=[foul_id],
            when=when + 25,
        )
        self.t += 15
        self.ball = (x, y)

    def beat_substitutions(self, team: str, minute: int, second: int, swaps: list[tuple[str, str]]) -> None:
        """Substitutions happen while the ball is dead."""
        when = at(minute, second)
        if self.ball_is_live():
            holder = self.poss_team or team
            self.emit(E.OUT_OF_PLAY, holder, in_play=False, poss=other(holder))
            self.ball = (30.0, 2.0)
        self.prepare(self.poss_team or other(team), when)
        for k, (off, on) in enumerate(swaps):
            self.emit(E.SUBSTITUTION, team, off, recipient=on, in_play=False, when=when + 10 * k)
            self.on_pitch[team] = [on if p == off else p for p in self.on_pitch[team]]
        self.t += 10

    def nbr_pressure_shot(
        self, minute: int, second: int, build: list[tuple[str, float, float]], outcome: str
    ) -> None:
        """One Northbridge attack during the 62'-70' spell: passes into the final third, then a shot."""
        shot_t = at(minute, second)
        start = shot_t - 5 * len(build)
        self.prepare(HOME, start)
        for k in range(len(build) - 1):
            (p, x, y), (q, nx, ny) = build[k], build[k + 1]
            self.pass_(HOME, p, x, y, nx, ny, q, start + 5 * k)
        shooter, sx, sy = build[-1]
        self.shot(HOME, shooter, sx + 1, sy, outcome, shot_t)

    def beat_nbr_goal(self) -> None:
        """68'-69': saved Reyes shot, a high recovery after pressing the goal kick, then Reyes scores (1-1)."""
        self.prepare(HOME, at(68, 1))
        self.pass_(HOME, "NBR_14", 58, 30, 64, 36, "NBR_10", at(68, 1))
        self.emit(E.CARRY, HOME, "NBR_10", x=64, y=36, end_x=78, end_y=34, when=at(68, 11))
        self.pass_(HOME, "NBR_10", 78, 34, 90, 37, "NBR_09", at(68, 14))
        self.shot(HOME, "NBR_09", 91, 37, "saved", at(68, 17))
        self.pass_(AWAY, "RVA_01", 3, 33, 18, 12, "RVA_03", at(68, 27))
        pressure_id = self.emit(E.PRESSURE, HOME, "NBR_07", x=86, y=56, when=at(68, 33))
        self.emit(
            E.PASS,
            AWAY,
            "RVA_03",
            x=19,
            y=12,
            end_x=30,
            end_y=20,
            outcome="incomplete",
            poss=None,
            when=at(68, 36),
        )
        self.emit(E.RECOVERY, HOME, "NBR_02", x=75, y=48, poss=HOME, related=[pressure_id], when=at(68, 41))
        self.pass_(HOME, "NBR_02", 75, 48, 82, 40, "NBR_10", at(68, 47))
        self.pass_(HOME, "NBR_10", 82, 40, 88, 24, "NBR_17", at(68, 55))
        self.pass_(HOME, "NBR_17", 88, 24, 93, 33, "NBR_09", at(69, 1))
        self.shot(HOME, "NBR_09", 94, 33, "goal", at(69, 6))

    def rva_surge_play(self, minute: int, second: int, kind: str) -> None:
        """Riverside's 76'-80' surge: high regains and shots that swing the momentum."""
        when = at(minute, second)
        if kind == "high_recovery":
            self.prepare(HOME, when - 6)
            self.pass_(HOME, "NBR_05", 20, 40, 27, 52, "NBR_03", when - 6)
            pressure_id = self.emit(E.PRESSURE, AWAY, "RVA_07", x=77, y=17, when=when - 3)
            self.emit(
                E.TACKLE,
                AWAY,
                "RVA_07",
                x=77,
                y=16,
                outcome="won",
                poss=AWAY,
                related=[pressure_id],
                when=when,
            )
            self.ball = (77, 16)
            return
        shooter, (sx, sy), outcome = {
            "shot_off": ("RVA_18", (88, 44), "off_target"),
            "shot_saved": ("RVA_09", (89, 30), "saved"),
            "shot_blocked": ("RVA_10", (85, 33), "blocked"),
        }[kind]
        self.prepare(AWAY, when - 16)
        self.pass_(AWAY, "RVA_04", 55, 34, 66, 24, "RVA_07", when - 16)
        self.emit(E.CARRY, AWAY, "RVA_07", x=66, y=24, end_x=79, end_y=20, when=when - 11)
        self.pass_(AWAY, "RVA_07", 79, 20, sx - 1, sy, shooter, when - 6)
        self.shot(AWAY, shooter, sx, sy, outcome, when)

    def beat_big_chance(self) -> None:
        """86': Oberlin is played clean through; Brandt saves (big chance, xG ≥ 0.30)."""
        self.prepare(AWAY, at(85, 55))
        self.pass_(AWAY, "RVA_04", 52, 34, 68, 30, "RVA_10", at(85, 55))
        self.pass_(AWAY, "RVA_10", 68, 30, 94, 33, "RVA_18", at(86, 2))
        self.emit(E.CARRY, AWAY, "RVA_18", x=94, y=33, end_x=96, end_y=33, when=at(86, 8))
        self.shot(AWAY, "RVA_18", 97, 33, "saved", at(86, 12))

    def beats(self) -> list[tuple[int, Callable[[], None]]]:
        b: list[tuple[int, Callable[[], None]]] = [
            (at(22, 40), self.beat_rva_goal),
            (at(35, 14), lambda: self.beat_card("NBR_06", AWAY, "RVA_10", 35, 20, 62, 40)),
            (at(40, 50), self.beat_rva_high_press),
            (at(52, 4), lambda: self.beat_card("RVA_04", HOME, "NBR_10", 52, 10, 66, 30)),
            (
                at(58, 0),
                lambda: self.beat_substitutions(HOME, 58, 0, [("NBR_08", "NBR_14"), ("NBR_11", "NBR_17")]),
            ),
            (at(61, 0), lambda: self.beat_substitutions(AWAY, 61, 0, [("RVA_11", "RVA_18")])),
            (
                at(63, 10),
                lambda: self.nbr_pressure_shot(
                    63, 25, [("NBR_06", 55, 34), ("NBR_14", 68, 22), ("NBR_17", 86, 14)], "off_target"
                ),
            ),
            (
                at(64, 45),
                lambda: self.nbr_pressure_shot(
                    65,
                    5,
                    [("NBR_05", 50, 40), ("NBR_10", 66, 34), ("NBR_07", 80, 50), ("NBR_10", 84, 36)],
                    "blocked",
                ),
            ),
            (
                at(66, 25),
                lambda: self.nbr_pressure_shot(
                    66, 40, [("NBR_14", 58, 30), ("NBR_10", 72, 36), ("NBR_09", 89, 30)], "saved"
                ),
            ),
            (at(68, 1), self.beat_nbr_goal),
            (at(72, 0), lambda: self.beat_substitutions(AWAY, 72, 0, [("RVA_08", "RVA_14")])),
            (at(76, 24), lambda: self.rva_surge_play(76, 40, "shot_off")),
            (at(77, 14), lambda: self.rva_surge_play(77, 20, "high_recovery")),
            (at(77, 34), lambda: self.rva_surge_play(77, 50, "shot_saved")),
            (at(78, 34), lambda: self.rva_surge_play(78, 40, "high_recovery")),
            (at(80, 30), lambda: self.beat_substitutions(AWAY, 80, 30, [("RVA_03", "RVA_16")])),
            (at(81, 30), lambda: self.beat_substitutions(HOME, 81, 30, [("NBR_02", "NBR_15")])),
            (at(85, 55), self.beat_big_chance),
        ]
        return sorted(b, key=lambda item: item[0])

    # --- the whole match ---

    def play_until(self, end_t: int, beats: list[tuple[int, Callable[[], None]]]) -> None:
        while True:
            next_beat = beats[0] if beats and beats[0][0] < end_t else None
            limit = next_beat[0] if next_beat else end_t
            while limit - self.t > 18:
                self.background_possession(limit)
            if next_beat is None:
                return
            beats.pop(0)
            next_beat[1]()

    def build(self) -> list[Event]:
        beats = self.beats()
        for period, kicking_team, start, end in [(1, HOME, 0, H1_END), (2, AWAY, H2_START, FULL_TIME)]:
            self.period = period
            self.emit(E.PERIOD_START, kicking_team, in_play=False, poss=None, when=start)
            self.emit(
                E.KICKOFF, kicking_team, self.pick(kicking_team, 52.5), x=52.5, y=34.0, poss=kicking_team
            )
            self.ball = (52.5, 34.0)
            self.play_until(end, beats)
            self.emit(E.PERIOD_END, self.poss_team or kicking_team, in_play=False, poss=None, when=end)
        if beats:
            raise ValueError(f"{len(beats)} beats were never played")
        mark_under_pressure(self.events)
        return [Event.model_validate(e) for e in self.events]

    def meta(self) -> MatchMeta:
        return MatchMeta(
            match_id=self.match_id,
            competition="Synthetic League",
            venue="Northbridge Park",
            kickoff="2026-10-24T15:00:00Z",
            seed=self.seed,
            home_team_id=HOME,
            away_team_id=AWAY,
            teams=TEAMS,
            squads={
                team: [
                    PlayerMeta(player_id=pid(team, s), name=n, shirt_number=s, position=pos, starter=st)
                    for s, n, pos, st in squad
                ]
                for team, squad in SQUADS.items()
            },
            periods=[
                PeriodMeta(period=1, start_second=0, end_second=H1_END),
                PeriodMeta(period=2, start_second=H2_START, end_second=FULL_TIME),
            ],
            final_score=dict(self.score),
        )


ON_BALL = {"pass", "carry", "shot", "clearance"}


def mark_under_pressure(events: list[dict]) -> None:
    """An on-ball action is under pressure if an opponent pressure event happened within the previous 3 s and
    10 m (locations compared in the same attacking frame)."""
    pressures: list[dict] = []
    for e in events:
        if e["event_type"] == "pressure":
            pressures.append(e)
            continue
        if e["event_type"] not in ON_BALL or e["x"] is None:
            continue
        for p in reversed(pressures):
            if e["match_second"] - p["match_second"] > 3:
                break
            if p["team_id"] == e["team_id"]:
                continue
            px, py = mirror(p["x"], p["y"])
            if math.hypot(px - e["x"], py - e["y"]) <= 10:
                e["under_pressure"] = True
                break


def _idx(team: str) -> int:
    return 0 if team == HOME else 1


def _r(v: float | None) -> float | None:
    return None if v is None else round(float(v), 1)


def to_jsonl(events: list[Event]) -> str:
    return "".join(json.dumps(e.model_dump(mode="json"), separators=(",", ":")) + "\n" for e in events)


def generate(match_id: str, seed: int) -> tuple[list[Event], MatchMeta]:
    builder = MatchBuilder(match_id, seed)
    events = builder.build()
    return events, builder.meta()


def write_outputs(match_id: str, seed: int, data_dir: Path) -> tuple[list[Event], MatchMeta]:
    events, meta = generate(match_id, seed)
    matches = data_dir / "matches"
    matches.mkdir(parents=True, exist_ok=True)
    (matches / f"{match_id}.jsonl").write_text(to_jsonl(events))
    (matches / f"{match_id}.meta.json").write_text(json.dumps(meta.model_dump(mode="json"), indent=2) + "\n")
    schema_dir = data_dir / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (schema_dir / "event.schema.json").write_text(json.dumps(Event.model_json_schema(), indent=2) + "\n")
    return events, meta


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a seeded synthetic football match.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--match-id", default="demo_01")
    parser.add_argument("--data-dir", type=Path, default=get_settings().data_dir)
    args = parser.parse_args()
    events, meta = write_outputs(args.match_id, args.seed, args.data_dir)
    print(
        f"{args.match_id}: {len(events)} events, final score {meta.final_score}, written to {args.data_dir}"
    )


if __name__ == "__main__":
    main()
