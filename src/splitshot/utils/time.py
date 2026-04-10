from __future__ import annotations


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def ms_to_seconds(value_ms: int) -> float:
    return value_ms / 1000.0


def seconds_to_ms(value_seconds: float) -> int:
    return int(round(value_seconds * 1000))


def format_time_ms(value_ms: int | None) -> str:
    if value_ms is None:
        return "--:--.---"
    total_seconds = value_ms / 1000.0
    minutes = int(total_seconds // 60)
    seconds = total_seconds - (minutes * 60)
    return f"{minutes:02d}:{seconds:06.3f}"
