from enum import StrEnum


class Role(StrEnum):
    admin = "admin"
    client = "client"


class Difficulty(StrEnum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class GameResult(StrEnum):
    """Result from the human user's point of view."""

    win = "win"
    loss = "loss"
    draw = "draw"


class GameStatus(StrEnum):
    in_progress = "in_progress"
    finished = "finished"
    aborted = "aborted"


class TerminationReason(StrEnum):
    checkmate = "checkmate"
    stalemate = "stalemate"
    draw_rule = "draw_rule"
    resignation = "resignation"
    timeout = "timeout"
    aborted = "aborted"


class Color(StrEnum):
    white = "white"
    black = "black"


class Player(StrEnum):
    human = "human"
    robot = "robot"


class MotorStatus(StrEnum):
    success = "success"
    failure = "failure"
