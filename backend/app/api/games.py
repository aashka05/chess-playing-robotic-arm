from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import DB, CurrentUser, Games
from app.core.config import get_settings
from app.models import Game, Move, User
from app.models.enums import Role
from app.schemas.game import DebugMoveRequest, GameDetail, GameSummary, StartGameRequest

router = APIRouter(prefix="/games", tags=["games"])


@router.post("", status_code=201)
async def start_game(body: StartGameRequest, user: CurrentUser, games: Games) -> dict:
    s = await games.start_game(
        user.user_id, body.color, body.difficulty, body.time_base_sec, body.time_increment_sec
    )
    return games.snapshot(s)


@router.get("", response_model=list[GameSummary])
async def list_games(user: CurrentUser, db: DB) -> list[GameSummary]:
    move_count = (
        select(Move.game_id, func.count(Move.move_id).label("n")).group_by(Move.game_id).subquery()
    )
    query = (
        select(Game, User.username, func.coalesce(move_count.c.n, 0))
        .join(User, User.user_id == Game.user_id)
        .outerjoin(move_count, move_count.c.game_id == Game.game_id)
        .order_by(Game.start_time.desc())
    )
    if user.role != Role.admin:
        query = query.where(Game.user_id == user.user_id)
    rows = (await db.execute(query)).all()
    return [
        GameSummary.model_validate(game).model_copy(update={"username": username, "move_count": n})
        for game, username, n in rows
    ]


@router.get("/active")
async def active_game(user: CurrentUser, games: Games) -> dict:
    game_id = games.active_game_id(user.user_id)
    if game_id is None:
        raise HTTPException(404, "No game in progress")
    return games.snapshot(games.game_session(game_id))


@router.get("/{game_id}", response_model=GameDetail)
async def get_game(game_id: int, user: CurrentUser, db: DB) -> GameDetail:
    game = await db.scalar(
        select(Game).where(Game.game_id == game_id).options(selectinload(Game.moves))
    )
    if game is None or (user.role != Role.admin and game.user_id != user.user_id):
        raise HTTPException(404, "Game not found")
    detail = GameDetail.model_validate(game)
    owner = await db.get(User, game.user_id)
    return detail.model_copy(update={"username": owner.username if owner else None, "move_count": len(game.moves)})


@router.get("/{game_id}/live")
async def live_state(game_id: int, user: CurrentUser, games: Games) -> dict:
    return games.snapshot(games.game_session(game_id, user.user_id))


@router.post("/{game_id}/press-clock", status_code=202)
async def press_clock(game_id: int, user: CurrentUser, games: Games) -> dict:
    await games.press_clock(user.user_id, game_id)
    return {"ok": True}


@router.post("/{game_id}/resign")
async def resign(game_id: int, user: CurrentUser, games: Games) -> dict:
    await games.resign(user.user_id, game_id)
    return {"ok": True}


@router.post("/{game_id}/abort")
async def abort(game_id: int, user: CurrentUser, games: Games) -> dict:
    await games.abort(user.user_id, game_id)
    return {"ok": True}


@router.post("/{game_id}/manual-done")
async def manual_done(game_id: int, user: CurrentUser, games: Games) -> dict:
    """The user finished a step the arm couldn't do (promotion piece, arm error)."""
    games.manual_action_done(user.user_id, game_id)
    return {"ok": True}


@router.post("/{game_id}/debug/human-move", status_code=202)
async def debug_human_move(game_id: int, body: DebugMoveRequest, user: CurrentUser, games: Games) -> dict:
    """Dev only: play a move as if the camera had detected it."""
    if not get_settings().debug_endpoints:
        raise HTTPException(404, "Not found")
    await games.press_clock(user.user_id, game_id, forced_uci=body.uci)
    return {"ok": True}
