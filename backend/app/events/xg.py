"""Synthetic xG: a simple, documented distance/angle logistic formula. Not a trained or validated model.

    angle = angle subtended by the goal posts (7.32 m wide) from the shot location, in radians
    distance = metres from the shot location to the centre of the goal (105, 34)
    xg = 1 / (1 + exp(-(-0.915 + 1.5 * angle - 0.12 * distance))), clamped to [0.01, 0.95], 2 decimals

Rough reference points (central shots): 6 m ≈ 0.50, 8 m ≈ 0.36, 11 m ≈ 0.23, 18 m ≈ 0.08, 25 m ≈ 0.03.
"""

import math

GOAL_X = 105.0
GOAL_Y = 34.0
HALF_GOAL_WIDTH = 3.66

INTERCEPT = -0.915
ANGLE_WEIGHT = 1.5
DISTANCE_WEIGHT = -0.12


def synthetic_xg(x: float, y: float) -> float:
    dx = GOAL_X - x
    distance = math.hypot(dx, GOAL_Y - y)
    angle = abs(math.atan2(GOAL_Y + HALF_GOAL_WIDTH - y, dx) - math.atan2(GOAL_Y - HALF_GOAL_WIDTH - y, dx))
    z = INTERCEPT + ANGLE_WEIGHT * angle + DISTANCE_WEIGHT * distance
    return round(min(0.95, max(0.01, 1.0 / (1.0 + math.exp(-z)))), 2)
