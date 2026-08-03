from __future__ import annotations

import argparse
import json
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PANE_DIR = ROOT / "src" / "splitshot" / "browser" / "static" / "panes"
SERVER_PATH = ROOT / "src" / "splitshot" / "browser" / "server.py"
CONTROLLER_PATH = ROOT / "src" / "splitshot" / "ui" / "controller.py"
QA_MATRIX_PATH = ROOT / "docs" / "project" / "browser-control-qa-matrix.md"
PANE_OWNERSHIP_PATH = ROOT / "docs" / "project" / "browser-pane-ownership.md"
DEFAULT_ARTIFACT_ROOT = ROOT / "artifacts" / "pane-function-audit"

PANE_FILES = {
    "Project": "project-pane.js",
    "Media": "media-pane.js",
    "Compose": "merge-pane.js",
    "Trim": "trim-sync-pane.js",
    "Score": "scoring-pane.js",
    "Splits": "timing-pane.js",
    "Markers": "markers-pane.js",
    "Overlay": "overlay-pane.js",
    "Review": "review-pane.js",
    "Export": "export-pane.js",
    "In / Out": "intro-outro-pane.js",
    "Queue": "queue-pane.js",
    "Metrics": "metrics-pane.js",
    "ShotML": "shotml-pane.js",
    "Settings": "settings-pane.js",
}

PANE_MATRIX_LABELS = {
    "Project": "Project / import",
    "Media": "Media",
    "Compose": "Compose",
    "Trim": "Trim",
    "Score": "Score",
    "Splits": "Splits / waveform",
    "Markers": "Markers / Review / Overlay",
    "Overlay": "Markers / Review / Overlay",
    "Review": "Markers / Review / Overlay",
    "Export": "Export",
    "In / Out": "In / Out",
    "Queue": "Queue",
    "Metrics": "Metrics",
    "ShotML": "ShotML",
    "Settings": "Settings",
}

TEST_GLOBS = (
    "tests/browser/test_*.py",
    "tests/export/test_*.py",
    "tests/analysis/test_*.py",
)


@dataclass(slots=True)
class FunctionAuditRow:
    pane_owner: str
    pane_file: str
    function_name: str
    function_type: str
    primary_controls: list[str]
    upstream_inputs: list[str]
    downstream_effects: list[str]
    route_paths: list[str]
    server_methods: list[str]
    controller_methods: list[str]
    persisted_state_paths: list[str]
    visible_truth_targets: list[str]
    affects_export_queue_runtime: bool
    mutates_persisted_project_state: bool
    changes_visible_truth: bool
    proof_sources: list[str]
    proof_strength: str
    defect_flags: list[str]
    remediation_required: list[str]
    closure_status: str


@dataclass(slots=True)
class PaneFunctionAudit:
    rows: list[FunctionAuditRow]
    generated_from: dict[str, str]

    @property
    def open_rows(self) -> list[FunctionAuditRow]:
        return [row for row in self.rows if row.closure_status != "closed"]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _strip_prefix(value: str, prefix: str) -> str:
    return value.removeprefix(prefix)


def _extract_functions(path: Path) -> list[tuple[str, str]]:
    text = _read_text(path)
    pattern = re.compile(r"(?:async\s+)?function\s+([A-Za-z0-9_]+)\s*\(")
    matches = list(pattern.finditer(text))
    functions: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        name = match.group(1)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.start() : end]
        functions.append((name, body))
    return functions


def _parse_qa_matrix() -> dict[str, list[str]]:
    matrix_text = _read_text(QA_MATRIX_PATH)
    pane_tests: dict[str, list[str]] = {}
    for line in matrix_text.splitlines():
        if not line.startswith("| ") or line.startswith("| ---"):
            continue
        parts = [part.strip() for part in line.split("|")[1:-1]]
        if len(parts) < 3 or parts[0] in {"Surface", "Shared shell"}:
            continue
        tests = [token.strip("` ") for token in parts[2].split(";") if token.strip()]
        pane_tests[parts[0]] = tests
    return pane_tests


def _parse_server_routes() -> dict[str, str]:
    text = _read_text(SERVER_PATH)
    return dict(re.findall(r'"(/api/[^"]+)":\s*self\.(_[A-Za-z0-9_]+)', text))


