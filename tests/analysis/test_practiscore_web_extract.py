from __future__ import annotations

import json
from pathlib import Path

from splitshot.scoring.practiscore_web_extract import (
    RemotePractiScoreMatch,
    download_remote_match_artifacts,
    discover_remote_matches,
)


class _FakePage:
    def __init__(
        self,
        *,
        url: str,
        html: str,
        discover_payload: list[dict[str, object]] | None = None,
        selection_payloads: dict[str, dict[str, object]] | None = None,
        selected_snapshots: dict[str, dict[str, object]] | None = None,
        fetched_artifacts: dict[str, dict[str, object]] | None = None,
    ) -> None:
        self.url = url
        self.goto_calls: list[str] = []
        self._html = html
        self._discover_payload = list(discover_payload or [])
        self._selection_payloads = dict(selection_payloads or {})
        self._selected_snapshots = dict(selected_snapshots or {})
        self._fetched_artifacts = dict(fetched_artifacts or {})

    def content(self) -> str:
        return self._html

    def evaluate(self, script: str, argument: object | None = None) -> object:
        if "splitshot-practiscore-discover-matches" in script:
            return list(self._discover_payload)
        if "splitshot-practiscore-select-match" in script:
            return dict(self._selection_payloads[str(argument)])
        if "splitshot-practiscore-selected-match" in script:
            return dict(self._selected_snapshots[str(argument)])
        if "splitshot-practiscore-fetch-artifact" in script:
            return dict(self._fetched_artifacts[str(argument)])
        raise AssertionError(f"Unexpected script: {script}")

    def goto(self, url: str, wait_until: str = "domcontentloaded", timeout: int = 15000) -> None:
        del wait_until, timeout
        self.url = url
        self.goto_calls.append(url)

    def is_closed(self) -> bool:
        return False

    def close(self) -> None:
        return


class _FakeContext:
    def __init__(self, landing_page: _FakePage, detail_pages: dict[str, _FakePage] | None = None) -> None:
        self.pages = [landing_page]
        self._detail_pages = dict(detail_pages or {})
        self._new_pages: list[_FakePage] = []

    def open_remote_match_page(self, remote_id: str) -> _FakePage:
        return self._detail_pages[remote_id]

    def new_page(self) -> _FakePage:
        page = _FakePage(url="about:blank", html="<html></html>")
        self._new_pages.append(page)
        return page


def test_discover_remote_matches_returns_stable_match_shape() -> None:
    landing_page = _FakePage(url="https://practiscore.com/dashboard/home", html="<html></html>")
    context = _FakeContext(landing_page)
    discovery_page = context.new_page()
    discovery_page._discover_payload = [
        {
            "remote_id": "match-100",
            "label": "April USPSA Night Match",
            "match_type": "uspsa",
            "event_name": "April USPSA Night Match",
            "event_date": "2026-04-21",
            "details_url": "https://practiscore.com/results/match-100",
        },
        {
            "remote_id": "match-200",
            "label": "Classifier Weekend",
            "match_type": "idpa",
            "event_name": "Classifier Weekend",
            "event_date": "2026-04-22",
            "details_url": "https://practiscore.com/results/match-200",
        },
    ]
    context._new_pages.clear()

    def _new_page() -> _FakePage:
        return discovery_page

    context.new_page = _new_page  # type: ignore[method-assign]

    matches = discover_remote_matches(context)

    assert landing_page.url == "https://practiscore.com/dashboard/home"
    assert discovery_page.goto_calls == ["https://practiscore.com/search/matches"]
    assert matches == [
        RemotePractiScoreMatch(
            remote_id="match-100",
            label="April USPSA Night Match",
            match_type="uspsa",
            event_name="April USPSA Night Match",
            event_date="2026-04-21",
            details_url="https://practiscore.com/results/match-100",
        ),
        RemotePractiScoreMatch(
            remote_id="match-200",
            label="Classifier Weekend",
            match_type="idpa",
            event_name="Classifier Weekend",
            event_date="2026-04-22",
            details_url="https://practiscore.com/results/match-200",
        ),
    ]


