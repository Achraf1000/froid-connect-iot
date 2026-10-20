from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )
    mongo_uri: str = "mongodb://127.0.0.1:27018"
    mongo_database: str = "cold_chain"
    device_api_key: str = Field(min_length=16)
    dashboard_password: str = Field(min_length=12)
    session_secret: str = Field(min_length=32)
    cookie_secure: bool = False
    firebase_mode: str = "emulator"
    firebase_database_url: str = "http://127.0.0.1:9000?ns=demo-cold-chain-default-rtdb"
    firebase_project_id: str = "demo-cold-chain"
    firebase_reader_uid: str = "dashboard"
    firebase_web_api_key: str = ""
    firebase_auth_domain: str = ""
    firebase_auth_emulator_url: str = "http://127.0.0.1:9099"
    firebase_database_emulator_host: str = "127.0.0.1"
    firebase_database_emulator_port: int = Field(default=9000, ge=1, le=65535)
    google_application_credentials: str = ""
    frontend_origin: str = "http://localhost:5173"


RULES = {
    "config_version": 1,
    "min_c": 2.0,
    "max_c": 8.0,
    "delay_ms": 30000,
    "sample_ms": 5000,
    "max_gap_ms": 10000,
    "stale_seconds": 15,
}
