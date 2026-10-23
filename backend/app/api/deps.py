"""Shared request dependencies."""

from fastapi import Request

from app.api.errors import ApiError
from app.events.simulator import Simulator
from app.services.registry import MatchRegistry, UnknownMatch
from app.services.store import MatchStore


def registry(request: Request) -> MatchRegistry:
    return request.app.state.registry


def store(request: Request) -> MatchStore:
    return request.app.state.store


async def get_sim(match_id: str, request: Request) -> Simulator:
    try:
        return await registry(request).get(match_id)
    except UnknownMatch:
        raise ApiError(404, "match_not_found", f"No match with id {match_id!r}") from None
