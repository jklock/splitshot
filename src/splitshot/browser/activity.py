from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar
from uuid import uuid4


class ActivityLogger:
    """Per-run JSONL activity logger for browser control sessions."""

    _LEVEL_ORDER: ClassVar[dict[str, int]] = {
        "debug": 10,
        "info": 20,
        "warning": 30,
        "error": 40,
        "off": 100,
    }
    _DEBUG_EVENTS: ClassVar[set[str]] = {
        "api.export.log",
        "api.export.progress",
        "browser.activity",
        "http.get",
        "http.post",
        "media.client_disconnect",
        "media.complete",
        "static.sent",
    }
    _WARNING_EVENTS: ClassVar[set[str]] = {
        "media.missing",
        "media.range_invalid",
        "static.missing",
    }
    _MAX_LOG_FILES = 100

    def __init__(self, log_dir: str | Path | None = None, console_level: str = "off") -> None:
        import tempfile

        default = Path(tempfile.gettempdir()) / "splitshot-activity-logs"
        root = Path(log_dir) if log_dir is not None else default
        root.mkdir(parents=True, exist_ok=True)
        self._prune_old_logs(root)
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        self.path = root / f"splitshot-browser-{stamp}-{uuid4().hex[:8]}.log"
        self._lock = threading.Lock()
        self._console_level = self.normalize_level(console_level)
        self._sequence = 0
        self._recent_records: list[dict[str, object]] = []

    @classmethod
    def _prune_old_logs(cls, log_dir: Path, max_files: int = 100) -> None:
        try:
            files = sorted(log_dir.glob("splitshot-browser-*.log"), key=lambda p: p.stat().st_mtime)
            while len(files) > max_files:
                files[0].unlink(missing_ok=True)
                files = files[1:]
        except OSError:
            pass

    @classmethod
    def normalize_level(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in cls._LEVEL_ORDER:
            raise ValueError(f"Unsupported log level: {value}")
        return normalized

    @classmethod
    def level_for_event(cls, event: str) -> str:
        if event.endswith(".error"):
            return "error"
        if event in cls._WARNING_EVENTS:
            return "warning"
        if event in cls._DEBUG_EVENTS:
            return "debug"
        return "info"

    def _should_echo(self, level: str) -> bool:
        if self._console_level == "off":
            return False
        return self._LEVEL_ORDER[level] >= self._LEVEL_ORDER[self._console_level]

    def log(self, event: str, *, level: str | None = None, **fields: object) -> None:
        record_level = self.normalize_level(level or self.level_for_event(event))
        with self._lock:
            self._sequence += 1
            record = {
                "seq": self._sequence,
                "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
                "event": event,
                "level": record_level,
                **fields,
            }
            self._recent_records.append(record)
            self._recent_records = self._recent_records[-1000:]
            line = json.dumps(record, default=str, sort_keys=True)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(f"{line}\n")
        if self._should_echo(record_level):
            print(f"[splitshot:{record_level}] {line}", flush=True)

    def snapshot(self, after_seq: int = 0, limit: int = 1000) -> dict[str, object]:
        with self._lock:
            entries = [
                record for record in self._recent_records if int(record.get("seq", 0)) > after_seq
            ]
            if limit > 0:
                entries = entries[-limit:]
            return {
                "cursor": self._sequence,
                "entries": entries,
            }
