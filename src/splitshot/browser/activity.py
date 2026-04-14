from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


class ActivityLogger:
    """Per-run JSONL activity logger for browser control sessions."""

    _LEVEL_ORDER = {
        "debug": 10,
        "info": 20,
        "warning": 30,
        "error": 40,
        "off": 100,
    }
    _DEBUG_EVENTS = {
        "api.export.log",
        "api.export.progress",
        "browser.activity",
        "http.get",
        "http.post",
        "media.complete",
        "static.sent",
    }
    _WARNING_EVENTS = {
        "media.client_disconnect",
        "media.missing",
        "media.range_invalid",
        "static.missing",
    }

    def __init__(self, log_dir: str | Path | None = None, console_level: str = "off") -> None:
        root = Path(log_dir) if log_dir is not None else Path.cwd() / "logs"
        root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        self.path = root / f"splitshot-browser-{stamp}-{uuid4().hex[:8]}.log"
        self._lock = threading.Lock()
        self._console_level = self.normalize_level(console_level)

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
        record = {
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "event": event,
            "level": record_level,
            **fields,
        }
        line = json.dumps(record, default=str, sort_keys=True)
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(f"{line}\n")
        if self._should_echo(record_level):
            print(f"[splitshot:{record_level}] {line}", flush=True)
