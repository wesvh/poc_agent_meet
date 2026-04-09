"""SQLAlchemy ORM models.

These are INFRASTRUCTURE models — they live here and nowhere else.
Application and domain code must NOT import from this module directly.
Use the repository ports (src.core.ports) or the concrete repositories
(src.infrastructure.db.repositories) instead.
"""
from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, Text, Time, UniqueConstraint, delete, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID, insert
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ETLRun(Base):
    __tablename__ = "etl_runs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    source_file_name = Column(Text, nullable=False)
    source_file_hash = Column(Text, nullable=False)
    s3_raw_key = Column(Text)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    finished_at = Column(DateTime(timezone=True))
    status = Column(Text, nullable=False, server_default=text("'running'"))
    rows_raw = Column(Integer, nullable=False, server_default=text("0"))
    rows_valid = Column(Integer, nullable=False, server_default=text("0"))
    rows_invalid = Column(Integer, nullable=False, server_default=text("0"))
    rows_upserted = Column(Integer, nullable=False, server_default=text("0"))


class ETLError(Base):
    __tablename__ = "etl_errors"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    etl_run_id = Column(PG_UUID(as_uuid=True), ForeignKey("etl_runs.id", ondelete="CASCADE"))
    source_row_number = Column(Integer)
    store_id = Column(Text)
    field_name = Column(Text)
    raw_value = Column(Text)
    error_message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class StagingStoreRaw(Base):
    __tablename__ = "stg_stores_raw"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    etl_run_id = Column(PG_UUID(as_uuid=True), ForeignKey("etl_runs.id", ondelete="CASCADE"))
    source_file_name = Column(Text, nullable=False)
    source_row_number = Column(Integer, nullable=False)
    ingested_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    raw_data = Column(JSONB, nullable=False)


class Store(Base):
    __tablename__ = "stores"

    store_id = Column(Text, primary_key=True)
    store_name = Column(Text, nullable=False)
    owner_name = Column(Text, nullable=False)
    phone = Column(Text)
    email = Column(Text)
    city = Column(Text)
    address = Column(Text)
    address_pin_lat = Column(Numeric(9, 6))
    address_pin_lng = Column(Numeric(9, 6))
    category = Column(Text)
    years_operating = Column(Numeric(5, 2))
    monthly_orders_avg = Column(Integer)
    average_ticket_usd = Column(Numeric(10, 2))
    schedule_open = Column(Time)
    schedule_close = Column(Time)
    menu_items_count = Column(Integer)
    has_rappialiados_access = Column(Boolean, nullable=False, server_default=text("FALSE"))
    has_portal_partners_access = Column(Boolean, nullable=False, server_default=text("FALSE"))
    onboarding_status = Column(Text)
    support_channel = Column(Text)
    commission_rate_pct = Column(Numeric(5, 2))
    notes = Column(Text)
    is_ready_for_handoff = Column(Boolean, nullable=False, server_default=text("FALSE"))
    data_quality_status = Column(Text, nullable=False, server_default=text("'valid'"))
    validation_errors = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    source_file_name = Column(Text)
    source_row_number = Column(Integer)
    ingested_at = Column(DateTime(timezone=True))
    normalized_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    @classmethod
    def upsert_stmt(cls, values: dict[str, Any]):
        stmt = insert(cls).values(**values)
        update_values = {
            key: getattr(stmt.excluded, key)
            for key in values
            if key not in {"store_id", "normalized_at"}
        }
        update_values["updated_at"] = text("now()")
        return stmt.on_conflict_do_update(
            index_elements=[cls.store_id],
            set_=update_values,
        )


class StorePaymentMethod(Base):
    __tablename__ = "store_payment_methods"
    __table_args__ = (UniqueConstraint("store_id", "method"),)

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    store_id = Column(ForeignKey("stores.store_id", ondelete="CASCADE"), nullable=False)
    method = Column(Text, nullable=False)

    @classmethod
    def delete_for_store_stmt(cls, store_id: str):
        return delete(cls).where(cls.store_id == store_id)

    @classmethod
    def insert_many_stmt(cls, store_id: str, methods: list[str]):
        return insert(cls).values([{"store_id": store_id, "method": method} for method in methods]).on_conflict_do_nothing()


class StoreScheduleDay(Base):
    __tablename__ = "store_schedule_days"
    __table_args__ = (UniqueConstraint("store_id", "day"),)

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    store_id = Column(ForeignKey("stores.store_id", ondelete="CASCADE"), nullable=False)
    day = Column(Text, nullable=False)

    @classmethod
    def delete_for_store_stmt(cls, store_id: str):
        return delete(cls).where(cls.store_id == store_id)

    @classmethod
    def insert_many_stmt(cls, store_id: str, days: list[str]):
        return insert(cls).values([{"store_id": store_id, "day": day} for day in days]).on_conflict_do_nothing()


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    store_id = Column(ForeignKey("stores.store_id", ondelete="CASCADE"), nullable=False)
    scheduled_at = Column(DateTime(timezone=True))
    meeting_link = Column(Text)
    status = Column(Text, nullable=False, server_default=text("'pending'"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    @classmethod
    def upsert_stmt(cls, values: dict[str, Any]):
        stmt = insert(cls).values(**values)
        return stmt.on_conflict_do_nothing(
            index_elements=[cls.store_id, cls.scheduled_at, cls.meeting_link]
        )


class HandoffSession(Base):
    __tablename__ = "handoff_sessions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    store_id = Column(Text, ForeignKey("stores.store_id", ondelete="CASCADE"), nullable=False)
    meeting_id = Column(PG_UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="SET NULL"))
    status = Column(Text, nullable=False, server_default=text("'active'"))
    blocks_completed = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    collected_data = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    issues_detected = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    commitments = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    transcript = Column(JSONB)
    summary = Column(Text)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    ended_at = Column(DateTime(timezone=True))
    turn_count = Column(Integer, nullable=False, server_default=text("0"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
