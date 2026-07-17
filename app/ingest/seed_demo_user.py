"""Create (or reset) the demo login used for showcasing FundRadar.

    Email:    demo@fundradar.com
    Password: demo1234

Safe to run repeatedly — if the account exists its password is reset.
Run:  python -m app.ingest.seed_demo_user
"""
from __future__ import annotations

from sqlalchemy import select

from app.auth.models import User
from app.auth.security import hash_password
from app.db.database import SessionLocal, init_db

DEMO_EMAIL = "demo@fundradar.com"
DEMO_PASSWORD = "demo1234"


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if user:
            user.password_hash = hash_password(DEMO_PASSWORD)
            user.is_verified = True   # demo account is always loginable
            print(f"Demo account already existed — password reset. ({DEMO_EMAIL})")
        else:
            db.add(User(email=DEMO_EMAIL,
                        password_hash=hash_password(DEMO_PASSWORD),
                        full_name="Demo User",
                        is_verified=True))
            print(f"Demo account created: {DEMO_EMAIL} / {DEMO_PASSWORD}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
