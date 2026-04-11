from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


class ActivityLogger:
    """Per-run JSONL activity logger for browser control sessions."""

    def __init__(self, log_dir: str | Path | None = None) -> None:
        root = Path(log_dir) if log_dir is not None else Path.cwd() / "logs"
        root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        self.path = root / f"splitshot-browser-{stamp}-{uuid4().hex[:8]}.log"
        self._lock = threading.Lock()

    def log(self, event: str, **fields: object) -> None:
        record = {
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "event": event,
            **fields,
        }
        line = json.dumps(record, default=str, sort_keys=True)
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(f"{line}\n")
        print(f"[splitshot] {line}", flush=True)