def test_download_remote_match_artifacts_writes_deterministic_cache_metadata(tmp_path: Path) -> None:
    landing_page = _FakePage(
        url="https://practiscore.com/clubs",
        html="<html></html>",
        selection_payloads={
            "match-100": {
                "remote_id": "match-100",
                "label": "April USPSA Night Match",
                "match_type": "uspsa",
                "event_name": "April USPSA Night Match",
                "event_date": "2026-04-21",
                "details_url": "https://practiscore.com/results/match-100",
            }
        },
    )
    detail_page = _FakePage(
        url="https://practiscore.com/results/match-100",
        html="<html><body><h1>April USPSA Night Match</h1></body></html>",
        selected_snapshots={
            "match-100": {
                "remote_id": "match-100",
                "label": "April USPSA Night Match",
                "match_type": "uspsa",
                "event_name": "April USPSA Night Match",
                "event_date": "2026-04-21",
                "title": "April USPSA Night Match",
                "heading": "April USPSA Night Match",
                "metadata": {
                    "Division": "Limited",
                    "Club": "SplitShot Club",
                },
                "artifact": {
                    "download_url": "https://practiscore.com/results/match-100/report.csv",
                    "suggested_filename": "night-match.csv",
                },
            }
        },
        fetched_artifacts={
            "https://practiscore.com/results/match-100/report.csv": {
                "ok": True,
                "status": 200,
                "url": "https://practiscore.com/results/match-100/report.csv",
                "content_type": "text/csv",
                "text": "Place,First Name,Last Name\n1,Jeff,Graff\n",
            }
        },
    )
    context = _FakeContext(landing_page, {"match-100": detail_page})

    artifacts = download_remote_match_artifacts(
        context,
        "match-100",
        tmp_path,
        match_catalog=[
            {
                "remote_id": "match-100",
                "label": "April USPSA Night Match",
                "match_type": "uspsa",
                "event_name": "April USPSA Night Match",
                "event_date": "2026-04-21",
            }
        ],
    )

    assert artifacts.cache_dir == tmp_path / "match-100"
    assert artifacts.source_artifact_path == artifacts.cache_dir / "night-match.csv"
    assert artifacts.html_path == artifacts.cache_dir / "selected-match.html"
    assert artifacts.summary_path == artifacts.cache_dir / "summary.json"
    summary = json.loads(artifacts.summary_path.read_text(encoding="utf-8"))
    assert summary["remote_match"] == {
        "remote_id": "match-100",
        "label": "April USPSA Night Match",
        "match_type": "uspsa",
        "event_name": "April USPSA Night Match",
        "event_date": "2026-04-21",
    }
    assert summary["artifact"]["source_artifact_path"] == str(artifacts.source_artifact_path)
    assert summary["metadata"] == {
        "Division": "Limited",
        "Club": "SplitShot Club",
    }


def test_download_remote_match_artifacts_captures_source_html_and_summary_together(tmp_path: Path) -> None:
    landing_page = _FakePage(
        url="https://practiscore.com/clubs",
        html="<html></html>",
    )
    detail_page = _FakePage(
        url="https://practiscore.com/results/match-200",
        html="<html><body><h1>Classifier Weekend</h1><p>Rendered HTML</p></body></html>",
        selected_snapshots={
            "match-200": {
                "remote_id": "match-200",
                "label": "Classifier Weekend",
                "match_type": "idpa",
                "event_name": "Classifier Weekend",
                "event_date": "2026-04-22",
                "title": "Classifier Weekend",
                "heading": "Classifier Weekend",
                "metadata": {"Range": "North Bay"},
                "artifact": {
                    "download_url": "https://practiscore.com/results/match-200/report.txt",
                    "suggested_filename": "classifier-report.txt",
                },
            }
        },
        fetched_artifacts={
            "https://practiscore.com/results/match-200/report.txt": {
                "ok": True,
                "status": 200,
                "url": "https://practiscore.com/results/match-200/report.txt",
                "content_type": "text/plain",
                "text": "$INFO Region:USPSA\nD FirstName,LastName\n",
            }
        },
    )
    context = _FakeContext(landing_page, {"match-200": detail_page})

    artifacts = download_remote_match_artifacts(context, "match-200", tmp_path)

    assert artifacts.source_artifact_path.read_text(encoding="utf-8") == "$INFO Region:USPSA\nD FirstName,LastName\n"
    assert "Rendered HTML" in artifacts.html_path.read_text(encoding="utf-8")
    assert artifacts.summary_snapshot["artifact"]["source_name"] == "classifier-report.txt"
    assert artifacts.summary_snapshot["metadata"] == {"Range": "North Bay"}