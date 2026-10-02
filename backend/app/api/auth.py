from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import DB, AdminUser, CurrentUser
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.models.enums import Role
from app.schemas.auth import LoginRequest, RegisterRequest, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _token(user: User) -> TokenOut:
    return TokenOut(access_token=create_access_token(user.user_id, user.role), user=UserOut.model_validate(user))


@router.post("/register", response_model=TokenOut, status_code=201)
async def register(body: RegisterRequest, db: DB) -> TokenOut:
    email = body.email.lower()
    if await db.scalar(select(User).where(func.lower(User.email) == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    user = User(username=body.username, email=email, password_hash=hash_password(body.password), role=Role.client)
    db.add(user)
    await db.commit()
    return _token(user)


@router.post("/login", response_model=TokenOut)
async def login(body: LoginRequest, db: DB) -> TokenOut:
    user = await db.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")
    return _token(user)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user


@router.get("/users", response_model=list[UserOut])
async def list_users(_: AdminUser, db: DB) -> list[User]:
    return list(await db.scalars(select(User).order_by(User.user_id)))
