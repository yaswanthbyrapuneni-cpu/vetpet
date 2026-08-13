import argparse

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.domain import User, UserRole


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a VetPet Connect administrator")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    if len(args.password) < 12:
        raise SystemExit("Administrator passwords must contain at least 12 characters")

    email = args.email.strip().lower()
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)) is not None:
            raise SystemExit("A user with this email already exists")
        admin = User(
            email=email,
            full_name=args.name.strip(),
            password_hash=hash_password(args.password),
            role=UserRole.ADMIN,
            is_email_verified=True,
        )
        db.add(admin)
        db.commit()
        print(f"Administrator created: {email}")


if __name__ == "__main__":
    main()


