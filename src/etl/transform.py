from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime, time, timezone
from typing import Any

import pytz
from pydantic import ValidationError

from src.schemas import TransformedStoreRow, ValidationIssue

log = logging.getLogger(__name__)

BOGOTA_TZ = pytz.timezone("America/Bogota")

# ── Helpers ──────────────────────────────────────────────────────────────────

def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _clean(v: Any) -> str:
    return str(v).strip() if v is not None else ""


# ── Phone ─────────────────────────────────────────────────────────────────────

def normalize_phone(raw: str) -> str | None:
    """Normalize to E.164 Colombia (+57XXXXXXXXXX)."""
    if not raw or not raw.strip():
        return None
    digits = re.sub(r"[^\d]", "", raw)
    if len(digits) == 10 and digits.startswith("3"):
        return f"+57{digits}"
    if digits.startswith("57") and len(digits) == 12:
        return f"+{digits}"
    return None


# ── Years operating ───────────────────────────────────────────────────────────

def normalize_years_operating(raw: str) -> float | None:
    if not raw or not raw.strip():
        return None
    v = _strip_accents(raw.strip().lower())
    v = re.sub(r";+", "", v)          # remove stray semicolons
    v = v.replace(",", ".")            # decimal comma → dot

    # "6 meses" → 0.5
    m = re.match(r"^(\d+(?:\.\d+)?)\s*meses?$", v)
    if m:
        return round(float(m.group(1)) / 12, 4)

    # "4años y medio" / "4 años y medio"
    m = re.match(r"^(\d+(?:\.\d+)?)\s*an?os?\s+y\s+medio$", v)
    if m:
        return float(m.group(1)) + 0.5

    # "3 años y 6 meses"
    m = re.match(r"^(\d+(?:\.\d+)?)\s*an?os?\s+y\s+(\d+(?:\.\d+)?)\s*meses?$", v)
    if m:
        return float(m.group(1)) + round(float(m.group(2)) / 12, 4)

    # "2.5 años" / "8años" / "1 año"
    m = re.match(r"^(\d+(?:\.\d+)?)\s*an?os?$", v)
    if m:
        return float(m.group(1))

    # pure number
    m = re.match(r"^(\d+(?:\.\d+)?)$", v)
    if m:
        return float(m.group(1))

    return None


# ── Schedule days ─────────────────────────────────────────────────────────────

_DAY_ORDER = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


def normalize_schedule_days(raw: str) -> list[str]:
    if not raw:
        return []
    seen: set[str] = set()
    result: list[str] = []
    for part in raw.split(";"):
        canonical = _strip_accents(part.strip().lower())
        if canonical in _DAY_ORDER and canonical not in seen:
            seen.add(canonical)
            result.append(canonical)
    return sorted(result, key=lambda d: _DAY_ORDER.index(d))


# ── Payment methods ───────────────────────────────────────────────────────────

_PAYMENT_CATALOG = {"efectivo", "tarjeta", "nequi", "daviplata", "pse"}


def normalize_payment_methods(raw: str) -> list[str]:
    if not raw:
        return []
    seen: set[str] = set()
    result: list[str] = []
    for part in raw.split(";"):
        m = part.strip().lower()
        if m in _PAYMENT_CATALOG and m not in seen:
            seen.add(m)
            result.append(m)
    return result


# ── City ──────────────────────────────────────────────────────────────────────

_CITY_CATALOG = {
    "bogota": "bogota",
    "medellin": "medellin",
    "cali": "cali",
    "barranquilla": "barranquilla",
}


def normalize_city(raw: str) -> str | None:
    if not raw:
        return None
    key = _strip_accents(raw.strip().lower())
    return _CITY_CATALOG.get(key)


# ── Category ──────────────────────────────────────────────────────────────────

_CATEGORY_MAP = {
    "comida rapida": "fast_food",
    "pizzeria": "pizza",
    "mexicana": "mexican",
    "japonesa": "japanese",
    "colombiana": "colombian",
    "saludable": "healthy",
    "asiatica": "asian",
    "panaderia/cafe": "bakery_cafe",
    "carnes/bbq": "bbq",
}


def normalize_category(raw: str) -> str | None:
    if not raw:
        return None
    key = _strip_accents(raw.strip().lower())
    return _CATEGORY_MAP.get(key, key)


# ── Scheduled at ──────────────────────────────────────────────────────────────

