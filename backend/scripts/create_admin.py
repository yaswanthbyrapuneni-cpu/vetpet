import argparse

from sqlalchemy import select

from app.api.routes.auth import normalized_mobile_number
from app.db.session import SessionLocal
from app.models.domain import User, UserRole


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Madina Vet Pet administrator")
    parser.add_argument("--mobile-number", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()

    mobile_number = normalized_mobile_number(args.mobile_number)
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.mobile_number == mobile_number)) is not None:
            raise SystemExit("A user with this mobile number already exists")
        admin = User(
            mobile_number=mobile_number,
            full_name=args.name.strip(),
            role=UserRole.ADMIN,
        )
        db.add(admin)
        db.commit()
        print(f"Administrator created: {mobile_number}")


if __name__ == "__main__":
    main()


