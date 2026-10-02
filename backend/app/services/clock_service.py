"""Authoritative chess clock.

The clock only knows about two sides (chess.WHITE / chess.BLACK). The game
service decides which side is running; the app merely renders the snapshot
and interpolates between updates.
"""

import time
from collections.abc import Callable

import chess


class ChessClock:
    def __init__(
        self,
        base_ms: int,
        increment_ms: int,
        now: Callable[[], float] = time.monotonic,
    ):
        self.base_ms = base_ms
        self.increment_ms = increment_ms
        self._now = now
        self._remaining: dict[chess.Color, float] = {chess.WHITE: base_ms, chess.BLACK: base_ms}
        self._running: chess.Color | None = None
        self._started_at = 0.0

    @property
    def running(self) -> chess.Color | None:
        return self._running

    def _elapsed_ms(self) -> float:
        return (self._now() - self._started_at) * 1000.0

    def remaining_exact(self, color: chess.Color) -> float:
        remaining = self._remaining[color]
        if self._running == color:
            remaining -= self._elapsed_ms()
        return remaining

    def remaining_ms(self, color: chess.Color) -> int:
        return max(0, int(self.remaining_exact(color)))

    def start(self, color: chess.Color) -> None:
        """Start `color`'s clock (stopping the other one if it was running)."""
        self.stop()
        self._running = color
        self._started_at = self._now()

    def stop(self) -> int:
        """Stop whichever clock is running. Returns the ms it ran for."""
        if self._running is None:
            return 0
        elapsed = self._elapsed_ms()
        self._remaining[self._running] -= elapsed
        self._running = None
        return int(elapsed)

    def add_increment(self, color: chess.Color) -> None:
        self._remaining[color] += self.increment_ms

    def set_remaining(self, color: chess.Color, ms: float) -> None:
        """Restore a side's time (used to refund an unrecognized move)."""
        if self._running == color:
            self._remaining[color] = ms + self._elapsed_ms()
        else:
            self._remaining[color] = ms

    def flagged(self) -> chess.Color | None:
        """The side whose time has run out, if any."""
        if self._running is not None and self.remaining_ms(self._running) <= 0:
            return self._running
        for color in (chess.WHITE, chess.BLACK):
            if self._remaining[color] <= 0:
                return color
        return None

    def snapshot(self) -> dict:
        running = None if self._running is None else chess.COLOR_NAMES[self._running]
        return {
            "white_ms": self.remaining_ms(chess.WHITE),
            "black_ms": self.remaining_ms(chess.BLACK),
            "running": running,
            "base_ms": self.base_ms,
            "increment_ms": self.increment_ms,
        }