def parse_scheduled_at(date_str: str, time_str: str) -> datetime:
    dt = datetime.strptime(f"{date_str.strip()} {time_str.strip()}", "%Y-%m-%d %H:%M")
    return BOGOTA_TZ.localize(dt)


def parse_clock(value: str) -> time | None:
    if not value:
        return None
    return datetime.strptime(value.strip(), "%H:%M").time()


# ── Boolean ───────────────────────────────────────────────────────────────────

def parse_bool(v: Any) -> bool:
    return str(v).strip().upper() in ("TRUE", "1", "YES", "SI", "SÍ")


# ── Main transform ────────────────────────────────────────────────────────────

def transform_row(raw: dict, row_num: int, filename: str, ingested_at: datetime) -> TransformedStoreRow:
    errors: list[ValidationIssue] = []

    def err(field: str, raw_v: Any, msg: str) -> None:
        errors.append(
            ValidationIssue(field=field, raw=None if raw_v is None else str(raw_v), msg=msg)
        )

    # ── Identity
    store_id = _clean(raw.get("store_id")).upper()

    # ── Phone
    phone = normalize_phone(_clean(raw.get("phone")))
    if raw.get("phone") and not phone:
        err("phone", raw["phone"], "Cannot normalize to E.164 +57")

    # ── Email
    email_raw = _clean(raw.get("email")).lower()
    email = email_raw if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email_raw) else None
    if email_raw and not email:
        err("email", email_raw, "Invalid email format")

    # ── Years operating
    years = normalize_years_operating(_clean(raw.get("years_operating")))
    if raw.get("years_operating") and years is None:
        err("years_operating", raw["years_operating"], "Cannot parse years")

    # ── Commission
    commission: float | None = None
    try:
        commission = float(_clean(raw.get("commission_rate_pct")))
        if not (0 <= commission <= 100):
            err("commission_rate_pct", commission, "Out of range 0-100")
            commission = None
    except (ValueError, TypeError):
        if raw.get("commission_rate_pct"):
            err("commission_rate_pct", raw["commission_rate_pct"], "Not a number")

    # ── Coordinates
    lat: float | None = None
    lng: float | None = None
    try:
        lat = float(_clean(raw.get("address_pin_lat")))
        lng = float(_clean(raw.get("address_pin_lng")))
    except (ValueError, TypeError):
        if raw.get("address_pin_lat") or raw.get("address_pin_lng"):
            err(
                "address_pin_lat/lng",
                f"{raw.get('address_pin_lat')}/{raw.get('address_pin_lng')}",
                "Cannot parse coordinates as float",
            )

    # ── Numeric fields
    def to_int(v: Any) -> int | None:
        try:
            return int(float(_clean(v)))
        except (ValueError, TypeError):
            return None

    def to_float(v: Any) -> float | None:
        try:
            return float(_clean(v))
        except (ValueError, TypeError):
            return None

    # ── Scheduled at
    scheduled_at: datetime | None = None
    meeting_date = _clean(raw.get("meeting_date"))
    meeting_time = _clean(raw.get("meeting_time"))
    if meeting_date and meeting_time:
        try:
            scheduled_at = parse_scheduled_at(meeting_date, meeting_time)
        except Exception as exc:
            err("meeting_date/time", f"{meeting_date} {meeting_time}", str(exc))

    meeting_link = _clean(raw.get("meeting_link")) or None
    onboarding = _clean(raw.get("onboarding_status")).lower()

    # Sanitize onboarding_status and support_channel to valid Literal values before model_validate
    valid_onboarding = {"pendiente", "en_proceso", "completado"}
    valid_support = {"whatsapp", "email"}
    onboarding_status = onboarding if onboarding in valid_onboarding else None
    if onboarding and onboarding not in valid_onboarding:
        err("onboarding_status", onboarding, f"Invalid value, must be one of {valid_onboarding}")

    support_channel_raw = _clean(raw.get("support_channel")).lower() or None
    support_channel = support_channel_raw if support_channel_raw in valid_support else None
    if support_channel_raw and support_channel_raw not in valid_support:
        err("support_channel", support_channel_raw, f"Invalid value, must be one of {valid_support}")

    schedule_open: time | None = None
    schedule_close: time | None = None
    for field_name in ("schedule_open", "schedule_close"):
        raw_value = _clean(raw.get(field_name))
        if not raw_value:
            continue
        try:
            parsed = parse_clock(raw_value)
            if field_name == "schedule_open":
                schedule_open = parsed
            else:
                schedule_close = parsed
        except ValueError:
            err(field_name, raw_value, "Invalid HH:MM time")

    # ── is_ready_for_handoff
    is_ready = (
        onboarding_status in ("pendiente", "en_proceso")
        and scheduled_at is not None
        and meeting_link is not None
        and phone is not None
        and email is not None
    )

    row = TransformedStoreRow.model_validate(
        {
            "store_id": store_id,
            "store_name": _clean(raw.get("store_name")),
            "owner_name": _clean(raw.get("owner_name")),
            "phone": phone,
            "email": email,
            "city": normalize_city(_clean(raw.get("city"))),
            "address": _clean(raw.get("address")) or None,
            "address_pin_lat": lat,
            "address_pin_lng": lng,
            "category": normalize_category(_clean(raw.get("category"))),
            "years_operating": years,
            "monthly_orders_avg": to_int(raw.get("monthly_orders_avg")),
            "average_ticket_usd": to_float(raw.get("average_ticket_usd")),
            "schedule_open": schedule_open,
            "schedule_close": schedule_close,
            "menu_items_count": to_int(raw.get("menu_items_count")),
            "has_rappialiados_access": parse_bool(raw.get("has_rappialiados_access")),
            "has_portal_partners_access": parse_bool(raw.get("has_portal_partners_access")),
            "onboarding_status": onboarding_status,
            "support_channel": support_channel,
            "commission_rate_pct": commission,
            "notes": _clean(raw.get("notes")) or None,
            "is_ready_for_handoff": is_ready,
            "data_quality_status": "invalid" if errors else "valid",
            "validation_errors": errors,
            "source_file_name": filename,
            "source_row_number": row_num,
            "ingested_at": ingested_at,
            "payment_methods": normalize_payment_methods(_clean(raw.get("payment_methods"))),
            "schedule_days": normalize_schedule_days(_clean(raw.get("schedule_days"))),
            "meeting": {
                "scheduled_at": scheduled_at,
                "meeting_link": meeting_link,
            }
            if (scheduled_at or meeting_link)
            else None,
        }
    )
    return row


