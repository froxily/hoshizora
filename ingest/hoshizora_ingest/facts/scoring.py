from dataclasses import dataclass
from datetime import datetime

from hoshizora_ingest.facts.spec import Scoring

FIRST_SCORE = 0.9
RECORD_SCORE = 1.0
SECONDS_PER_DAY = 86_400


@dataclass(frozen=True)
class Signals:
    percentile: float | None = None
    is_record: bool = False
    is_first: bool = False
    event_at: datetime | None = None


def recency(event_at: datetime | None, as_of: datetime, half_life_days: float | None) -> float:
    if event_at is None or half_life_days is None:
        return 1.0
    age_days = abs((as_of - event_at).total_seconds()) / SECONDS_PER_DAY
    return 0.5 ** (age_days / half_life_days)


def score(signals: Signals, scoring: Scoring, as_of: datetime) -> float:
    strength = max(
        scoring.base,
        signals.percentile or 0.0,
        FIRST_SCORE if signals.is_first else 0.0,
        RECORD_SCORE if signals.is_record else 0.0,
    )
    decay = recency(signals.event_at, as_of, scoring.half_life_days)
    return round(min(1.0, strength) * decay, 4)