def _parse_server_controller_calls() -> dict[str, list[str]]:
    text = _read_text(SERVER_PATH)
    mapping: dict[str, list[str]] = {}
    for match in re.finditer(
        r"def\s+(_[A-Za-z0-9_]+)\(self,\s*[^)]*\)\s*->\s*None:\n",
        text,
    ):
        method_name = match.group(1)
        body_start = match.end()
        next_def = text.find("\n            def ", body_start)
        body = text[body_start : next_def if next_def != -1 else len(text)]
        controller_calls = re.findall(r"controller\.([A-Za-z0-9_]+)\(", body)
        if controller_calls:
            mapping[method_name] = sorted(set(controller_calls))
    return mapping


def _parse_controller_method_bodies() -> dict[str, str]:
    text = _read_text(CONTROLLER_PATH)
    bodies: dict[str, str] = {}
    for match in re.finditer(r"\n    def\s+([A-Za-z0-9_]+)\(", text):
        name = match.group(1)
        body_start = text.find(":\n", match.start()) + 2
        next_match = re.search(r"\n    def\s+[A-Za-z0-9_]+\(", text[body_start:])
        body_end = body_start + next_match.start() if next_match else len(text)
        bodies[name] = text[body_start:body_end]
    return bodies


def _load_test_corpus() -> dict[str, str]:
    corpus: dict[str, str] = {}
    for pattern in TEST_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            corpus[str(path.relative_to(ROOT))] = _read_text(path)
    return corpus


def _selectors_from_body(body: str) -> list[str]:
    selectors: set[str] = set()
    for match in re.finditer(r"querySelector(?:All)?\((['\"`])(.+?)\1\)", body, re.DOTALL):
        selectors.add(match.group(2).strip())
    for match in re.finditer(r"getElementById\((['\"`])(.+?)\1\)", body):
        selectors.add(f"#{match.group(2).strip()}")
    for match in re.finditer(r"\$\((['\"])(.+?)\1\)", body):
        selectors.add(f"#{match.group(2).strip()}")
    for match in re.finditer(r'\bid=["\']([A-Za-z0-9_-]+)["\']', body):
        selectors.add(f"#{match.group(1)}")
    for match in re.finditer(
        r'\b(data-[A-Za-z0-9_-]+)=["\']([^"\']+)["\']', body
    ):
        attribute, value = match.groups()
        selectors.add(
            f"[{attribute}]" if "${" in value else f'[{attribute}="{value}"]'
        )
    return sorted(selectors)


def _routes_from_body(body: str) -> list[str]:
    return sorted(
        set(
            re.findall(
                r"(?:callApi\(|queueSave\([^,]+,)\s*(['\"])(/api/[^'\"]+)\1",
                body,
            )
        )
    )


def _normalized_routes(route_matches: list[tuple[str, str]]) -> list[str]:
    return [route for _, route in route_matches]


def _controller_assignments(body: str) -> list[str]:
    project_paths = re.findall(
        r"(self\.project\.[A-Za-z0-9_\.]+|stage\.[A-Za-z0-9_\.]+|source\.[A-Za-z0-9_\.]+)\s*=",
        body,
    )
    return sorted(set(project_paths))


def _downstream_effects(body: str) -> list[str]:
    effects: set[str] = set()
    for token in (
        "self.analyze_primary(",
        "self.analyze_secondary(",
        "_sync_project_to_active_stage(",
        "_sync_active_stage_to_project(",
        "_mark_stage_queue_stale(",
        "self.project_changed.emit(",
        "self.settings_changed.emit(",
        "_refresh_secondary_analysis_projection(",
    ):
        if token in body:
            effects.add(token.replace("(", ""))
    return sorted(effects)


def _visible_truth_targets(body: str, selectors: Iterable[str], routes: Iterable[str]) -> list[str]:
    targets: set[str] = set()
    haystack = f"{body}\n{' '.join(selectors)}\n{' '.join(routes)}".lower()
    for token, label in (
        ("waveform", "waveform"),
        ("preview", "preview"),
        ("merge", "compose-preview"),
        ("trim", "trim-state"),
        ("review", "review-output"),
        ("overlay", "overlay-preview"),
        ("queue", "queue-state"),
        ("export", "export-settings"),
        ("metrics", "metrics-output"),
        ("shotml", "shotml-output"),
        ("status", "status-bar"),
        ("primary", "primary-media"),
        ("secondary", "secondary-media"),
    ):
        if token in haystack:
            targets.add(label)
    return sorted(targets)


