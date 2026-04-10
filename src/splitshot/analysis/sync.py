from __future__ import annotations


def compute_sync_offset(primary_beep_ms: int | None, secondary_beep_ms: int | None) -> int:
    if primary_beep_ms is None or secondary_beep_ms is None:
        return 0
    return int(secondary_beep_ms - primary_beep_ms)
