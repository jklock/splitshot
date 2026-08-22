import json
import time
import urllib.request

import pytest


class ActivityTracker:
    """Polls the server's /api/activity/poll endpoint and provides log assertions."""

    def __init__(self, server_url: str) -> None:
        self.server_url = server_url.rstrip("/")
        self.cursor = 0
        self._all_entries: list[dict] = []

    def poll(self) -> list[dict]:
        url = f"{self.server_url}/api/activity/poll?after={self.cursor}"
        try:
            response = urllib.request.urlopen(url, timeout=5)
            data = json.loads(response.read().decode("utf-8"))
        except Exception:  # noqa: BLE001 - polling tolerates transient server shutdown.
            return []
        entries = data.get("entries", [])
        if entries:
            seqs = [int(e.get("seq", 0)) for e in entries]
            self.cursor = max(seqs)
            self._all_entries.extend(entries)
        return entries

    def all_entries(self) -> list[dict]:
        return list(self._all_entries)

    def _match_event(self, entry: dict, event_pattern: str) -> bool:
        return event_pattern in entry.get("event", "") or event_pattern in entry.get(
            "browser_event", ""
        )

    def assert_activity(self, event_pattern: str, timeout: float = 8.0) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            entries = self.poll()
            for entry in entries:
                if self._match_event(entry, event_pattern):
                    return entry
            time.sleep(0.1)
        self._dump_log()
        pytest.fail(
            f"Activity event matching '{event_pattern}' not found within {timeout}s. "
            f"Cursor at {self.cursor}, have {len(self._all_entries)} entries total."
        )

    def assert_activity_count(
        self, event_pattern: str, expected: int, timeout: float = 8.0
    ) -> list[dict]:
        deadline = time.time() + timeout
        while time.time() < deadline:
            self.poll()
            matched = [e for e in self._all_entries if self._match_event(e, event_pattern)]
            if len(matched) >= expected:
                return matched
            time.sleep(0.1)
        self._dump_log()
        matched = [e for e in self._all_entries if self._match_event(e, event_pattern)]
        pytest.fail(
            f"Expected {expected} entries matching '{event_pattern}', found {len(matched)} "
            f"within {timeout}s."
        )

    def assert_no_activity(self, event_pattern: str, timeout: float = 3.0) -> None:
        time.sleep(timeout)
        self.poll()
        matched = [e for e in self._all_entries if self._match_event(e, event_pattern)]
        if matched:
            pytest.fail(
                f"Found unexpected activity event '{event_pattern}' ({len(matched)} entries)"
            )

    def _dump_log(self) -> None:
        import sys

        if not self._all_entries:
            print("[activity_tracker] No entries captured yet.", file=sys.stderr)
            return
        print(
            f"[activity_tracker] Last {min(20, len(self._all_entries))} entries:", file=sys.stderr
        )
        for entry in self._all_entries[-20:]:
            ev = entry.get("event", "?")
            be = entry.get("browser_event", "")
            label = f"{ev}/{be}" if be else ev
            detail = {
                k: v
                for k, v in entry.items()
                if k not in ("seq", "ts", "event", "level", "browser_event")
            }
            detail_str = json.dumps(detail, default=str)[:200]
            print(f"  seq={entry.get('seq')} event={label} detail={detail_str}", file=sys.stderr)


def get_status_bar(page) -> str:
    return str(page.evaluate("() => document.getElementById('status')?.textContent?.trim() || ''"))


def assert_status(page, substr: str) -> None:
    actual = get_status_bar(page)
    assert substr.lower() in actual.lower(), f"Expected status '{substr}', got '{actual}'"
