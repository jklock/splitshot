"""Inventory-driven, one-action audit for ordinary SplitShot value controls.

This audit is deliberately narrower than the full browser interaction audit: it
does not claim button, drag, native-picker, or dialog coverage.  Instead it
turns every source-inventory row into an explicit PASS/FAIL/GAP record and
exercises each rendered ordinary input, select, or textarea exactly once.

The generated JSON is intended to be joined with the complete source inventory
so that an absent interaction can never disappear from the reported totals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from playwright.sync_api import Browser, Page, sync_playwright

from splitshot.browser.server import BrowserControlServer
from splitshot.ui.controller import ProjectController

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INVENTORY = ROOT / "tmp/codex/artifacts/complete-browser-control-source-inventory.json"
DEFAULT_REPORT = ROOT / "tmp/codex/artifacts/value-control-interaction-audit.json"
PRIMARY_FIXTURE = ROOT / "tests/fixtures/media/stage.mp4"
MERGE_FIXTURE = ROOT / "tests/fixtures/media/stage-merge.mp4"
PRACTISCORE_FIXTURE = ROOT / "example_data/IDPA/IDPA.csv"

PANE_TOOLS = (
    "project",
    "media",
    "merge",
    "trim-sync",
    "timing",
    "scoring",
    "markers",
    "overlay",
    "review",
    "export",
    "intro-outro",
    "queue",
    "metrics",
    "shotml",
    "settings",
)

# These value controls are not safe to generically mutate.  They have dedicated
# interaction semantics and remain visible as gaps in the report.
EXCLUDED_IDS: dict[str, str] = {
    "media-active-stage-label": "stage-name draft requires the adjacent Save action",
    "project-path": "project destination requires the create-project action",
    "project-output-root": "folder destination requires the native folder picker/save workflow",
    "merge-media-input": "native file picker",
    "media-add-more-input": "native file picker",
    "practiscore-file-input": "native file picker",
    "primary-file-input": "native file picker",
    "trim-global-start": "bulk-trim draft requires Apply All",
    "trim-global-end": "bulk-trim draft requires Apply All",
    "trim-video-scrubber": "playback transport is session-local and has no persistence contract",
    "scoring-preset": "preset changes dependent scoring structure and requires an isolated action case",
    "settings-scope": "storage scope routes later saves and is covered by the isolated settings audit",
    "settings-layout-locked": "layout draft persists only through the adjacent Save Current Settings action",
    "settings-layout-rail-width": "layout draft persists only through the adjacent Save Current Settings action",
    "settings-layout-inspector-width": "layout draft persists only through the adjacent Save Current Settings action",
    "settings-layout-waveform-height": "layout draft persists only through the adjacent Save Current Settings action",
    "export-preset": "preset selection and a paired quality edit intentionally resolve to Custom",
}

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
PRIMARY_MEDIA_PANES = {
    "media",
    "merge",
    "trim-sync",
    "timing",
    "scoring",
    "markers",
    "overlay",
    "review",
    "export",
    "intro-outro",
    "queue",
    "metrics",
}
PRACTISCORE_PANES = {
    "project",
    "scoring",
    "timing",
    "markers",
    "overlay",
    "review",
    "metrics",
    "intro-outro",
}

_INTERACTIVE_LITERAL_RE = re.compile(
    r"<(button|input|select|textarea|video)\b([^>]*)>", re.IGNORECASE | re.DOTALL
)
_QUOTED_ATTRIBUTE_RE = re.compile(
    r"""([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*(["'])(.*?)\2""", re.DOTALL
)


@dataclass(slots=True)
class Proof:
    inventory_identity: str
    pane: str | None
    status: str
    reason: str
    before: Any = None
    intended_after: Any = None
    immediate_after: Any = None
    immediate_same_node: bool | None = None
    immediate_connected: bool | None = None
    event_counts: dict[str, int] = field(default_factory=dict)
    paired_with: str | None = None
    settled_after: Any = None
    settled_same_node: bool | None = None
    settled_connected: bool | None = None
    mutating_requests: list[dict[str, Any]] = field(default_factory=list)
    pair_mutation_count: int = 0
    after_pane_return: Any = None
    after_project_reopen: Any = None
    project_file_changed: bool | None = None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory-json", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--browser",
        choices=("chromium", "chrome", "firefox", "webkit"),
        default="chromium",
    )
    parser.add_argument("--headed", action="store_true")
    parser.add_argument(
        "--default-visible-only",
        action="store_true",
        help="Exercise only controls visible without opening nested workbenches.",
    )
    parser.add_argument(
        "--pane",
        action="append",
        choices=PANE_TOOLS,
        dest="panes",
        help="Limit runtime exercise to one or more panes; all panes are inventoried regardless.",
    )
    return parser.parse_args()


def _literal_identity(attributes: dict[str, str]) -> str | None:
    if attributes.get("id"):
        return attributes["id"]
    for name, value in attributes.items():
        if name.startswith("data-"):
            return f"[{name}={value}]"
    classes = attributes.get("class", "").split()
    return f".{classes[0]}" if classes else None


def build_source_inventory(path: Path = DEFAULT_INVENTORY) -> list[dict[str, Any]]:
    """Build the literal-control inventory when no prior audit artifact exists."""
    controls: list[dict[str, Any]] = []
    sources = [ROOT / "src/splitshot/browser/static/index.html"]
    sources.extend(sorted((ROOT / "src/splitshot/browser/static").rglob("*.js")))
    for source in sources:
        text = source.read_text(encoding="utf-8")
        for match in _INTERACTIVE_LITERAL_RE.finditer(text):
            raw_attributes = match.group(2)
            attributes = {
                item.group(1): item.group(3)
                for item in _QUOTED_ATTRIBUTE_RE.finditer(raw_attributes)
            }
            if attributes.get("type", "").lower() == "hidden" or re.search(
                r"\breadonly(?:\s|/|$)", raw_attributes, re.IGNORECASE
            ):
                continue
            identity = _literal_identity(attributes)
            if not identity:
                continue
            controls.append(
                {
                    "identity": identity,
                    "tag": match.group(1).lower(),
                    "input_type": attributes.get("type", "").lower(),
                    "file": str(source.relative_to(ROOT)),
                    "line": text.count("\n", 0, match.start()) + 1,
                    "attributes": attributes,
                    "action_refs": [],
                }
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"count": len(controls), "controls": controls}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return controls


def _read_inventory(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return build_source_inventory(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    controls = payload.get("controls") if isinstance(payload, dict) else None
    if not isinstance(controls, list):
        raise TypeError(f"Inventory does not contain a controls list: {path}")
    return [item for item in controls if isinstance(item, dict)]


def _ordinary_value_row(row: dict[str, Any]) -> bool:
    tag = str(row.get("tag") or "").lower()
    input_type = str(row.get("input_type") or "").lower()
    return tag in {"select", "textarea"} or (
        tag == "input"
        and input_type not in {"button", "file", "hidden", "image", "reset", "submit"}
    )


def _identity_selector(identity: str) -> str | None:
    if identity.startswith(("#", ".", "[")):
        return identity
    if identity.startswith("id:"):
        return f"#{identity[3:]}"
    if identity.startswith("data-") and ":" in identity:
        attribute, value = identity.split(":", 1)
        return f'[{attribute}="{value}"]'
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", identity):
        return f"#{identity}"
    return None


def _file_digest(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _upload_fixture(base_url: str, endpoint: str, path: Path) -> None:
    """Upload a repo fixture without treating picker automation as UI proof."""
    boundary = uuid.uuid4().hex
    data = path.read_bytes()
    body = (
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode("latin-1")
        + data
        + f"\r\n--{boundary}--\r\n".encode("latin-1")
    )
    request = Request(
        f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urlopen(request, timeout=120) as response:
        if response.status >= 400:
            raise RuntimeError(f"fixture upload failed: {endpoint} -> {response.status}")


def _install_request_probe(page: Page) -> None:
    page.evaluate(
        """() => {
          if (window.__valueAuditFetchInstalled) return;
          window.__valueAuditFetchInstalled = true;
          window.__valueAuditRequests = [];
          const originalFetch = window.fetch.bind(window);
          window.fetch = async (...args) => {
            const request = args[0];
            const options = args[1] || {};
            const method = String(options.method || request?.method || 'GET').toUpperCase();
            const url = String(typeof request === 'string' ? request : request?.url || '');
            const started = performance.now();
            try {
              const response = await originalFetch(...args);
              window.__valueAuditRequests.push({ method, url, status: response.status, started, finished: performance.now() });
              return response;
            } catch (error) {
              window.__valueAuditRequests.push({ method, url, status: 0, started, finished: performance.now(), error: String(error) });
              throw error;
            }
          };
        }"""
    )


def _discover_pane_controls(page: Page, pane: str) -> list[dict[str, Any]]:
    page.locator(f'[data-tool="{pane}"]').click()
    page.wait_for_timeout(80)
    return page.evaluate(
        """(pane) => {
          const visible = (node) => {
            const style = getComputedStyle(node);
            const rect = node.getBoundingClientRect();
            return !node.disabled && !node.readOnly && style.display !== 'none'
              && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
          };
          const identity = (node) => {
            if (node.id) return `#${CSS.escape(node.id)}`;
            const preferred = [
              'data-shotml-setting', 'data-text-box-field', 'data-popup-field',
              'data-merge-source-field', 'data-stage-field', 'data-intro-outro-field',
              'data-field', 'name'
            ];
            for (const attr of preferred) {
              const value = node.getAttribute(attr);
              if (value) return `[${attr}="${CSS.escape(value)}"]`;
            }
            return null;
          };
          const seen = new Map();
          return [...document.querySelectorAll('input:not([type="hidden"]), select, textarea')]
            .filter(visible)
            .map((node) => {
              const base = identity(node);
              if (!base) return null;
              const occurrence = seen.get(base) || 0;
              seen.set(base, occurrence + 1);
              return {
                pane,
                selector: base,
                occurrence,
                tag: node.tagName.toLowerCase(),
                type: String(node.type || '').toLowerCase(),
                id: node.id || '',
              };
            })
            .filter(Boolean);
        }""",
        pane,
    )


def _reveal_pane_value_controls(page: Page, pane: str) -> None:
    page.locator(f'[data-tool="{pane}"]').click()
    page.wait_for_timeout(80)
    expanders = {
        "scoring": "#expand-scoring",
        "timing": "#expand-timing",
        "metrics": "#expand-metrics",
    }
    selector = expanders.get(pane)
    if selector and page.locator(selector).is_visible():
        page.locator(selector).click()
        page.wait_for_timeout(80)
    if pane == "shotml":
        page.evaluate(
            """() => document.querySelectorAll('[data-shotml-section].collapsed').forEach((section) => {
              section.querySelector(':scope > .section-header [data-section-toggle]')?.click();
            })"""
        )
        page.wait_for_timeout(120)
    elif pane == "settings":
        page.evaluate(
            """() => document.querySelectorAll('[data-settings-section].collapsed').forEach((section) => {
              section.querySelector(':scope > .section-header [data-section-toggle]')?.click();
            })"""
        )
        page.wait_for_timeout(120)
    elif pane == "markers" and page.locator("#popup-edit-selected").is_visible():
        page.locator("#popup-edit-selected").click()
        page.wait_for_timeout(80)
        if page.locator("#popup-import-shots-workbench").is_visible():
            page.locator("#popup-import-shots-workbench").click()
            page.wait_for_timeout(150)
    elif pane == "review":
        page.locator("#review-add-text-box").click()
        page.locator("#review-add-imported-box").click()
        page.wait_for_timeout(150)
    elif pane == "intro-outro":
        page.locator("#intro-outro-add-text").click()
        page.wait_for_timeout(100)
        page.locator("#intro-outro-add-match").click()
        page.wait_for_timeout(150)


def _arm_and_interact(page: Page, case: dict[str, Any], slot: str) -> dict[str, Any]:
    return page.evaluate(
        """({ selector, occurrence, slot }) => {
          const node = document.querySelectorAll(selector)[occurrence];
          if (!(node instanceof HTMLInputElement || node instanceof HTMLSelectElement || node instanceof HTMLTextAreaElement)) {
            return { error: 'control disappeared before interaction' };
          }
          const valueOf = (el) => el instanceof HTMLInputElement && (el.type === 'checkbox' || el.type === 'radio')
            ? el.checked : el.value;
          const before = valueOf(node);
          let intended;
          const counts = { click: 0, input: 0, change: 0, blur: 0 };
          for (const eventName of Object.keys(counts)) node.addEventListener(eventName, () => { counts[eventName] += 1; });
          window[`__valueAuditNode_${slot}`] = node;
          window[`__valueAuditCounts_${slot}`] = counts;

          if (node instanceof HTMLInputElement && node.type === 'checkbox') {
            intended = !node.checked;
            node.click();
          } else if (node instanceof HTMLInputElement && node.type === 'radio') {
            if (node.checked) return { skipped: 'already-selected radio has no one-click alternate value', before };
            intended = true;
            node.click();
          } else if (node instanceof HTMLSelectElement) {
            const options = [...node.options].filter((option) => !option.disabled && option.value !== '' && option.value !== node.value);
            if (!options.length) return { skipped: 'select has no alternate enabled option', before };
            intended = options[0].value;
            node.value = intended;
            node.dispatchEvent(new Event('change', { bubbles: true }));
          } else {
            const type = node instanceof HTMLInputElement ? node.type : 'textarea';
            if (type === 'number' || type === 'range') {
              const min = Number.isFinite(Number(node.min)) && node.min !== '' ? Number(node.min) : -100000;
              const max = Number.isFinite(Number(node.max)) && node.max !== '' ? Number(node.max) : 100000;
              const step = Number.isFinite(Number(node.step)) && Number(node.step) > 0 ? Number(node.step) : 1;
              const current = Number(node.value || 0);
              const candidate = current + step <= max ? current + step : current - step;
              intended = String(Math.max(min, Math.min(max, candidate)));
            } else if (type === 'color') {
              intended = String(node.value).toLowerCase() === '#123456' ? '#654321' : '#123456';
            } else if (type === 'time') {
              intended = String(node.value) === '00:01' ? '00:02' : '00:01';
            } else {
              intended = `${String(node.value).slice(0, 80)} audit`.trim();
            }
            node.focus();
            node.value = intended;
            node.dispatchEvent(new Event('input', { bubbles: true }));
            node.dispatchEvent(new Event('change', { bubbles: true }));
          }
          return {
            before,
            intended,
            immediate: valueOf(node),
            sameNode: window[`__valueAuditNode_${slot}`] === node,
            connected: node.isConnected,
            counts: { ...counts },
          };
        }""",
        {**case, "slot": slot},
    )


def _read_armed(page: Page, case: dict[str, Any], slot: str) -> dict[str, Any]:
    return page.evaluate(
        """({ selector, occurrence, slot }) => {
          const original = window[`__valueAuditNode_${slot}`];
          const current = document.querySelectorAll(selector)[occurrence];
          const valueOf = (el) => el instanceof HTMLInputElement && (el.type === 'checkbox' || el.type === 'radio')
            ? el.checked : el?.value;
          return {
            value: valueOf(current),
            sameNode: original === current,
            connected: Boolean(original?.isConnected),
            counts: { ...(window[`__valueAuditCounts_${slot}`] || {}) },
          };
        }""",
        {**case, "slot": slot},
    )


def _read_fresh(page: Page, case: dict[str, Any]) -> Any:
    return page.evaluate(
        """({ selector, occurrence }) => {
          const node = document.querySelectorAll(selector)[occurrence];
          if (node instanceof HTMLInputElement && (node.type === 'checkbox' || node.type === 'radio')) return node.checked;
          return node?.value;
        }""",
        case,
    )


def _values_match(case: dict[str, Any], actual: Any, expected: Any) -> bool:
    if case.get("type") in {"number", "range"}:
        try:
            return abs(float(actual) - float(expected)) < 1e-9
        except (TypeError, ValueError):
            return False
    return actual == expected


def _mutating_requests(page: Page) -> list[dict[str, Any]]:
    requests = page.evaluate("() => [...(window.__valueAuditRequests || [])]")
    return [
        item
        for item in requests
        if str(item.get("method", "")).upper() in MUTATING_METHODS
        and not str(item.get("url", "")).endswith("/api/activity")
        and not str(item.get("url", "")).endswith("/api/project/ui-state")
    ]


def _source_identity_for_runtime(case: dict[str, Any], rows: list[dict[str, Any]]) -> str | None:
    def normalized(selector: str) -> str:
        return re.sub(r"""(\[[^=\]]+=)["']([^"']+)["']\]""", r"\1\2]", selector)

    selector = normalized(case["selector"])
    for row in rows:
        source_selector = _identity_selector(str(row.get("identity") or ""))
        if source_selector is not None and normalized(source_selector) == selector:
            return str(row["identity"])
    return None


def _exercise_pair(
    page: Page,
    pane: str,
    first: dict[str, Any],
    second: dict[str, Any] | None,
    project_path: Path,
    inventory_rows: list[dict[str, Any]],
) -> list[Proof]:
    page.evaluate("() => { window.__valueAuditRequests = []; }")
    project_file = project_path / "project.json"
    digest_before = _file_digest(project_file)
    first_result = _arm_and_interact(page, first, "a")
    second_result = _arm_and_interact(page, second, "b") if second else None
    page.evaluate(
        "() => document.activeElement instanceof HTMLElement && document.activeElement.blur()"
    )
    page.wait_for_timeout(1300)
    settled_first = _read_armed(page, first, "a") if not first_result.get("skipped") else {}
    settled_second = (
        _read_armed(page, second, "b")
        if second and second_result and not second_result.get("skipped")
        else {}
    )
    requests = _mutating_requests(page)
    digest_after = _file_digest(project_file)

    # Pane navigation is explicitly structural.  Re-query the fresh nodes and
    # verify the values, but do not require DOM identity across navigation.
    other_pane = "project" if pane != "project" else "metrics"
    page.locator(f'[data-tool="{other_pane}"]').click()
    page.locator(f'[data-tool="{pane}"]').click()
    page.wait_for_timeout(120)
    after_return_first = _read_fresh(page, first)
    after_return_second = _read_fresh(page, second) if second else None

    page.evaluate("path => useProjectFolder(path)", str(project_path))
    page.wait_for_function(
        "path => state?.project?.path === path", arg=str(project_path), timeout=15_000
    )
    page.locator(f'[data-tool="{pane}"]').click()
    page.wait_for_timeout(120)
    after_reopen_first = _read_fresh(page, first)
    after_reopen_second = _read_fresh(page, second) if second else None

    pair_requests = requests
    proofs: list[Proof] = []
    for case, result, settled, returned, reopened, partner in (
        (first, first_result, settled_first, after_return_first, after_reopen_first, second),
        (second, second_result, settled_second, after_return_second, after_reopen_second, first),
    ):
        if case is None or result is None:
            continue
        identity = _source_identity_for_runtime(case, inventory_rows) or case["selector"]
        if result.get("error") or result.get("skipped"):
            proofs.append(
                Proof(
                    inventory_identity=identity,
                    pane=pane,
                    status="gap",
                    reason=str(result.get("error") or result.get("skipped")),
                    before=result.get("before"),
                    paired_with=partner["selector"] if partner else None,
                )
            )
            continue
        intended = result["intended"]
        passed = (
            _values_match(case, result["immediate"], intended)
            and result["sameNode"] is True
            and result["connected"] is True
            and _values_match(case, settled.get("value"), intended)
            and settled.get("sameNode") is True
            and settled.get("connected") is True
            and _values_match(case, returned, intended)
            and _values_match(case, reopened, intended)
            and len(pair_requests) <= (2 if second else 1)
            and all(200 <= int(request.get("status", 0)) < 300 for request in pair_requests)
        )
        reasons: list[str] = []
        if not _values_match(case, result["immediate"], intended):
            reasons.append("visible value did not change immediately")
        if not result["sameNode"] or not result["connected"]:
            reasons.append("node was replaced/disconnected during the action")
        if not _values_match(case, settled.get("value"), intended):
            reasons.append("value reverted after debounce/API work")
        if not settled.get("sameNode") or not settled.get("connected"):
            reasons.append("ordinary save replaced/disconnected the active node")
        if not _values_match(case, returned, intended):
            reasons.append("value was lost after pane navigation")
        if not _values_match(case, reopened, intended):
            reasons.append("value was lost after project reopen")
        if len(pair_requests) > (2 if second else 1):
            reasons.append(f"pair emitted {len(pair_requests)} mutating API requests")
        if any(not 200 <= int(request.get("status", 0)) < 300 for request in pair_requests):
            reasons.append("a mutating API request failed")
        proofs.append(
            Proof(
                inventory_identity=identity,
                pane=pane,
                status="pass" if passed else "fail",
                reason=(
                    "all one-action persistence assertions passed" if passed else "; ".join(reasons)
                ),
                before=result["before"],
                intended_after=intended,
                immediate_after=result["immediate"],
                immediate_same_node=result["sameNode"],
                immediate_connected=result["connected"],
                event_counts=result["counts"],
                paired_with=partner["selector"] if partner else None,
                settled_after=settled.get("value"),
                settled_same_node=settled.get("sameNode"),
                settled_connected=settled.get("connected"),
                mutating_requests=pair_requests,
                pair_mutation_count=len(pair_requests),
                after_pane_return=returned,
                after_project_reopen=reopened,
                project_file_changed=digest_before != digest_after,
            )
        )
    return proofs


def _initial_gap(row: dict[str, Any]) -> Proof:
    identity = str(row.get("identity") or "")
    tag = str(row.get("tag") or "").lower()
    input_type = str(row.get("input_type") or "").lower()
    if tag == "button":
        reason = "button action is outside the ordinary-value harness"
    elif input_type == "file":
        reason = "native file picker requires a dedicated picker audit"
    elif not _ordinary_value_row(row):
        reason = (
            f"{tag or 'unknown'} {input_type or 'control'} is outside the ordinary-value harness"
        )
    else:
        reason = (
            "ordinary value control was not rendered with the audit fixture or requires a "
            "prerequisite"
        )
    return Proof(inventory_identity=identity, pane=None, status="gap", reason=reason)


def run(args: argparse.Namespace) -> dict[str, Any]:
    inventory_rows = _read_inventory(args.inventory_json)
    proofs_by_identity = {
        str(row.get("identity") or ""): _initial_gap(row) for row in inventory_rows
    }
    runtime_extra: list[Proof] = []
    panes = tuple(args.panes or PANE_TOOLS)

    with tempfile.TemporaryDirectory(
        prefix="value-control-audit-", dir=ROOT / "tmp/codex"
    ) as temp_dir:
        controller = ProjectController()
        server = BrowserControlServer(controller=controller, port=0, log_level="off")
        server.start_background(open_browser=False)
        try:
            with sync_playwright() as playwright:
                browser_type = (
                    playwright.chromium
                    if args.browser == "chrome"
                    else getattr(playwright, args.browser)
                )
                launch_options = {"headless": not args.headed}
                if args.browser == "chrome":
                    launch_options["channel"] = "chrome"
                browser: Browser = browser_type.launch(**launch_options)
                try:
                    page = browser.new_page(viewport={"width": 1440, "height": 1024})
                    for pane in panes:
                        # Each pane receives a clean browser document and clean
                        # project.  Generic audit values from one surface must
                        # not create false failures in a later surface.
                        project_path = Path(temp_dir) / f"{pane}-interaction-audit.ssproj"
                        page.goto(server.url, wait_until="domcontentloaded")
                        page.wait_for_selector("#current-file")
                        page.evaluate("path => createNewProject(path)", str(project_path))
                        page.wait_for_function(
                            "path => state?.project?.path === path",
                            arg=str(project_path),
                            timeout=15_000,
                        )
                        fixture_changed = False
                        if (
                            not args.default_visible_only
                            and pane in PRACTISCORE_PANES
                            and PRACTISCORE_FIXTURE.is_file()
                        ):
                            _upload_fixture(
                                server.url,
                                "/api/files/practiscore",
                                PRACTISCORE_FIXTURE,
                            )
                            fixture_changed = True
                        if pane in PRIMARY_MEDIA_PANES and PRIMARY_FIXTURE.is_file():
                            _upload_fixture(server.url, "/api/files/primary", PRIMARY_FIXTURE)
                            fixture_changed = True
                            if pane in {"merge", "trim-sync"} and MERGE_FIXTURE.is_file():
                                _upload_fixture(server.url, "/api/files/merge", MERGE_FIXTURE)
                        if fixture_changed:
                            page.evaluate("async () => { await refresh(); }")
                        _install_request_probe(page)
                        if not args.default_visible_only:
                            _reveal_pane_value_controls(page, pane)
                        page.wait_for_timeout(700)
                        controls = _discover_pane_controls(page, pane)
                        candidates = []
                        for control in controls:
                            if control["type"] == "file":
                                continue
                            if control["id"] in EXCLUDED_IDS:
                                identity = f"#{control['id']}"
                                proof = Proof(
                                    inventory_identity=identity,
                                    pane=pane,
                                    status="gap",
                                    reason=EXCLUDED_IDS[control["id"]],
                                )
                                if identity in proofs_by_identity:
                                    proofs_by_identity[identity] = proof
                                else:
                                    runtime_extra.append(proof)
                                continue
                            # The standalone audit process must never touch the
                            # user's app-level settings file. Pytest's isolated
                            # settings suite owns these controls.
                            if pane == "settings":
                                identity = (
                                    _source_identity_for_runtime(control, inventory_rows)
                                    or control["selector"]
                                )
                                proof = Proof(
                                    inventory_identity=identity,
                                    pane=pane,
                                    status="gap",
                                    reason="delegated to the isolated settings persistence audit",
                                )
                                if identity in proofs_by_identity:
                                    proofs_by_identity[identity] = proof
                                else:
                                    runtime_extra.append(proof)
                                continue
                            candidates.append(control)

                        for index in range(0, len(candidates), 2):
                            # Re-enter before each pair because the preceding
                            # pair ends with a full project reopen.
                            page.locator(f'[data-tool="{pane}"]').click()
                            partner_selector = (
                                candidates[index + 1]["selector"]
                                if index + 1 < len(candidates)
                                else "-"
                            )
                            print(
                                f"audit pair {pane}: {candidates[index]['selector']} / "
                                f"{partner_selector}",
                                flush=True,
                            )
                            pair = _exercise_pair(
                                page,
                                pane,
                                candidates[index],
                                candidates[index + 1] if index + 1 < len(candidates) else None,
                                project_path,
                                inventory_rows,
                            )
                            for proof in pair:
                                if proof.inventory_identity in proofs_by_identity:
                                    existing = proofs_by_identity[proof.inventory_identity]
                                    # Multiple live rows sharing one source
                                    # identity are retained as runtime cases.
                                    if existing.status not in {"gap"}:
                                        if proof.status == "fail" and existing.status != "fail":
                                            runtime_extra.append(existing)
                                            proofs_by_identity[proof.inventory_identity] = proof
                                        else:
                                            runtime_extra.append(proof)
                                    else:
                                        proofs_by_identity[proof.inventory_identity] = proof
                                else:
                                    runtime_extra.append(proof)
                finally:
                    browser.close()
        finally:
            server.shutdown()

    proofs = [*proofs_by_identity.values(), *runtime_extra]
    source_definition_coverage = []
    for row in inventory_rows:
        identity = str(row.get("identity") or "")
        proof = proofs_by_identity[identity]
        source_definition_coverage.append(
            {
                "identity": identity,
                "file": row.get("file"),
                "line": row.get("line"),
                "status": proof.status,
                "reason": proof.reason,
            }
        )
    counts = {
        "source_definitions": len(inventory_rows),
        "inventory_identities": len(proofs_by_identity),
        "reported_cases": len(proofs),
        "runtime_cases": sum(1 for item in proofs if item.pane is not None),
        "passed": sum(1 for item in proofs if item.status == "pass"),
        "failed": sum(1 for item in proofs if item.status == "fail"),
        "gaps": sum(1 for item in proofs if item.status == "gap"),
        "source_definitions_passed": sum(
            1 for item in source_definition_coverage if item["status"] == "pass"
        ),
        "source_definitions_failed": sum(
            1 for item in source_definition_coverage if item["status"] == "fail"
        ),
        "source_definitions_gaps": sum(
            1 for item in source_definition_coverage if item["status"] == "gap"
        ),
    }
    return {
        "generated_at_epoch_s": time.time(),
        "browser": args.browser,
        "panes": list(panes),
        "inventory_path": str(args.inventory_json),
        "scope": (
            "ordinary rendered value controls only; buttons/drags/pickers/dialogs are explicit gaps"
        ),
        "counts": counts,
        "cases": [asdict(item) for item in proofs],
        "source_definition_coverage": source_definition_coverage,
    }


def _markdown_value(value: Any) -> str:
    rendered = json.dumps(value, sort_keys=True) if not isinstance(value, str) else value
    return rendered.replace("|", "\\|").replace("\n", " ")


def _write_markdown(payload: dict[str, Any], path: Path) -> None:
    counts = payload["counts"]
    lines = [
        "# SplitShot ordinary value-control interaction audit",
        "",
        f"Browser: `{payload['browser']}`",
        "",
        (
            f"Source definitions: {counts['source_definitions']}; unique inventory identities: "
            f"{counts['inventory_identities']}; runtime cases: {counts['runtime_cases']}; "
            f"pass: {counts['passed']}; fail: {counts['failed']}; gap: {counts['gaps']}."
        ),
        "",
        (
            "Buttons, drags, file/folder pickers, native dialogs, and status-only nodes are "
            "gaps in this audit, never implicit passes."
        ),
        "",
        "## Runtime interaction proof",
        "",
        (
            "| Interaction | Pane | Result | Before | Intended | Immediate | Settled | "
            "Pane return | Reopen | Events | Pair API mutations | Reason |"
        ),
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- |",
    ]
    for case in payload["cases"]:
        if case["pane"] is None:
            continue
        lines.append(
            "| "
            + " | ".join(
                [
                    _markdown_value(case["inventory_identity"]),
                    _markdown_value(case["pane"]),
                    case["status"].upper(),
                    _markdown_value(case["before"]),
                    _markdown_value(case["intended_after"]),
                    _markdown_value(case["immediate_after"]),
                    _markdown_value(case["settled_after"]),
                    _markdown_value(case["after_pane_return"]),
                    _markdown_value(case["after_project_reopen"]),
                    _markdown_value(case["event_counts"]),
                    str(case["pair_mutation_count"]),
                    _markdown_value(case["reason"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Complete source-definition disposition",
            "",
            "| Interaction | Source | Result | Reason |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in payload["source_definition_coverage"]:
        source = f"{item.get('file', '')}:{item.get('line', '')}"
        lines.append(
            f"| {_markdown_value(item['identity'])} | {_markdown_value(source)} | "
            f"{item['status'].upper()} | {_markdown_value(item['reason'])} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = _parse_args()
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    payload = run(args)
    args.report_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    markdown_path = args.report_json.with_suffix(".md")
    _write_markdown(payload, markdown_path)
    print(json.dumps(payload["counts"], indent=2))
    print(f"report: {args.report_json}")
    print(f"report: {markdown_path}")
    return 1 if payload["counts"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