def _classify_function(name: str, body: str, selectors: list[str], routes: list[str]) -> str:
    lowered = name.lower()
    if routes:
        return "browser-action"
    if any(token in lowered for token in ("render", "build", "append", "position", "create")):
        if any(
            token in body.lower() for token in ("waveform", "preview", "canvas", "svg", "video")
        ):
            return "preview/waveform renderer"
        return "render-only"
    if any(
        token in lowered
        for token in (
            "current",
            "active",
            "read",
            "normalize",
            "format",
            "label",
            "meta",
            "value",
            "payload",
            "summary",
            "state",
        )
    ):
        return "derived-state builder"
    if "addEventListener" in body or selectors:
        return "local-ui-state"
    return "render-only"


def _proof_evidence(
    pane_owner: str,
    function_name: str,
    selectors: list[str],
    routes: list[str],
    pane_tests: list[str],
    test_corpus: dict[str, str],
) -> tuple[list[str], str]:
    direct_hits: list[str] = []
    search_terms = {function_name, *routes}
    for selector in selectors:
        selector = selector.strip()
        if selector.startswith("#"):
            search_terms.add(selector[1:])
            search_terms.add(selector)
        elif selector.startswith(("[data-", ".")):
            search_terms.add(selector)
        for token in re.findall(
            r"(#[A-Za-z0-9_-]+|\.[A-Za-z0-9_-]+|\[data-[A-Za-z0-9_-]+)", selector
        ):
            search_terms.add(token)
            if token.startswith("#"):
                search_terms.add(token[1:])
    for path, content in test_corpus.items():
        if any(term and term in content for term in search_terms):
            direct_hits.append(path)
    direct_hits = sorted(set(direct_hits))
    if direct_hits:
        visible_hit = any(
            any(
                token in test_corpus[path]
                for token in (
                    "page.locator",
                    "get_by_role",
                    "inner_text",
                    "wait_for_function",
                    "screenshot",
                )
            )
            for path in direct_hits
        )
        state_only = all(
            "page.locator" not in test_corpus[path]
            and "get_by_role" not in test_corpus[path]
            and "wait_for_function" not in test_corpus[path]
            for path in direct_hits
        )
        if visible_hit:
            return direct_hits, "fully proved by visible-result test"
        pane_visible_hits = [
            path
            for path in pane_tests
            if path in test_corpus
            and any(
                token in test_corpus[path]
                for token in (
                    "page.locator",
                    "get_by_role",
                    "inner_text",
                    "wait_for_function",
                    "screenshot",
                )
            )
        ]
        if state_only and pane_visible_hits:
            return sorted(
                set(direct_hits + pane_visible_hits)
            ), "fully proved by visible-result test"
        if state_only:
            return direct_hits, "proved only by state/assertion test"
        return direct_hits, "proved only indirectly by a broad suite"
    if pane_tests:
        return list(pane_tests), "proved only indirectly by a broad suite"
    return [], "unproved"


