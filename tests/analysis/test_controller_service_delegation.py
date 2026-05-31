from __future__ import annotations

import pytest

import splitshot.ui.controller as controller_module
from splitshot.ui.controller import ProjectController


@pytest.mark.parametrize(
    (
        "method_name",
        "service_module_name",
        "service_method_name",
        "args",
        "kwargs",
        "expected_result",
    ),
    [
        (
            "new_project",
            "project_session_service_module",
            "new_project",
            (),
            {},
            None,
        ),
        (
            "analyze_primary",
            "analysis_service_module",
            "analyze_primary",
            (),
            {},
            None,
        ),
        (
            "set_shotml_settings",
            "analysis_service_module",
            "set_shotml_settings",
            ({"detection_threshold": 0.4},),
            {"rerun": True, "update_app_defaults": True},
            None,
        ),
        (
            "assign_score",
            "scoring_service_module",
            "assign_score",
            ("shot-1",),
            {"letter": "A", "penalty_counts": {"NS": 1}},
            None,
        ),
        (
            "workspace_export",
            "merge_export_service_module",
            "workspace_export",
            ("stage-1", "recap"),
            {},
            {"success": True, "recipe": "recap"},
        ),
        (
            "add_merge_source",
            "merge_export_service_module",
            "add_merge_source",
            ("/tmp/merge.mp4",),
            {"source_name": "Angle 2"},
            None,
        ),
    ],
)
def test_project_controller_service_delegation(
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    service_module_name: str,
    service_method_name: str,
    args: tuple[object, ...],
    kwargs: dict[str, object],
    expected_result: object,
) -> None:
    controller = ProjectController()
    captured: list[tuple[ProjectController, tuple[object, ...], dict[str, object]]] = []

    def fake_service(
        forwarded_controller: ProjectController,
        *forwarded_args: object,
        **forwarded_kwargs: object,
    ) -> object:
        captured.append((forwarded_controller, forwarded_args, forwarded_kwargs))
        return expected_result

    service_module = getattr(controller_module, service_module_name)
    monkeypatch.setattr(service_module, service_method_name, fake_service)

    result = getattr(controller, method_name)(*args, **kwargs)

    assert captured == [(controller, args, kwargs)]
    assert result == expected_result
