from __future__ import annotations

import logging
import re

from src.schemas import TransformedStoreRow, ValidationIssue

log = logging.getLogger(__name__)


def validate_store_id(v: str) -> bool:
    return bool(re.match(r"^STR\d{3,}$", str(v).strip().upper()))


def validate_email(v: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(v).strip().lower()))


def validate_phone_e164(v: str) -> bool:
    return bool(re.match(r"^\+57\d{10}$", str(v).strip()))


def validate_commission(v) -> bool:
    try:
        return 0 <= float(v) <= 100
    except (ValueError, TypeError):
        return False


def validate_onboarding_status(v: str) -> bool:
    return str(v).lower() in ("pendiente", "en_proceso", "completado")


def validate_support_channel(v: str) -> bool:
    return str(v).lower() in ("whatsapp", "email")


def check_business_rules(row: TransformedStoreRow) -> list[ValidationIssue]:
    """Apply cross-field and field-level business rules. Returns list of errors."""
    errors: list[ValidationIssue] = []
    onboarding = (row.onboarding_status or "").lower()

    # Cross-field: meeting fields required for active onboarding
    if onboarding in ("pendiente", "en_proceso"):
        if not row.meeting or not row.meeting.meeting_link:
            errors.append(
                ValidationIssue(
                    field="meeting_link",
                    raw=None,
                    msg=f"meeting_link required when onboarding_status={onboarding}",
                )
            )
        if not row.meeting or not row.meeting.scheduled_at:
            errors.append(
                ValidationIssue(
                    field="meeting_date/time",
                    raw=None,
                    msg=f"scheduled_at required when onboarding_status={onboarding}",
                )
            )

    # store_id format
    if not validate_store_id(row.store_id):
        errors.append(
            ValidationIssue(
                field="store_id",
                raw=row.store_id,
                msg=r"Does not match STR\d{3,}",
            )
        )

    # email format (post-transform validation)
    if row.email and not validate_email(row.email):
        errors.append(
            ValidationIssue(
                field="email",
                raw=row.email,
                msg="Invalid email format",
            )
        )

    # phone E.164 format
    if row.phone and not validate_phone_e164(row.phone):
        errors.append(
            ValidationIssue(
                field="phone",
                raw=row.phone,
                msg="Phone not in E.164 +57XXXXXXXXXX format",
            )
        )

    # commission range
    if row.commission_rate_pct is not None and not validate_commission(row.commission_rate_pct):
        errors.append(
            ValidationIssue(
                field="commission_rate_pct",
                raw=str(row.commission_rate_pct),
                msg="Commission must be between 0 and 100",
            )
        )

    if errors:
        log.debug(
            "[validate] Row %d (%s): %d business rule error(s): %s",
            row.source_row_number,
            row.store_id,
            len(errors),
            [e.field for e in errors],
        )

    return errors
