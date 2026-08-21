from __future__ import annotations

import json
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from splitshot.browser.server import BrowserControlServer
from splitshot.domain.models import ProjectStage, QueueEntry, QueueStatus, ShotEvent, VideoAsset
from splitshot.ui.controller import ProjectController
from tests.browser.helpers.video_test_helpers import create_project


def _open_test_page(playwright, server: BrowserControlServer):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(server.url, wait_until="domcontentloaded")
    return browser, page


def test_added_media_requires_primary_in_controller() -> None:
    controller = ProjectController()
    stage = controller.create_stage()
    with pytest.raises(ValueError, match="Add primary media"):
        controller.import_stage_added(stage.id, "/does/not/matter.mp4")


def test_media_global_settings_controls_preserve_target_stage_data() -> None:
    controller = ProjectController()
    source = ProjectStage(label="Stage 1", primary_media=VideoAsset(path="one.mp4"))
    target = ProjectStage(label="Stage 2", primary_media=VideoAsset(path="two.mp4"))
    source.overlay.font_size = 48
    target.analysis.shots = [ShotEvent(time_ms=3210)]
    target.scoring.stage_number = 2
    controller.project.stages = [source, target]
    controller.project.active_stage_id = source.id
    controller._sync_active_stage_to_project()
    controller.project.queue = [QueueEntry(stage_id=target.id, status=QueueStatus.QUEUED)]
    target.queue_status = QueueStatus.QUEUED
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                page.locator("button[data-tool='media']").click(force=True)
                primary = page.locator("#media-global-settings-primary")
                ignored = page.locator("#media-ignore-global-settings")
                assert primary.is_visible()
                assert ignored.is_visible()
                primary.click()
                page.wait_for_function(
                    "(id) => state.project.global_settings_stage_id === id", arg=source.id
                )
                assert page.locator("#media-global-settings-primary").get_attribute(
                    "aria-pressed"
                ) == "true"
                page.locator("#media-active-stage-select").select_option(target.id)
                page.wait_for_function(
                    "(id) => state.project.active_stage_id === id", arg=target.id
                )
                page.locator("#media-ignore-global-settings").click()
                page.wait_for_function(
                    "(id) => state.project.stages.find(stage => stage.id === id)?.ignore_global_settings === true",
                    arg=target.id,
                )
                saved_target = next(stage for stage in controller.project.stages if stage.id == target.id)
                assert [shot.time_ms for shot in saved_target.analysis.shots] == [3210]
                assert saved_target.scoring.stage_number == 2
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_media_intake_buttons_use_distinct_primary_and_green_add_styles(
    synthetic_video_factory,
) -> None:
    primary_path = Path(synthetic_video_factory(name="media-intake-gate"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                create_project(page, str(primary_path.parent / "media-intake-gate.ssproj"))
                page.evaluate("() => callApi('/api/project/stage/create', {})")
                page.wait_for_function("() => Boolean(state?.project?.active_stage_id)")
                page.locator("button[data-tool='media']").click(force=True)
                add_primary = page.locator(".media-add-primary-btn")
                add_media = page.locator(".media-add-more-btn")
                assert add_primary.is_enabled()
                assert add_media.is_disabled()
                primary_box = add_primary.bounding_box()
                media_box = add_media.bounding_box()
                assert primary_box and media_box
                assert primary_box["height"] >= 30
                assert media_box["height"] >= 30
                assert add_primary.evaluate(
                    "el => getComputedStyle(el).backgroundColor"
                ) != add_media.evaluate(
                    "el => { el.disabled = false; const color = getComputedStyle(el).backgroundColor; el.disabled = true; return color; }"
                )

                page.locator("#primary-file-input").set_input_files(str(primary_path))
                page.wait_for_function("() => Boolean(state?.project?.primary_video?.path)")
                page.locator("button[data-tool='project']").click(force=True)
                page.locator("button[data-tool='media']").click(force=True)
                assert page.locator(".media-add-more-btn").is_enabled()
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_media_stage_switch_keeps_primary_and_added_media_owned_by_each_stage(
    synthetic_video_factory,
) -> None:
    stage_media = {
        "Stage 1": (
            Path(synthetic_video_factory(name="stage-1-primary")),
            Path(synthetic_video_factory(name="stage-1-added")),
        ),
        "Stage 2": (
            Path(synthetic_video_factory(name="stage-2-primary")),
            Path(synthetic_video_factory(name="stage-2-added")),
        ),
        "Stage 3": (
            Path(synthetic_video_factory(name="stage-3-primary")),
            Path(synthetic_video_factory(name="stage-3-added")),
        ),
    }
    project_root = stage_media["Stage 1"][0].parent / "media-stage-ownership.ssproj"
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                create_project(page, str(project_root))
                page.evaluate("() => callApi('/api/project/stage/create', { label: 'Stage 1' })")
                page.wait_for_function("() => Boolean(state?.project?.active_stage_id)")
                page.locator("button[data-tool='media']").click(force=True)

                def active_stage_id() -> str:
                    return str(page.evaluate("state.project.active_stage_id"))

                def assert_empty_stage(label: str) -> None:
                    page.wait_for_function(
                        """(expectedLabel) => {
                            const active = state?.project?.active_stage_id;
                            const stage = (state?.project?.stages || []).find(
                                (item) => item.id === active,
                            );
                            return stage?.label === expectedLabel
                                && !state?.project?.primary_video?.path
                                && (state?.project?.merge_sources || []).length === 0
                                && document.querySelector(
                                    '.media-add-primary-btn',
                                )?.textContent?.trim() === 'Add Primary'
                                && !document.querySelector(
                                    '.media-asset-row[data-source-id="primary"]',
                                );
                        }""",
                        arg=label,
                    )
                    assert page.locator(".media-add-more-btn").is_disabled()
                    assert page.locator(".media-asset-row").count() == 0

                def add_stage_media(stage_id: str, primary: Path, added: Path) -> None:
                    page.evaluate(
                        """({ stageId, path }) => callApi(
                            '/api/project/stage/import-primary',
                            { stage_id: stageId, path },
                        )""",
                        {"stageId": stage_id, "path": str(primary)},
                    )
                    page.wait_for_function("() => Boolean(state?.project?.primary_video?.path)")
                    assert page.locator(".media-add-more-btn").is_enabled()
                    page.evaluate(
                        """({ stageId, path }) => callApi(
                            '/api/project/stage/import-added',
                            { stage_id: stageId, path },
                        )""",
                        {"stageId": stage_id, "path": str(added)},
                    )
                    page.wait_for_function(
                        "() => (state?.project?.merge_sources || []).length === 1"
                    )

                def assert_stage_inventory(
                    stage_id: str,
                    label: str,
                    primary: Path,
                    added: Path,
                ) -> None:
                    page.locator("#media-active-stage-select").select_option(stage_id)
                    page.wait_for_function(
                        """({ stageId, primaryName, addedName }) => {
                            const rows = Array.from(
                                document.querySelectorAll('#media-pane .media-asset-row'),
                            );
                            const text = rows.map(
                                (row) => row.textContent || '',
                            ).join('\\n');
                            return state?.project?.active_stage_id === stageId
                                && rows.length === 2
                                && text.includes(primaryName)
                                && text.includes(addedName);
                        }""",
                        arg={
                            "stageId": stage_id,
                            "primaryName": primary.name,
                            "addedName": added.name,
                        },
                    )
                    pane_text = page.locator("#media-pane").inner_text()
                    assert label in pane_text
                    assert primary.name in pane_text
                    assert added.name in pane_text
                    for other_label, other_paths in stage_media.items():
                        if other_label == label:
                            continue
                        assert other_paths[0].name not in pane_text
                        assert other_paths[1].name not in pane_text
                    replace = page.locator(
                        '#media-pane .media-asset-row[data-source-id="primary"] '
                        ".media-asset-actions .media-replace-primary-btn"
                    )
                    assert replace.inner_text() == "Replace"

                stage_ids: dict[str, str] = {}
                for index, label in enumerate(("Stage 1", "Stage 2", "Stage 3")):
                    if index:
                        page.locator(".media-add-stage-btn").click()
                    assert_empty_stage(label)
                    stage_ids[label] = active_stage_id()
                    primary, added = stage_media[label]
                    add_stage_media(stage_ids[label], primary, added)
                    assert_stage_inventory(stage_ids[label], label, primary, added)

                for label in ("Stage 1", "Stage 2", "Stage 3"):
                    primary, added = stage_media[label]
                    assert_stage_inventory(stage_ids[label], label, primary, added)
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_practiscore_autosave_keeps_empty_selected_stage_and_player_isolated(
    synthetic_video_factory,
    tmp_path: Path,
) -> None:
    warmup_path = Path(synthetic_video_factory(name="warmup-stage-primary"))
    practiscore = Path(__file__).resolve().parents[2] / "example_data" / "IDPA" / "IDPA.csv"
    project_path = tmp_path / "practiscore-stage-state.ssproj"

    controller = ProjectController()
    controller.import_practiscore_file(str(practiscore), source_name="IDPA.csv")
    controller.save_project(str(project_path))
    warmup_stage = controller.project.stages[0]
    controller.import_stage_primary(warmup_stage.id, str(warmup_path))
    empty_stage = controller.create_stage("Empty Stage")

    assert controller.project.active_stage_id == empty_stage.id
    assert controller.project.primary_video.path == ""
    assert empty_stage.primary_media.path == ""

    reopened = ProjectController()
    reopened.open_project(str(project_path))
    assert reopened.project.active_stage_id == empty_stage.id
    assert reopened.project.primary_video.path == ""
    assert reopened.project.active_stage.primary_media.path == ""

    server = BrowserControlServer(controller=reopened, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                page.locator("button[data-tool='media']").click(force=True)
                assert (
                    page.locator("#media-pane").get_by_text("Primary Media", exact=True).count()
                    == 1
                )
                assert (
                    page.locator("#media-pane").get_by_text("Secondary Media", exact=True).count()
                    == 1
                )
                for selector, label in (
                    (".media-add-primary-btn", "Add Primary"),
                    (".media-add-more-btn", "Add Media"),
                ):
                    button = page.locator(selector)
                    assert button.inner_text() == label
                    dimensions = button.evaluate(
                        """(node) => ({
                            clientHeight: node.clientHeight,
                            scrollHeight: node.scrollHeight,
                            clientWidth: node.clientWidth,
                            scrollWidth: node.scrollWidth,
                        })"""
                    )
                    assert dimensions["scrollHeight"] <= dimensions["clientHeight"]
                    assert dimensions["scrollWidth"] <= dimensions["clientWidth"]
                assert "No primary media." in page.locator("#media-pane").inner_text()
                assert warmup_path.name not in page.locator("#media-pane").inner_text()

                page.locator("#media-active-stage-select").select_option(warmup_stage.id)
                page.wait_for_function(
                    """({ stageId, name }) => (
                        state?.project?.active_stage_id === stageId
                        && state?.project?.primary_video?.path?.endsWith(name)
                        && document.querySelector('#primary-video')?.dataset.sourcePath?.endsWith(name)
                    )""",
                    arg={"stageId": warmup_stage.id, "name": warmup_path.name},
                )

                page.locator("#media-active-stage-select").select_option(empty_stage.id)
                page.wait_for_function(
                    """(stageId) => (
                        state?.project?.active_stage_id === stageId
                        && !state?.project?.primary_video?.path
                        && !state?.media?.primary_available
                        && !document.querySelector('#primary-video')?.dataset.sourcePath
                        && document.querySelector('#media-pane')?.innerText.includes('No primary media.')
                    )""",
                    arg=empty_stage.id,
                )
                assert warmup_path.name not in page.locator("#media-pane").inner_text()

                saved = {}
                for _ in range(50):
                    saved = json.loads((project_path / "project.json").read_text())
                    if saved.get("active_stage_id") == empty_stage.id:
                        break
                    page.wait_for_timeout(100)
                saved_empty_stage = next(
                    stage for stage in saved["stages"] if stage["id"] == empty_stage.id
                )
                assert saved["active_stage_id"] == empty_stage.id
                assert saved["primary_video"]["path"] == ""
                assert saved_empty_stage["primary_media"]["path"] == ""
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_media_pane_active_stage_workspace_present(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="media-qa-card"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                if not page.evaluate("Boolean(state?.project?.path)"):
                    project_path = str(primary_path.parent / "media-qa.ssproj")
                    page.evaluate(f"() => createNewProject({json.dumps(project_path)})")
                    page.wait_for_function("() => Boolean(state?.project?.path)")
                page.locator("button[data-tool='media']").click(force=True)
                page.wait_for_timeout(100)
                page.locator("#primary-file-input").set_input_files(str(primary_path))
                page.wait_for_function("() => Boolean(state?.project?.primary_video?.path)")
                assert page.locator("#media-pane").get_by_text("Stage", exact=True).count() >= 1
                assert (
                    page.locator("#media-pane").get_by_text("Primary Media", exact=True).count()
                    == 1
                )
                assert (
                    page.locator("#media-pane").get_by_text("Secondary Media", exact=True).count()
                    == 1
                )
                assert page.locator("#media-pane").get_by_text("Stages", exact=True).count() == 0
                assert page.locator("button.media-add-stage-btn").count() >= 1
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_media_pane_uses_active_stage_selector_without_stage_navigator(
    synthetic_video_factory,
) -> None:
    primary_path = Path(synthetic_video_factory(name="media-qa-nav"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                if not page.evaluate("Boolean(state?.project?.path)"):
                    project_path = str(primary_path.parent / "media-qa-nav.ssproj")
                    page.evaluate(f"() => createNewProject({json.dumps(project_path)})")
                    page.wait_for_function("() => Boolean(state?.project?.path)")
                page.locator("button[data-tool='media']").click(force=True)
                page.wait_for_timeout(100)
                page.locator("#primary-file-input").set_input_files(str(primary_path))
                page.wait_for_function("() => Boolean(state?.project?.primary_video?.path)")
                assert page.locator("#media-active-stage-select").count() >= 1
                assert "Stage Navigator" not in page.locator("#media-pane").inner_text()
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_media_pane_primary_and_added_sections_present(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="media-qa-sections"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                if not page.evaluate("Boolean(state?.project?.path)"):
                    project_path = str(primary_path.parent / "media-qa-sec.ssproj")
                    page.evaluate(f"() => createNewProject({json.dumps(project_path)})")
                    page.wait_for_function("() => Boolean(state?.project?.path)")
                page.locator("button[data-tool='media']").click(force=True)
                page.wait_for_timeout(100)
                page.locator("#primary-file-input").set_input_files(str(primary_path))
                page.wait_for_function("() => Boolean(state?.project?.primary_video?.path)")
                inner_text = page.locator("#media-pane").inner_text()
                assert "Primary Media" in inner_text
                assert "Secondary Media" in inner_text
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_media_inventory_disclosures_persist_without_stages_wrapper(
    synthetic_video_factory,
) -> None:
    primary_path = Path(synthetic_video_factory(name="media-qa-disclosures"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                create_project(page, str(primary_path.parent / "media-qa-disclosures.ssproj"))
                page.evaluate("() => callApi('/api/project/stage/create', {})")
                page.wait_for_function("() => Boolean(state?.project?.active_stage_id)")
                page.locator("button[data-tool='media']").click(force=True)
                page.locator("#primary-file-input").set_input_files(str(primary_path))
                page.wait_for_function("() => Boolean(state?.project?.primary_video?.path)")

                primary_toggle = page.locator('[data-media-section="primary"]')
                primary_toggle.click()
                assert primary_toggle.get_attribute("aria-label") == "Expand Primary Media"
                assert (
                    page.locator("#media-pane .media-pane-section")
                    .nth(1)
                    .get_attribute("class")
                    .endswith("collapsed")
                )
                assert (
                    page.evaluate(
                        "() => JSON.parse(localStorage.getItem('splitshot.media.sectionExpanded')).primary"
                    )
                    is False
                )
                assert page.locator("#media-pane").get_by_text("Stages", exact=True).count() == 0
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_media_add_stage_lives_inside_active_stage_controls(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="media-qa-add-stage"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                if not page.evaluate("Boolean(state?.project?.path)"):
                    project_path = str(primary_path.parent / "media-qa-add-stage.ssproj")
                    page.evaluate(f"() => createNewProject({json.dumps(project_path)})")
                    page.wait_for_function("() => Boolean(state?.project?.path)")
                page.locator("button[data-tool='media']").click(force=True)
                page.wait_for_timeout(100)
                page.locator("#primary-file-input").set_input_files(str(primary_path))
                page.wait_for_function("() => Boolean(state?.project?.primary_video?.path)")

                add_stage = page.locator("#media-pane .media-add-stage-full")
                add_stage.wait_for(state="visible")
                active_stage_section = page.locator("#media-pane .media-pane-section-static").first
                assert active_stage_section.locator(".media-add-stage-full").count() == 1
                assert page.locator("#media-pane > .media-add-stage-full").count() == 0
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_media_save_stage_updates_active_stage_label_visibly(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="media-qa-rename"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                project_path = str(primary_path.parent / "media-qa-rename.ssproj")
                create_project(page, project_path)
                page.evaluate("() => callApi('/api/project/stage/create', {})")
                page.wait_for_function("() => Boolean(state?.project?.active_stage_id)")
                page.evaluate(
                    "(path) => callApi('/api/project/stage/import-primary', { stage_id: state.project.active_stage_id, path })",
                    str(primary_path),
                )
                page.wait_for_function("() => Boolean(state?.project?.primary_video?.path)")
                page.locator("button[data-tool='media']").click(force=True)
                page.wait_for_timeout(150)

                page.locator("#media-active-stage-label").fill("Classifier Bay")
                page.locator(".media-save-stage-btn").click()
                page.wait_for_function(
                    """() => {
                        const active = state?.project?.active_stage_id;
                        const stage = (state?.project?.stages || []).find((item) => item.id === active);
                        return stage?.label === 'Classifier Bay';
                    }"""
                )

                assert "Classifier Bay" in page.locator("#media-pane").inner_text()
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_stage_rename_resorts_every_stage_order_consumer_and_persists(tmp_path: Path) -> None:
    project_path = tmp_path / "stage-natural-order.ssproj"
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                create_project(page, str(project_path))
                for label in ("Stage 2", "Stage 3", "Stage 6"):
                    page.evaluate(
                        "(stageLabel) => callApi('/api/project/stage/create', { label: stageLabel })",
                        label,
                    )

                page.locator("button[data-tool='media']").click(force=True)
                page.locator("#media-active-stage-label").fill("Stage 1")
                page.locator(".media-save-stage-btn").click()
                page.wait_for_function(
                    """() => (state?.project?.stages || [])
                        .map((stage) => stage.label).join('|') === 'Stage 1|Stage 2|Stage 3'"""
                )

                assert page.locator("#media-active-stage-select option").all_text_contents() == [
                    "Stage 1",
                    "Stage 2",
                    "Stage 3",
                ]
                assert page.evaluate(
                    "() => state.project.stages.map((stage) => stage.order_index)"
                ) == [1, 2, 3]
                assert page.evaluate(
                    "() => state.stage_metrics.map((entry) => entry.stage_name)"
                ) == ["Stage 1", "Stage 2", "Stage 3"]

                page.locator("button[data-tool='queue']").click(force=True)
                assert page.locator(".queue-stage-copy > strong").all_text_contents() == [
                    "Stage 1",
                    "Stage 2",
                    "Stage 3",
                ]

                controller.autosave_project_if_needed()
                reopened = ProjectController()
                reopened.open_project(str(project_path))
                assert [stage.label for stage in reopened.project.stages] == [
                    "Stage 1",
                    "Stage 2",
                    "Stage 3",
                ]
                assert [stage.order_index for stage in reopened.project.stages] == [1, 2, 3]
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_media_delete_stage_removes_stage_from_selector_visibly(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="media-qa-delete"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                project_path = str(primary_path.parent / "media-qa-delete.ssproj")
                create_project(page, project_path)
                page.evaluate("() => callApi('/api/project/stage/create', {})")
                page.wait_for_function("() => Boolean(state?.project?.active_stage_id)")
                page.evaluate(
                    "(path) => callApi('/api/project/stage/import-primary', { stage_id: state.project.active_stage_id, path })",
                    str(primary_path),
                )
                page.wait_for_function("() => Boolean(state?.project?.primary_video?.path)")
                page.locator("button[data-tool='media']").click(force=True)
                page.wait_for_timeout(150)

                page.evaluate("() => callApi('/api/project/stage/create', {})")
                page.wait_for_function("() => (state?.project?.stages || []).length === 2")
                page.locator("#media-active-stage-label").fill("Temporary Stage")
                page.locator(".media-save-stage-btn").click()
                page.wait_for_timeout(150)
                page.locator(".media-delete-stage-btn").click()
                page.wait_for_function("() => (state?.project?.stages || []).length === 1")

                selector_text = page.locator("#media-active-stage-select").inner_text()
                assert "Temporary Stage" not in selector_text
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_media_delete_imported_stage_persists_after_autosave(tmp_path: Path) -> None:
    controller = ProjectController()
    source = Path(__file__).resolve().parents[2] / "example_data" / "IDPA" / "IDPA.csv"
    controller.import_practiscore_file(str(source), source_name="IDPA.csv")
    controller.save_project(str(tmp_path / "media-delete-imported.ssproj"))
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                page.locator("button[data-tool='media']").click(force=True)
                page.wait_for_function("() => (state?.project?.stages || []).length === 4")
                page.locator("#media-active-stage-select").select_option(
                    controller.project.active_stage_id
                )
                page.locator(".media-delete-stage-btn").click()
                page.wait_for_function(
                    """() => {
                        const stages = state?.project?.stages || [];
                        return stages.length === 3
                            && stages.every((stage) => stage.imported_stage_number !== 1);
                    }"""
                )

                assert "Stage 1" not in page.locator("#media-active-stage-select").inner_text()
                assert controller.project.excluded_imported_stage_numbers == [1]
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_media_clear_primary_shows_empty_primary_state(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="media-qa-clear-primary"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                project_path = str(primary_path.parent / "media-qa-clear-primary.ssproj")
                create_project(page, project_path)
                page.evaluate("() => callApi('/api/project/stage/create', {})")
                page.wait_for_function("() => Boolean(state?.project?.active_stage_id)")
                page.evaluate(
                    "(path) => callApi('/api/project/stage/import-primary', { stage_id: state.project.active_stage_id, path })",
                    str(primary_path),
                )
                page.wait_for_function("() => Boolean(state?.project?.primary_video?.path)")
                page.locator("button[data-tool='media']").click(force=True)
                page.wait_for_timeout(150)

                page.locator('.media-remove-file-btn[data-source-id="primary"]').click()
                page.wait_for_function("() => !Boolean(state?.project?.primary_video?.path)")
                assert "No primary media." in page.locator("#media-pane").inner_text()
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_media_set_primary_promotes_added_row_visibly(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="media-qa-primary-a"))
    added_path = Path(synthetic_video_factory(name="media-qa-primary-b"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                project_path = str(primary_path.parent / "media-qa-set-primary.ssproj")
                create_project(page, project_path)
                page.evaluate("() => callApi('/api/project/stage/create', {})")
                page.wait_for_function("() => Boolean(state?.project?.active_stage_id)")
                page.evaluate(
                    "(path) => callApi('/api/project/stage/import-primary', { stage_id: state.project.active_stage_id, path })",
                    str(primary_path),
                )
                page.wait_for_function("() => Boolean(state?.project?.primary_video?.path)")
                page.evaluate(
                    "(path) => callApi('/api/project/stage/import-added', { stage_id: state.project.active_stage_id, path })",
                    str(added_path),
                )
                page.wait_for_function("() => (state?.project?.merge_sources || []).length === 1")
                page.locator("button[data-tool='media']").click(force=True)
                page.wait_for_timeout(150)

                primary_before = page.locator(
                    '#media-pane .media-asset-row[data-source-id="primary"]'
                ).inner_text()
                assert primary_path.name in primary_before

                added_row = page.locator(
                    '#media-pane .media-asset-row[data-source-id]:not([data-source-id="primary"])'
                ).first
                added_row.locator(".media-set-primary-btn").click()
                page.wait_for_function(
                    """(expected) => {
                        const primary = state?.project?.primary_video || {};
                        return (primary?.path || '').split(/[\\\\/]/).pop() === expected;
                    }""",
                    arg=added_path.name,
                )

                primary_text = page.locator(
                    '#media-pane .media-asset-row[data-source-id="primary"]'
                ).inner_text()
                assert added_path.name in primary_text
                assert primary_path.name in page.locator("#media-pane").inner_text()
            finally:
                browser.close()
    finally:
        server.shutdown()
