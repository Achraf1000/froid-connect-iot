from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")]


class Telemetry(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    schema_version: Literal[1] = 1
    config_version: Literal[1] = 1
    vehicle_id: Literal["VEH-001"]
    transport_id: Identifier
    boot_id: Identifier
    sequence: Annotated[int, Field(strict=True, ge=0, le=2**53-1)]
    measured_at: datetime | None
    uptime_ms: Annotated[int, Field(strict=True, ge=0, le=2**53-1)]
    temperature_c: Annotated[float, Field(strict=True, ge=-55, le=125)] | None
    latitude: Annotated[float, Field(strict=True, ge=-90, le=90)]
    longitude: Annotated[float, Field(strict=True, ge=-180, le=180)]
    sensor_status: Literal["ok", "error"]
    local_alarm: StrictBool
    dropped_count: Annotated[int, Field(strict=True, ge=0)] = 0
    source: Literal["wokwi", "simulator"] = "wokwi"

    @field_validator("measured_at")
    @classmethod
    def timestamp_is_utc(cls, value):
        if value is not None:
            if value.tzinfo is None:
                raise ValueError("Un fuseau horaire est requis.")
            value = value.astimezone(timezone.utc)
            if (value - datetime.now(timezone.utc)).total_seconds() > 60:
                raise ValueError("Horodatage dans le futur.")
        return value

    @model_validator(mode="after")
    def temperature_matches_status(self):
        if self.sensor_status == "ok" and self.temperature_c is None:
            raise ValueError("Température requise pour un capteur valide.")
        if self.sensor_status == "error" and self.temperature_c is not None:
            raise ValueError("Une erreur capteur doit avoir une température null.")
        return self


class TransportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Identifier
    name: str = Field(min_length=1, max_length=100)
    origin: str = Field(default="Tunis", max_length=80)
    destination: str = Field(default="La Marsa", max_length=80)


class TransportUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["completed"]


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str = Field(max_length=256)
