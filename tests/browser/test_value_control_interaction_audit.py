from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path("scripts/audits/browser/run_value_control_interaction_audit.py")


def _load_audit_module():
    spec = importlib.util.spec_from_file_location("value_control_interaction_audit", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_ordinary_value_classification_does_not_claim_buttons_or_file_pickers() -> None:
    audit = _load_audit_module()

    assert audit._ordinary_value_row({"tag": "input", "input_type": "checkbox"})
    assert audit._ordinary_value_row({"tag": "input", "input_type": "number"})
    assert audit._ordinary_value_row({"tag": "select", "input_type": ""})
    assert audit._ordinary_value_row({"tag": "textarea", "input_type": ""})
    assert not audit._ordinary_value_row({"tag": "button", "input_type": ""})
    assert not audit._ordinary_value_row({"tag": "input", "input_type": "file"})
    assert not audit._ordinary_value_row({"tag": "input", "input_type": "hidden"})


def test_every_unexercised_inventory_row_is_an_explicit_gap() -> None:
    audit = _load_audit_module()

    button = audit._initial_gap(
        {"identity": "#save", "tag": "button", "input_type": ""}
    )
    picker = audit._initial_gap(
        {"identity": "#media", "tag": "input", "input_type": "file"}
    )
    value = audit._initial_gap(
        {"identity": "#quality", "tag": "select", "input_type": ""}
    )

    assert button.status == "gap"
    assert "button" in button.reason
    assert picker.status == "gap"
    assert "picker" in picker.reason
    assert value.status == "gap"
    assert "not rendered" in value.reason


def test_source_inventory_identity_conversion_is_deterministic() -> None:
    audit = _load_audit_module()

    assert audit._identity_selector("#quality") == "#quality"
    assert audit._identity_selector("id:quality") == "#quality"
    assert audit._identity_selector("quality") == "#quality"
    assert audit._identity_selector("data-tool:export") == '[data-tool="export"]'
    assert audit._identity_selector("anonymous selector") is None


def test_numeric_controls_compare_by_value_not_display_format() -> None:
    audit = _load_audit_module()

    assert audit._values_match({"type": "number"}, "0.990", "0.99")
    assert audit._values_match({"type": "range"}, "36", 36)
    assert not audit._values_match({"type": "text"}, "0.990", "0.99")
