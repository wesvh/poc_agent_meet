from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from src.config import Config
from src.infrastructure.db.engine import session_scope
from src.infrastructure.db.orm import Meeting
from src.infrastructure.events.eventbridge import upsert_meeting_schedule

log = logging.getLogger(__name__)


@dataclass
class MeetingScheduleCandidate:
    store_id: str
    scheduled_at: datetime
    meeting_link: str


async def schedule_meeting_candidates(candidates: list[dict]) -> dict:
    stats = {
        "candidates": len(candidates),
        "scheduled": 0,
        "updated": 0,
        "missing": 0,
        "skipped_past": 0,
    }
    if not candidates:
        return stats

    now = datetime.now(UTC)
    async with session_scope() as session:
        for raw in candidates:
            candidate = MeetingScheduleCandidate(
                store_id=raw["store_id"],
                scheduled_at=datetime.fromisoformat(raw["scheduled_at"]),
                meeting_link=raw["meeting_link"],
            )
            trigger_at = candidate.scheduled_at.astimezone(UTC) - timedelta(minutes=Config.MEETING_LEAD_MINUTES)
            if trigger_at <= now:
                stats["skipped_past"] += 1
                continue

            meeting = await session.scalar(
                select(Meeting).where(
                    Meeting.store_id == candidate.store_id,
                    Meeting.scheduled_at == candidate.scheduled_at,
                    Meeting.meeting_link == candidate.meeting_link,
                    Meeting.status == "pending",
                )
            )
            if meeting is None:
                stats["missing"] += 1
                continue

            changed = await upsert_meeting_schedule(
                meeting_id=str(meeting.id),
                store_id=meeting.store_id,
                scheduled_at=meeting.scheduled_at,
                meeting_link=meeting.meeting_link,
                lead_minutes=Config.MEETING_LEAD_MINUTES,
            )
            stats["updated" if changed == "updated" else "scheduled"] += 1

    log.info("[meeting-scheduler] stats=%s", json.dumps(stats, default=str))
    return stats