def transform_rows(rows: list[dict], filename: str = "unknown") -> list[TransformedStoreRow]:
    """Transform all rows. Each row is isolated — failures are captured as invalid rows."""
    ingested_at = datetime.now(timezone.utc)
    log.info("[transform] Starting transform of %d rows from '%s'", len(rows), filename)

    results: list[TransformedStoreRow] = []
    for i, raw in enumerate(rows):
        row_num = i + 1
        try:
            result = transform_row(raw, row_num, filename, ingested_at)
            if result.validation_errors:
                log.debug(
                    "[transform] Row %d (%s) has %d field error(s): %s",
                    row_num,
                    result.store_id,
                    len(result.validation_errors),
                    [e.field for e in result.validation_errors],
                )
            results.append(result)
        except (ValidationError, Exception) as exc:
            log.warning("[transform] Row %d failed entirely: %s", row_num, exc)
            store_id = str(raw.get("store_id", f"ROW{row_num}")).strip().upper() or f"ROW{row_num}"
            # Build a minimal valid row marked as invalid so the error is recorded in DB
            fallback = TransformedStoreRow.model_construct(
                store_id=store_id,
                store_name=str(raw.get("store_name", "UNKNOWN")).strip() or "UNKNOWN",
                owner_name=str(raw.get("owner_name", "UNKNOWN")).strip() or "UNKNOWN",
                data_quality_status="invalid",
                validation_errors=[ValidationIssue(field="__row__", raw=str(raw), msg=str(exc))],
                source_file_name=filename,
                source_row_number=row_num,
                ingested_at=ingested_at,
                is_ready_for_handoff=False,
                has_rappialiados_access=False,
                has_portal_partners_access=False,
                payment_methods=[],
                schedule_days=[],
                meeting=None,
            )
            results.append(fallback)

    valid_count = sum(1 for r in results if r.data_quality_status != "invalid")
    invalid_count = len(results) - valid_count
    log.info(
        "[transform] Completed: %d total, %d valid, %d invalid",
        len(results), valid_count, invalid_count,
    )
    return results
