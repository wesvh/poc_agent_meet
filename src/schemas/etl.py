from __future__ import annotations

from datetime import datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ValidationIssue(BaseModel):
    field: str
    raw: str | None = None
    msg: str


class MeetingPayload(BaseModel):
    scheduled_at: datetime | None = None
    meeting_link: str | None = None


class TransformedStoreRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    store_id: str
    store_name: str
    owner_name: str
    phone: str | None = None
    email: str | None = None
    city: str | None = None
    address: str | None = None
    address_pin_lat: float | None = None
    address_pin_lng: float | None = None
    category: str | None = None
    years_operating: float | None = None
    monthly_orders_avg: int | None = None
    average_ticket_usd: float | None = None
    schedule_open: time | None = None
    schedule_close: time | None = None
    menu_items_count: int | None = None
    has_rappialiados_access: bool = False
    has_portal_partners_access: bool = False
    onboarding_status: Literal["pendiente", "en_proceso", "completado"] | None = None
    support_channel: Literal["whatsapp", "email"] | None = None
    commission_rate_pct: float | None = None
    notes: str | None = None
    is_ready_for_handoff: bool = False
    data_quality_status: Literal["valid", "invalid", "warning"] = "valid"
    validation_errors: list[ValidationIssue] = Field(default_factory=list)
    source_file_name: str
    source_row_number: int
    ingested_at: datetime
    payment_methods: list[str] = Field(default_factory=list)
    schedule_days: list[str] = Field(default_factory=list)
    meeting: MeetingPayload | None = None

    @field_validator("store_id")
    @classmethod
    def normalize_store_id(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("store_name", "owner_name", "source_file_name")
    @classmethod
    def require_non_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("commission_rate_pct")
    @classmethod
    def validate_commission(cls, value: float | None) -> float | None:
        if value is not None and not 0 <= value <= 100:
            raise ValueError("must be between 0 and 100")
        return value

    def with_additional_errors(self, issues: list[ValidationIssue]) -> "TransformedStoreRow":
        merged = [*self.validation_errors, *issues]
        return self.model_copy(
            update={
                "validation_errors": merged,
                "data_quality_status": "invalid" if merged else self.data_quality_status,
            }
        )

    def store_values(self) -> dict:
        return self.model_dump(
            mode="python",
            exclude={"payment_methods", "schedule_days", "meeting"},
        )
