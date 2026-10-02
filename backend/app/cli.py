"""Admin helpers.  Usage:
    python -m app.cli create-admin --email admin@example.com --username admin --password secret
"""

import argparse
import asyncio

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import User
from app.models.enums import Role


async def create_admin(email: str, username: str, password: str) -> None:
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == email.lower()))
        if user is None:
            user = User(email=email.lower(), username=username, password_hash=hash_password(password))
            db.add(user)
        user.role = Role.admin
        user.password_hash = hash_password(password)
        await db.commit()
        print(f"Admin ready: {user.email} (id {user.user_id})")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    admin = sub.add_parser("create-admin")
    admin.add_argument("--email", required=True)
    admin.add_argument("--username", required=True)
    admin.add_argument("--password", required=True)
    args = parser.parse_args()
    if args.command == "create-admin":
        asyncio.run(create_admin(args.email, args.username, args.password))


if __name__ == "__main__":
    main()
