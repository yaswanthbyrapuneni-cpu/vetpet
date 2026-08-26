from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture(autouse=True)
def never_send_real_sms(monkeypatch: pytest.MonkeyPatch) -> None:
    # Guards against a developer's local .env having a real Twilio account
    # configured with otp_mock_mode=false — tests must never place a real
    # network call to a paid SMS API no matter what's on disk locally.
    monkeypatch.setattr("app.api.routes.auth.send_otp_sms", lambda *args, **kwargs: None)

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    Base.metadata.create_all(test_engine)
    yield
    Base.metadata.drop_all(test_engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    with TestingSessionLocal() as session:
        yield session


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def otp_login_headers(
    client: TestClient, mobile_number: str, full_name: str | None = None
) -> dict[str, str]:
    """Request+verify an OTP for mobile_number, creating a new owner if full_name is given."""
    request = client.post("/api/v1/auth/otp/request", json={"mobile_number": mobile_number})
    assert request.status_code == 200
    payload: dict[str, object] = {"mobile_number": mobile_number, "code": request.json()["dev_otp"]}
    if full_name is not None:
        payload["full_name"] = full_name
    verify = client.post("/api/v1/auth/otp/verify", json=payload)
    assert verify.status_code == 200
    return {"Authorization": f"Bearer {verify.json()['access_token']}"}

