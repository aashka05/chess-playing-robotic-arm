"""The authoritative session/game state machine.

A session starts in SETUP_EMPTY when the user taps "Play New Game" and
ends in GAME_OVER. Only the transitions listed in TRANSITIONS are legal;
anything else raises InvalidTransition so a bug (or a double tap in the
app) can never skip a step such as move detection.
"""

from enum import StrEnum


class GameState(StrEnum):
    SETUP_EMPTY = "SETUP_EMPTY"
    SETUP_PIECES = "SETUP_PIECES"
    VERIFY = "VERIFY"
    COLOR_SELECT = "COLOR_SELECT"
    HUMAN_TURN = "HUMAN_TURN"
    DETECTING = "DETECTING"
    ENGINE_THINKING = "ENGINE_THINKING"
    ARM_EXECUTING = "ARM_EXECUTING"
    GAME_OVER = "GAME_OVER"


S = GameState

SETUP_STATES = frozenset({S.SETUP_EMPTY, S.SETUP_PIECES, S.VERIFY, S.COLOR_SELECT})
PLAYING_STATES = frozenset({S.HUMAN_TURN, S.DETECTING, S.ENGINE_THINKING, S.ARM_EXECUTING})

TRANSITIONS: dict[GameState, frozenset[GameState]] = {
    # Empty board photographed and rectified.
    S.SETUP_EMPTY: frozenset({S.SETUP_PIECES}),
    # User pressed OK after setting up the pieces.
    S.SETUP_PIECES: frozenset({S.VERIFY}),
    # Wrong position -> back to SETUP_PIECES; correct -> COLOR_SELECT.
    S.VERIFY: frozenset({S.SETUP_PIECES, S.COLOR_SELECT}),
    # Start: White -> human moves first; Black -> engine moves first.
    S.COLOR_SELECT: frozenset({S.HUMAN_TURN, S.ENGINE_THINKING}),
    # Clock pressed -> detect; or resign/timeout/abort.
    S.HUMAN_TURN: frozenset({S.DETECTING, S.GAME_OVER}),
    # Not recognized -> back to HUMAN_TURN; recognized -> engine (or game over).
    S.DETECTING: frozenset({S.HUMAN_TURN, S.ENGINE_THINKING, S.GAME_OVER}),
    S.ENGINE_THINKING: frozenset({S.ARM_EXECUTING, S.GAME_OVER}),
    # Arm finished -> human's turn, or the robot's move ended the game.
    S.ARM_EXECUTING: frozenset({S.HUMAN_TURN, S.GAME_OVER}),
    S.GAME_OVER: frozenset(),
}


class InvalidTransition(Exception):
    def __init__(self, current: GameState, target: GameState):
        super().__init__(f"Cannot go from {current} to {target}")
        self.current = current
        self.target = target


class StateMachine:
    def __init__(self, initial: GameState = S.SETUP_EMPTY):
        self._state = initial
        self.history: list[GameState] = [initial]

    @property
    def state(self) -> GameState:
        return self._state

    def can(self, target: GameState) -> bool:
        return target in TRANSITIONS[self._state]

    def transition(self, target: GameState) -> GameState:
        if not self.can(target):
            raise InvalidTransition(self._state, target)
        self._state = target
        self.history.append(target)
        return target

    def require(self, *states: GameState) -> None:
        """Raise InvalidTransition-like error if not currently in one of `states`."""
        if self._state not in states:
            raise WrongState(self._state, states)

    @property
    def is_setup(self) -> bool:
        return self._state in SETUP_STATES

    @property
    def is_playing(self) -> bool:
        return self._state in PLAYING_STATES

    @property
    def is_over(self) -> bool:
        return self._state == S.GAME_OVER


class WrongState(Exception):
    def __init__(self, current: GameState, expected: tuple[GameState, ...]):
        names = ", ".join(expected)
        super().__init__(f"Action not allowed in state {current} (expected {names})")
        self.current = current
