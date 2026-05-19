#!/usr/bin/env python3
"""Automation E2E scenario tests for SplitShot.

Exercises the 4 E2E scenarios from docs/automate/10-acceptance-and-proof.md
against the controller API, validating structured payload correctness.
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from splitshot.ui.controller import ProjectController


def test_single_video_reviewed_output_flow():
    """Scenario: Single Video reviewed-output flow."""
    print("=== Single Video reviewed-output flow ===")

    c = ProjectController()
    c.new_project()
    c.project.name = "E2E Stage Project"
    assert c.editor_scope == "single"
    assert c.project.name == "E2E Stage Project"
    print("  [1] Project created OK")

    c.project.primary_video.path = "/tmp/e2e_test_video.mp4"
    print("  [2] Media path set")

    assert hasattr(c.project.analysis, "shots")
    assert isinstance(c.project.analysis.shots, list)
    print("  [3] Analysis structure present")

    p1 = c.output_profile_create(
        "stage", c.project.id, "Technical Review", "stage_output",
        frame_profile="16:9",
        metric_caption_preset={"enabled_fields": ["cumulative_time", "hit_factor"]},
    )
    p2 = c.output_profile_create(
        "stage", c.project.id, "Social Clip", "stage_output",
        frame_profile="9:16",
        metric_caption_preset={"enabled_fields": ["shot_count"]},
        lead_in_card={"match_name": "E2E Match", "shooter": "Test Shooter"},
    )
    profiles = c.output_profile_list("stage", c.project.id)
    assert len(profiles) == 2, f"Expected 2 profiles, got {len(profiles)}"
    print(f"  [4] Created {len(profiles)} output profiles")

    render1 = c.output_profile_render(p1["output_id"])
    assert render1["success"] is True
    assert "run_window" in render1
    assert render1["source"] == "output_profile"
    print(f"  [5] Run Window render plan OK (start={render1['run_window'].get('start_ms', 'N/A')})")

    render2 = c.output_profile_render(p2["output_id"])
    assert render2["success"] is True
    assert "metric_caption_preset" in render2
    assert render2["frame_profile"] == "9:16"
    print(f"  [6] Metric Captions render plan OK (frame={render2['frame_profile']})")

    pstatus = c.proxy_status()
    assert "exists" in pstatus
    assert "stale" in pstatus
    print(f"  [7-8] Proxy status: exists={pstatus['exists']}, stale={pstatus['stale']}")

    print("  Single Video scenario: PASSED\n")


def test_multi_video_shared_default_and_match_recap_flow():
    """Scenario: Multi Video shared-default and Match Recap flow."""
    print("=== Multi Video shared-default and Match Recap flow ===")

    c = ProjectController()

    c.new_workspace()
    c.workspace.name = "E2E Match"
    assert c.editor_scope == "multi"
    assert c.workspace.name == "E2E Match"
    print("  [1] Workspace created OK")

    c.workspace_add_stage("s1", "Bay 1", "")
    c.workspace_add_stage("s2", "Bay 2", "")
    c.workspace_add_stage("s3", "Bay 3", "")
    assert len(c.workspace.stage_entries) == 3
    assert c.workspace.stage_order == ["s1", "s2", "s3"]
    print(f"  [2] Added {len(c.workspace.stage_entries)} stages")

    c.workspace_set_defaults({"frame_profile": "16:9"})
    assert c.workspace.shared_defaults.get("frame_profile") == "16:9"
    print("  [3] Shared defaults applied")

    c.workspace_set_stage_override("s1", {"frame_profile": "9:16"})
    assert c.workspace.stage_entries["s1"].override_values.get("frame_profile") == "9:16"
    assert c.workspace.stage_entries["s1"].status == "overridden"
    print("  [4] Stage 1 overridden")

    assert c.resolve_setting("s1", "frame_profile") == "9:16"
    assert c.resolve_setting("s2", "frame_profile") == "16:9"
    assert c.resolve_setting("s3", "frame_profile") == "16:9"
    print("  [5] Sibling stages inherited correctly")

    recap_profile = c.output_profile_create(
        "match", c.workspace.match_id, "Match Recap", "match_recap",
        frame_profile="16:9",
    )
    recap = c.match_recap_preview(recap_profile["output_id"])
    assert recap["success"] is True
    assert recap["profile_kind"] == "match_recap"
    assert recap["stage_count"] == 3
    print(f"  [6] Match Recap preview OK ({recap['stage_count']} stages)")

    print("  Multi Video scenario: PASSED\n")


def test_stage_composite_and_angle_align_flow():
    """Scenario: Stage Composite and Angle Align flow."""
    print("=== Stage Composite and Angle Align flow ===")

    c = ProjectController()
    c.new_workspace()
    stage_id = "s1"
    c.workspace_add_stage(stage_id, "Composite Stage", "")

    c.workspace_stage_clip_add(stage_id, "/tmp/pov.mp4", "primary")
    c.workspace_stage_clip_add(stage_id, "/tmp/follow.mp4", "follow")
    c.workspace_stage_clip_add(stage_id, "/tmp/static.mp4", "static")
    all_clips = c._get_stage_clips(stage_id)
    assert len(all_clips) == 3, f"Expected 3 clips, got {len(all_clips)}"
    print(f"  [1] Added {len(all_clips)} clips to stage")

    roles = [cl["angle_role"] for cl in all_clips]
    assert "primary" in roles
    assert "follow" in roles
    assert "static" in roles
    print(f"  [2] Angle roles assigned: {roles}")

    ref_id = all_clips[0]["clip_id"]
    align = c.angle_align(stage_id, ref_id)
    assert align["success"] is True
    assert align["aligned_clips"] == 3
    print(f"  [3] Angle Align OK ({align['aligned_clips']} clips aligned)")

    audio = c.audio_mix_set(stage_id, ref_id, gain=0.8, muted=False, primary=True)
    assert audio is not None
    assert audio["audio_gain"] == 0.8
    print(f"  [4] Audio mix adjusted (gain={audio['audio_gain']})")

    profile = c.output_profile_create(
        "stage", stage_id, "Composite Output", "stage_composite",
        frame_profile="16:9",
    )
    composite = c.stage_composite_preview(profile["output_id"])
    assert composite["success"] is True
    assert composite["profile_kind"] == "stage_composite"
    assert composite["clip_count"] == 3
    print(f"  [5] Stage Composite preview OK ({composite['clip_count']} clips)")

    print("  Stage Composite scenario: PASSED\n")


def test_performance_library_browse_and_reopen_flow():
    """Scenario: Performance Library browse and reopen flow."""
    print("=== Performance Library browse and reopen flow ===")

    test_lib = tempfile.mkdtemp(prefix="splitshot_e2e_lib_")
    os.environ["SPLITSHOT_LIBRARY_ROOT"] = test_lib

    try:
        c = ProjectController()
        c.new_project()
        c.project.name = "Library Stage"

        c._sync_project_to_library()
        print("  [1] Stage truth saved to library")

        c.new_workspace()
        c.workspace.name = "Library Match"
        c.workspace_add_stage("ls1", "Library Stage 1", "")
        c._sync_workspace_to_library()
        print("  [1] Workspace truth saved to library")

        from splitshot.persistence.library import read_stage_metrics, read_match_metrics

        stage_metrics = read_stage_metrics()
        match_metrics = read_match_metrics()
        assert len(stage_metrics) >= 1, f"Expected >=1 stage metric rows, got {len(stage_metrics)}"
        assert len(match_metrics) >= 1, f"Expected >=1 match metric rows, got {len(match_metrics)}"
        print(f"  [2] Library records: {len(stage_metrics)} stages, {len(match_metrics)} matches")

        filtered = [s for s in stage_metrics if s.get("stage_id") == c.project.id]
        assert len(filtered) >= 1
        print(f"  [3] History query OK ({len(filtered)} matching records)")

        pstatus = c.proxy_status()
        print(f"  [4] Proxy status: exists={pstatus['exists']}, stale={pstatus['stale']}")

        from splitshot.persistence.library import load_stage_record

        record = load_stage_record(filtered[0]["library_record_id"])
        assert record is not None
        target = record.editor_target
        print(f"  [5] Editor target: type={target.get('type', 'N/A')}, stage_id={record.stage_id}")
        assert record.stage_id is not None
        print("  [5] Editor reopen target resolved OK")

        print("  Library scenario: PASSED\n")
    finally:
        os.environ.pop("SPLITSHOT_LIBRARY_ROOT", None)
        import shutil
        shutil.rmtree(test_lib, ignore_errors=True)


def main():
    results = [
        ("Single Video reviewed-output flow", test_single_video_reviewed_output_flow),
        ("Multi Video Match Recap flow", test_multi_video_shared_default_and_match_recap_flow),
        ("Stage Composite and Angle Align flow", test_stage_composite_and_angle_align_flow),
        ("Performance Library browse and reopen flow", test_performance_library_browse_and_reopen_flow),
    ]

    print("=" * 60)
    print("E2E SCENARIO RESULTS")
    print("=" * 60)

    fails = []
    for name, test_fn in results:
        try:
            test_fn()
        except Exception as exc:
            print(f"  FAIL: {name}")
            print(f"        {type(exc).__name__}: {exc}")
            fails.append(name)
            import traceback
            traceback.print_exc()
            print()

    if fails:
        print(f"\n{len(fails)} E2E SCENARIO(S) FAILED: {', '.join(fails)}")
        return 1
    else:
        print("\nALL E2E SCENARIOS PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())
