import argparse

from sqlalchemy import select

from app.api.routes.auth import normalized_mobile_number
from app.db.session import SessionLocal
from app.models.domain import DoctorProfile, User, UserRole, VerificationStatus, utc_now


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the single verified doctor account")
    parser.add_argument("--mobile-number", required=True)
    parser.add_argument("--name", default="Dr. Madina Prasadrao")
    parser.add_argument("--license-number", default="MADINA-VET-0001")
    parser.add_argument("--qualification", default="BVSc & AH")
    parser.add_argument("--specialization", default="General Veterinarian")
    args = parser.parse_args()

    mobile_number = normalized_mobile_number(args.mobile_number)
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.mobile_number == mobile_number)) is not None:
            raise SystemExit("A user with this mobile number already exists")
        doctor_user = User(
            mobile_number=mobile_number,
            full_name=args.name.strip(),
            role=UserRole.DOCTOR,
        )
        profile = DoctorProfile(
            user=doctor_user,
            license_number=args.license_number.strip(),
            qualification=args.qualification.strip(),
            specialization=args.specialization,
            verification_status=VerificationStatus.VERIFIED,
            verified_at=utc_now(),
        )
        db.add_all([doctor_user, profile])
        db.commit()
        print(f"Primary doctor created: {mobile_number} ({args.name})")


if __name__ == "__main__":
    main()
