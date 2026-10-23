import asyncio


class FakeClock:
    """Wall time that only moves when someone sleeps. `sleep` yields to the event loop so tasks interleave."""

    def __init__(self) -> None:
        self.t = 0.0

    def now(self) -> float:
        return self.t

    async def sleep(self, seconds: float) -> None:
        self.t += seconds
        await asyncio.sleep(0)

    async def run_for(self, seconds: float, step: float = 0.1) -> None:
        """Let `seconds` of fake wall time pass while background tasks run."""
        end = self.t + seconds
        while self.t < end - 1e-9:
            await asyncio.sleep(0)
