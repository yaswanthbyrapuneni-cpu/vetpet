from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.domain import Reminder, ReminderType
from tests.conftest import otp_login_headers


def create_owner_and_pet(
    client: TestClient, suffix: str
) -> tuple[dict[str, str], dict[str, object]]:
    mobile_number = f"+9198767{suffix.zfill(5)}"
    headers = otp_login_headers(client, mobile_number, full_name="Reminder Owner")
    pet = client.post(
        "/api/v1/pets",
        json={"name": "Coco", "species": "dog"},
        headers=headers,
    )
    return headers, pet.json()


def test_owner_creates_updates_and_deactivates_reminder(client: TestClient) -> None:
    headers, pet = create_owner_and_pet(client, "00001")
    scheduled = datetime.now(UTC) + timedelta(days=1)
    created = client.post(
        f"/api/v1/pets/{pet['id']}/reminders",
        json={
            "reminder_type": "medicine",
            "title": "Give antibiotic",
            "message": "Give one tablet after food",
            "scheduled_for": scheduled.isoformat(),
            "repeat_interval_hours": 12,
            "ends_at": (scheduled + timedelta(days=5)).isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201
    reminder_id = created.json()["id"]
    assert len(client.get("/api/v1/reminders", headers=headers).json()) == 1

    updated = client.patch(
        f"/api/v1/reminders/{reminder_id}",
        json={"title": "Give prescribed antibiotic"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Give prescribed antibiotic"
    assert client.delete(f"/api/v1/reminders/{reminder_id}", headers=headers).status_code == 204
    assert client.get("/api/v1/reminders", headers=headers).json() == []


def test_due_reminder_becomes_notification_and_can_be_read(
    client: TestClient, db_session: Session
) -> None:
    headers, pet = create_owner_and_pet(client, "00002")
    reminder = Reminder(
        user_id=pet["owner_id"],
        pet_id=pet["id"],
        created_by_user_id=pet["owner_id"],
        reminder_type=ReminderType.VACCINATION,
        title="Vaccination due",
        message="Annual vaccination is due today.",
        scheduled_for=datetime.now(UTC) - timedelta(minutes=1),
    )
    db_session.add(reminder)
    db_session.commit()

    inbox = client.get("/api/v1/notifications", headers=headers)
    assert inbox.status_code == 200
    assert len(inbox.json()) == 1
    assert inbox.json()[0]["notification_type"] == "reminder"
    notification_id = inbox.json()[0]["id"]

    read = client.post(f"/api/v1/notifications/{notification_id}/read", headers=headers)
    assert read.status_code == 200
    assert read.json()["read_at"] is not None
    assert client.get("/api/v1/reminders", headers=headers).json() == []


def test_repeating_due_reminder_advances_to_future(
    client: TestClient, db_session: Session
) -> None:
    headers, pet = create_owner_and_pet(client, "00003")
    reminder = Reminder(
        user_id=pet["owner_id"],
        pet_id=pet["id"],
        created_by_user_id=pet["owner_id"],
        reminder_type=ReminderType.MEDICINE,
        title="Medicine dose",
        scheduled_for=datetime.now(UTC) - timedelta(hours=25),
        repeat_interval_hours=12,
    )
    db_session.add(reminder)
    db_session.commit()

    assert len(client.get("/api/v1/notifications", headers=headers).json()) == 1
    active = client.get("/api/v1/reminders", headers=headers).json()
    assert len(active) == 1
    next_time = datetime.fromisoformat(active[0]["scheduled_for"])
    if next_time.tzinfo is None:
        next_time = next_time.replace(tzinfo=UTC)
    assert next_time > datetime.now(UTC)


def test_users_cannot_read_each_others_notifications(
    client: TestClient, db_session: Session
) -> None:
    first_headers, pet = create_owner_and_pet(client, "00004")
    second_headers, _ = create_owner_and_pet(client, "00005")
    reminder = Reminder(
        user_id=pet["owner_id"],
        pet_id=pet["id"],
        created_by_user_id=pet["owner_id"],
        reminder_type=ReminderType.CUSTOM,
        title="Private reminder",
        scheduled_for=datetime.now(UTC) - timedelta(minutes=1),
    )
    db_session.add(reminder)
    db_session.commit()
    notification_id = client.get("/api/v1/notifications", headers=first_headers).json()[0]["id"]

    assert (
        client.post(
            f"/api/v1/notifications/{notification_id}/read", headers=second_headers
        ).status_code
        == 404
    )
