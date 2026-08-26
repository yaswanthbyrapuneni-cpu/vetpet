from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Madina Vet Pet API"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./vetpet.db"
    jwt_secret_key: str = "development-only-change-me-before-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8080"]
    upload_dir: str = "./uploads"
    max_upload_bytes: int = 10 * 1024 * 1024
    max_recording_bytes: int = 250 * 1024 * 1024
    otp_mock_mode: bool = True
    otp_expiry_seconds: int = 300
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        env_prefix="VETPET_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
