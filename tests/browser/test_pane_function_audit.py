from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "audits"
    / "browser"
    / "pane_function_audit.py"
)
SPEC = importlib.util.spec_from_file_location("pane_function_audit", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
PANE_FILES = MODULE.PANE_FILES
build_audit = MODULE.build_audit


def test_pane_function_audit_inventories_every_pane_function() -> None:
    audit = build_audit()
    assert audit.rows, "Expected pane function audit rows"

    pane_counts = {pane_owner: 0 for pane_owner in PANE_FILES}
    for row in audit.rows:
        pane_counts[row.pane_owner] += 1
        assert row.function_name
        assert row.function_type
        assert row.proof_strength
        assert row.closure_status in {"open", "closed"}

    missing = [pane_owner for pane_owner, count in pane_counts.items() if count == 0]
    assert not missing, f"Missing pane audit rows for: {missing}"


def test_pane_function_audit_traces_browser_actions_to_server_and_controller() -> None:
    audit = build_audit()
    browser_actions = [row for row in audit.rows if row.function_type == "browser-action"]
    assert browser_actions, "Expected browser-action rows in pane function audit"

    untraced = [
        f"{row.pane_owner}.{row.function_name}"
        for row in browser_actions
        if row.route_paths and (not row.server_methods or not row.controller_methods)
    ]
    assert not untraced, f"Browser actions missing trace coverage: {untraced}"


def test_pane_function_audit_keeps_mutating_rows_out_of_unproved_state() -> None:
    audit = build_audit()
    unproved = [
        f"{row.pane_owner}.{row.function_name}"
        for row in audit.rows
        if row.mutates_persisted_project_state and row.proof_strength == "unproved"
    ]
    assert not unproved, f"Mutating pane functions are unproved: {unproved}"
