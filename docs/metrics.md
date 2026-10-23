# Metric definitions

Every number InsideMatch shows is computed by code from structured events (`backend/app/analytics/`). No language
model computes, estimates or fills in a statistic. Each metric function returns its **value and the event IDs that
produced it**, so any number can be traced back to events ("Evidence" in the UI).

These definitions are enforced twice: by hand-worked fixtures in `backend/tests/unit/test_analytics.py`, and by an
independent, deliberately simple implementation (`scripts/compute_expected_stats.py`) that the fast engine must
match exactly at 15', 45', 69' and 90' of `demo_01` (`backend/tests/unit/test_expected_stats.py`).

## Conventions

- **Pitch:** 105 × 68 m. Coordinates are normalized so the acting team always attacks toward x = 105.
- **Final third / high region:** x ≥ 70.
- **Clock:** `match_second` is continuous across halves (2nd half starts at 2700 + 1st-half stoppage).
- **Windows** end at the current replay clock `t`: `last_5` = (t − 300, t], `last_10` = (t − 600, t],
  `full` = [kickoff, t]. The start is exclusive and the end inclusive: an event exactly at t − 300 is not in
  `last_5`; an event exactly at t is.
- **Only received events count.** Nothing after the replay clock is ever used.
- **Percentages** are whole numbers rounded half up (12.5 → 13). When the denominator is 0 the value is `None`,
  shown as "n/a".

## Team metrics

| Metric | Definition |
|---|---|
| Possession seconds | Control runs from an event to the next event **in the same `possession_id`** and is credited to the first event's `possession_team_id`. Not credited: intervals that start with an out-of-play event (`in_play = false`), intervals with no team in control (`possession_team_id = null`, e.g. a loose ball after an incomplete pass or clearance), and the transition interval that ends in a change of possession. Intervals are clipped to the window. Only intervals closed by an event at or before `t` count. |
| Possession % | Team possession seconds ÷ total assigned possession seconds in the window × 100. *Worked example: NBR 213 s, RVA 87 s → total 300 s → NBR 71 %, RVA 29 %.* `None` if no time is assigned. |
| Shots | Unique `shot` events. A `goal` event linked to its shot is **not** a second shot. |
| Shots on target | Shots with outcome `saved` or `goal`. |
| Synthetic xG | Sum of the shots' synthetic xG, rounded to 2 decimals. xG comes from a documented distance/angle formula (`backend/app/events/xg.py`), not a trained model. |
| Passes attempted / completed | `pass` events / those with outcome `complete`. |
| Pass accuracy | Completed ÷ attempted × 100, or `None` ("n/a") when no passes were attempted. |
| Final-third entry | A completed `pass` or a `carry` with `x < 70` and `end_x ≥ 70`. Actions that start inside the final third do not count. |
| Recoveries (ball wins) | `recovery`, `interception`, or `tackle` with outcome `won`. |
| High recovery | A ball win with `x ≥ 70` (in the opponent's defensive third). |

## Player metrics

Computed over the player's own events in the window: passes attempted, completed and accuracy, shots, synthetic
xG, recoveries (ball wins) and final-third entries, as above.

**Involvement** is the count of a player's recorded on-ball actions: `kickoff`, `pass`, `carry`, `shot`, `tackle`,
`interception`, `recovery`, `clearance`. It excludes `pressure` (off the ball), `foul`, `card`, `substitution`,
`out_of_play` and `goal` (already counted as the shot). It is **not** a count of touches and is never called that.

## Score

The score at time `t` counts `goal` events at or before `t`.

## Checkpoints in `demo_01.expected_stats.json`

15' = 900 s and 45' = 2700 s (1st-half clock, before stoppage); 69' = 2nd-half start + 24 min and
90' = 2nd-half start + 45 min (the 2nd-half display clock restarts at 45:00). The 69' checkpoint (69:00) falls
just before Northbridge's 69:07 equaliser, so the score there is 0–1.