def build_audit() -> PaneFunctionAudit:
    pane_tests_by_surface = _parse_qa_matrix()
    server_routes = _parse_server_routes()
    server_controller_calls = _parse_server_controller_calls()
    controller_bodies = _parse_controller_method_bodies()
    test_corpus = _load_test_corpus()

    rows: list[FunctionAuditRow] = []
    for pane_owner, file_name in PANE_FILES.items():
        path = PANE_DIR / file_name
        pane_tests = pane_tests_by_surface.get(PANE_MATRIX_LABELS[pane_owner], [])
        for function_name, body in _extract_functions(path):
            selectors = _selectors_from_body(body)
            route_matches = _routes_from_body(body)
            routes = _normalized_routes(route_matches)
            function_type = _classify_function(function_name, body, selectors, routes)
            server_methods = [server_routes[route] for route in routes if route in server_routes]
            controller_methods = sorted(
                {
                    controller_method
                    for server_method in server_methods
                    for controller_method in server_controller_calls.get(server_method, [])
                }
            )
            persisted_state_paths = sorted(
                {
                    path_name
                    for controller_method in controller_methods
                    for path_name in _controller_assignments(
                        controller_bodies.get(controller_method, "")
                    )
                }
            )
            downstream_effects = sorted(
                {
                    effect
                    for controller_method in controller_methods
                    for effect in _downstream_effects(controller_bodies.get(controller_method, ""))
                }
            )
            visible_truth_targets = _visible_truth_targets(body, selectors, routes)
            mutates_state = bool(routes or persisted_state_paths)
            changes_visible_truth = bool(
                visible_truth_targets
                or function_type == "preview/waveform renderer"
                or any(
                    token in function_name.lower()
                    for token in (
                        "trim",
                        "sync",
                        "merge",
                        "overlay",
                        "review",
                        "score",
                        "timing",
                        "marker",
                        "queue",
                        "export",
                        "shotml",
                    )
                )
            )
            affects_export_queue_runtime = bool(
                any(
                    token in " ".join(routes + persisted_state_paths + downstream_effects).lower()
                    for token in ("export", "queue", "trim", "merge", "shotml", "analysis")
                )
            )
            proof_sources, proof_strength = _proof_evidence(
                pane_owner,
                function_name,
                selectors,
                routes,
                pane_tests,
                test_corpus,
            )
            defect_flags: list[str] = []
            remediation_required: list[str] = []
            if routes and not server_methods:
                defect_flags.append("missing-server-route-trace")
                remediation_required.append("Trace the browser route to a server handler.")
            if server_methods and not controller_methods:
                defect_flags.append("missing-controller-trace")
                remediation_required.append("Trace the server route to a controller mutation.")
            if mutates_state and proof_strength == "unproved":
                defect_flags.append("missing-proof")
                remediation_required.append("Add a UI-driven test with a visible-result assertion.")
            if (
                mutates_state
                and changes_visible_truth
                and proof_strength == "proved only by state/assertion test"
            ):
                defect_flags.append("state-only-visible-proof")
                remediation_required.append(
                    "Replace state-only proof with a visible-result browser assertion."
                )
            rows.append(
                FunctionAuditRow(
                    pane_owner=pane_owner,
                    pane_file=file_name,
                    function_name=function_name,
                    function_type=function_type,
                    primary_controls=selectors,
                    upstream_inputs=sorted(set(selectors + routes)),
                    downstream_effects=downstream_effects,
                    route_paths=routes,
                    server_methods=server_methods,
                    controller_methods=controller_methods,
                    persisted_state_paths=persisted_state_paths,
                    visible_truth_targets=visible_truth_targets,
                    affects_export_queue_runtime=affects_export_queue_runtime,
                    mutates_persisted_project_state=mutates_state,
                    changes_visible_truth=changes_visible_truth,
                    proof_sources=proof_sources,
                    proof_strength=proof_strength,
                    defect_flags=defect_flags,
                    remediation_required=remediation_required,
                    closure_status="closed" if not defect_flags else "open",
                )
            )
    return PaneFunctionAudit(
        rows=rows,
        generated_from={
            "pane_directory": str(PANE_DIR.relative_to(ROOT)),
            "server": str(SERVER_PATH.relative_to(ROOT)),
            "controller": str(CONTROLLER_PATH.relative_to(ROOT)),
            "qa_matrix": str(QA_MATRIX_PATH.relative_to(ROOT)),
            "pane_ownership": str(PANE_OWNERSHIP_PATH.relative_to(ROOT)),
        },
    )


def _rows_to_json(rows: list[FunctionAuditRow]) -> list[dict[str, object]]:
    return [asdict(row) for row in rows]


def _control_trace_rows(rows: list[FunctionAuditRow]) -> list[dict[str, object]]:
    traces: list[dict[str, object]] = []
    for pane_owner in PANE_FILES:
        pane_rows = [row for row in rows if row.pane_owner == pane_owner]
        controls = sorted({control for row in pane_rows for control in row.primary_controls})
        pane_route_rows = [row for row in pane_rows if row.route_paths]
        renderers = sorted(
            {
                row.function_name
                for row in pane_rows
                if "render" in row.function_name.lower()
                or row.function_type == "preview/waveform renderer"
            }
        )
        for control in controls:
            owning_rows = [row for row in pane_rows if control in row.primary_controls]
            handler_rows = [
                row
                for row in owning_rows
                if row.function_type in {"browser-action", "local-ui-state"}
                or any(token in row.function_name.lower() for token in ("bind", "handle", "apply", "save", "set", "toggle", "select", "delete", "add", "remove", "drag"))
            ]
            draft_owners = sorted(
                {
                    row.function_name
                    for row in pane_rows
                    if any(token in row.function_name.lower() for token in ("draft", "editable", "read", "save", "queue"))
                }
            )
            route_rows = [row for row in owning_rows if row.route_paths] or pane_route_rows
            traces.append(
                {
                    "pane_owner": pane_owner,
                    "control": control,
                    "event_handlers": sorted({row.function_name for row in handler_rows}),
                    "client_draft_state_owners": draft_owners,
                    "api_routes": sorted({route for row in route_rows for route in row.route_paths}),
                    "server_methods": sorted({method for row in route_rows for method in row.server_methods}),
                    "controller_methods": sorted({method for row in route_rows for method in row.controller_methods}),
                    "stored_project_profile_fields": sorted({field for row in route_rows for field in row.persisted_state_paths}),
                    "renderer_refresh_paths": renderers,
                    "later_export_queue_trim_consumption": sorted(
                        {
                            target
                            for row in pane_rows
                            if row.affects_export_queue_runtime
                            for target in row.visible_truth_targets
                        }
                    ),
                    "proof_sources": sorted({source for row in owning_rows for source in row.proof_sources}),
                }
            )
    return traces


