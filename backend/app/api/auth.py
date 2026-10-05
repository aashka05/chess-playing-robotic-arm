from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from sqlalchemy import delete, func, select, update

from app.api.deps import DB, AdminUser, CurrentUser
from app.core.config import get_settings
from app.core.email import send_password_reset
from app.core.security import (
    create_access_token,
    hash_password,
    hash_reset_token,
    new_reset_token,
    verify_password,
)
from app.models import PasswordResetToken, User
from app.models.enums import Role
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenOut,
    UserOut,
)

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


@router.post("/forgot-password", status_code=202)
async def forgot_password(body: ForgotPasswordRequest, db: DB, background: BackgroundTasks) -> dict:
    """Email a single-use reset code. Same answer whether or not the account exists."""
    user = await db.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    if user is not None:
        token = new_reset_token()
        # Only the newest code works.
        await db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.user_id))
        db.add(PasswordResetToken(
            user_id=user.user_id,
            token_hash=hash_reset_token(token),
            expires_at=datetime.now(UTC) + timedelta(minutes=get_settings().password_reset_expire_minutes),
        ))
        await db.commit()
        background.add_task(send_password_reset, user.email, token)
    return {"detail": "If an account exists for this email, a reset code has been sent to it."}


@router.post("/reset-password", status_code=204)
async def reset_password(body: ResetPasswordRequest, db: DB) -> None:
    now = datetime.now(UTC)
    # Mark the token used in the same statement that checks it, so it works exactly once.
    user_id = await db.scalar(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.token_hash == hash_reset_token(body.token.strip()),
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
        .values(used_at=now)
        .returning(PasswordResetToken.user_id)
    )
    user = await db.get(User, user_id) if user_id is not None else None
    if user is None:
        await db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset code is invalid or has expired. Request a new one.")
    user.password_hash = hash_password(body.new_password)
    await db.commit()


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user


@router.get("/users", response_model=list[UserOut])
async def list_users(_: AdminUser, db: DB) -> list[User]:
    return list(await db.scalars(select(User).order_by(User.user_id)))
