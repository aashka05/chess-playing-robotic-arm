import pytest

from app.services.state_machine import GameState as S
from app.services.state_machine import InvalidTransition, StateMachine, WrongState


def test_happy_path_user_white():
    sm = StateMachine()
    for state in [S.SETUP_PIECES, S.VERIFY, S.COLOR_SELECT, S.HUMAN_TURN, S.DETECTING,
                  S.ENGINE_THINKING, S.ARM_EXECUTING, S.HUMAN_TURN, S.GAME_OVER]:
        sm.transition(state)
    assert sm.is_over


def test_user_black_starts_with_engine():
    sm = StateMachine(S.COLOR_SELECT)
    sm.transition(S.ENGINE_THINKING)
    sm.transition(S.ARM_EXECUTING)
    sm.transition(S.HUMAN_TURN)
    assert sm.state == S.HUMAN_TURN


def test_verification_loop():
    sm = StateMachine(S.SETUP_PIECES)
    sm.transition(S.VERIFY)
    sm.transition(S.SETUP_PIECES)  # wrong position
    sm.transition(S.VERIFY)
    sm.transition(S.COLOR_SELECT)
    assert sm.history == [S.SETUP_PIECES, S.VERIFY, S.SETUP_PIECES, S.VERIFY, S.COLOR_SELECT]


def test_unrecognized_move_returns_to_human_turn():
    sm = StateMachine(S.DETECTING)
    sm.transition(S.HUMAN_TURN)
    assert sm.state == S.HUMAN_TURN


@pytest.mark.parametrize(
    "start,target",
    [
        (S.SETUP_EMPTY, S.COLOR_SELECT),   # can't skip verification
        (S.SETUP_PIECES, S.HUMAN_TURN),
        (S.HUMAN_TURN, S.ENGINE_THINKING),  # can't skip detection
        (S.DETECTING, S.ARM_EXECUTING),
        (S.ENGINE_THINKING, S.HUMAN_TURN),  # arm must execute the reply
        (S.GAME_OVER, S.HUMAN_TURN),
        (S.COLOR_SELECT, S.GAME_OVER),
    ],
)
def test_illegal_transitions(start, target):
    sm = StateMachine(start)
    with pytest.raises(InvalidTransition):
        sm.transition(target)
    assert sm.state == start


@pytest.mark.parametrize("state", [S.HUMAN_TURN, S.DETECTING, S.ENGINE_THINKING, S.ARM_EXECUTING])
def test_game_can_end_from_any_playing_state(state):
    sm = StateMachine(state)
    sm.transition(S.GAME_OVER)
    assert sm.is_over


def test_require():
    sm = StateMachine(S.DETECTING)
    sm.require(S.DETECTING, S.HUMAN_TURN)
    with pytest.raises(WrongState):
        sm.require(S.HUMAN_TURN)


def test_flags():
    assert StateMachine(S.VERIFY).is_setup
    assert StateMachine(S.ARM_EXECUTING).is_playing
    assert not StateMachine(S.GAME_OVER).is_playing