def write_artifacts(audit: PaneFunctionAudit, artifact_root: Path) -> None:
    artifact_root.mkdir(parents=True, exist_ok=True)
    rows_json = _rows_to_json(audit.rows)
    (artifact_root / "pane-function-inventory.json").write_text(
        json.dumps(rows_json, indent=2) + "\n",
        encoding="utf-8",
    )
    control_traces = _control_trace_rows(audit.rows)
    (artifact_root / "control-interaction-trace-matrix.json").write_text(
        json.dumps(control_traces, indent=2) + "\n",
        encoding="utf-8",
    )
    trace_rows = [
        {
            "pane_owner": row.pane_owner,
            "pane_file": row.pane_file,
            "function_name": row.function_name,
            "function_type": row.function_type,
            "route_paths": row.route_paths,
            "server_methods": row.server_methods,
            "controller_methods": row.controller_methods,
            "persisted_state_paths": row.persisted_state_paths,
            "downstream_effects": row.downstream_effects,
            "visible_truth_targets": row.visible_truth_targets,
        }
        for row in audit.rows
    ]
    (artifact_root / "pane-function-trace-matrix.json").write_text(
        json.dumps(trace_rows, indent=2) + "\n",
        encoding="utf-8",
    )
    proof_rows = [
        {
            "pane_owner": row.pane_owner,
            "function_name": row.function_name,
            "proof_strength": row.proof_strength,
            "proof_sources": row.proof_sources,
        }
        for row in audit.rows
    ]
    (artifact_root / "pane-function-proof-strength.json").write_text(
        json.dumps(proof_rows, indent=2) + "\n",
        encoding="utf-8",
    )
    defects = [
        {
            "pane_owner": row.pane_owner,
            "function_name": row.function_name,
            "defect_flags": row.defect_flags,
            "remediation_required": row.remediation_required,
        }
        for row in audit.rows
        if row.defect_flags
    ]
    (artifact_root / "pane-function-defect-ledger.json").write_text(
        json.dumps(defects, indent=2) + "\n",
        encoding="utf-8",
    )
    remediation = [
        {
            "pane_owner": row.pane_owner,
            "function_name": row.function_name,
            "remediation_required": row.remediation_required,
            "closure_status": row.closure_status,
        }
        for row in audit.rows
        if row.remediation_required
    ]
    (artifact_root / "pane-function-remediation-ledger.json").write_text(
        json.dumps(remediation, indent=2) + "\n",
        encoding="utf-8",
    )
    closure = [
        {
            "pane_owner": row.pane_owner,
            "function_name": row.function_name,
            "closure_status": row.closure_status,
        }
        for row in audit.rows
    ]
    (artifact_root / "pane-function-closure-status.json").write_text(
        json.dumps(closure, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Pane Function Audit",
        "",
        f"- Inventory rows: {len(audit.rows)}",
        f"- Control trace rows: {len(control_traces)}",
        f"- Open rows: {len(audit.open_rows)}",
        "",
        "## Sources",
        "",
    ]
    for key, value in audit.generated_from.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Pane Summary", ""])
    for pane_owner in PANE_FILES:
        pane_rows = [row for row in audit.rows if row.pane_owner == pane_owner]
        open_count = sum(1 for row in pane_rows if row.closure_status != "closed")
        lines.append(f"- `{pane_owner}`: {len(pane_rows)} functions, {open_count} open")
    lines.extend(["", "## Open Rows", ""])
    if not audit.open_rows:
        lines.append("- None.")
    else:
        for row in audit.open_rows:
            lines.append(f"- `{row.pane_owner}.{row.function_name}`: {', '.join(row.defect_flags)}")
    (artifact_root / "pane-function-audit.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a code-first pane function audit.")
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    args = parser.parse_args()
    audit = build_audit()
    write_artifacts(audit, args.artifact_root)
    print(
        json.dumps(
            {
                "artifact_root": str(args.artifact_root),
                "inventory_rows": len(audit.rows),
                "open_rows": len(audit.open_rows),
            }
        )
    )


if __name__ == "__main__":
    main()
