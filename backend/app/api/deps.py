from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User
from app.models.enums import Role
from app.services.game_service import GameService

_bearer = HTTPBearer(auto_error=False)

DB = Annotated[AsyncSession, Depends(get_db)]


async def user_from_token(db: AsyncSession, token: str | None) -> User | None:
    if not token:
        return None
    user_id = decode_access_token(token)
    if user_id is None:
        return None
    return await db.get(User, user_id)


async def get_current_user(
    db: DB, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
) -> User:
    user = await user_from_token(db, credentials.credentials if credentials else None)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in", {"WWW-Authenticate": "Bearer"})
    return user


async def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != Role.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admins only")
    return user


def get_game_service(request: Request) -> GameService:
    return request.app.state.game_service


CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
Games = Annotated[GameService, Depends(get_game_service)]
