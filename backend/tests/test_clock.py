import chess
import pytest

from app.services.clock_service import ChessClock


class FakeTime:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


@pytest.fixture
def ft():
    return FakeTime()


def test_initial_state(ft):
    clock = ChessClock(60_000, 2_000, now=ft)
    assert clock.running is None
    assert clock.remaining_ms(chess.WHITE) == 60_000
    ft.advance(10)
    assert clock.remaining_ms(chess.WHITE) == 60_000  # not running


def test_running_side_counts_down(ft):
    clock = ChessClock(60_000, 0, now=ft)
    clock.start(chess.WHITE)
    ft.advance(5)
    assert clock.remaining_ms(chess.WHITE) == 55_000
    assert clock.remaining_ms(chess.BLACK) == 60_000


def test_switch_and_increment(ft):
    clock = ChessClock(60_000, 3_000, now=ft)
    clock.start(chess.WHITE)
    ft.advance(10)
    clock.start(chess.BLACK)  # implicitly stops white
    clock.add_increment(chess.WHITE)
    ft.advance(4)
    assert clock.remaining_ms(chess.WHITE) == 53_000
    assert clock.remaining_ms(chess.BLACK) == 56_000
    assert clock.running == chess.BLACK


def test_stop_returns_elapsed(ft):
    clock = ChessClock(60_000, 0, now=ft)
    clock.start(chess.BLACK)
    ft.advance(1.5)
    assert clock.stop() == 1500
    assert clock.running is None
    assert clock.stop() == 0


def test_flag(ft):
    clock = ChessClock(1_000, 0, now=ft)
    clock.start(chess.WHITE)
    ft.advance(0.5)
    assert clock.flagged() is None
    ft.advance(0.6)
    assert clock.flagged() == chess.WHITE
    assert clock.remaining_ms(chess.WHITE) == 0  # never negative


def test_refund(ft):
    clock = ChessClock(60_000, 0, now=ft)
    clock.start(chess.BLACK)
    before = clock.remaining_ms(chess.BLACK)
    ft.advance(7)
    clock.set_remaining(chess.BLACK, before)
    assert clock.remaining_ms(chess.BLACK) == 60_000
    ft.advance(1)
    assert clock.remaining_ms(chess.BLACK) == 59_000


def test_snapshot(ft):
    clock = ChessClock(300_000, 5_000, now=ft)
    clock.start(chess.BLACK)
    ft.advance(1)
    assert clock.snapshot() == {
        "white_ms": 300_000,
        "black_ms": 299_000,
        "running": "black",
        "base_ms": 300_000,
        "increment_ms": 5_000,
    }
