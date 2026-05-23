export function createMatchView({
  $ = (id) => document.getElementById(id),
  documentObject = document,
  windowObject = window,
  getState = () => ({}),
  getCurrentWorkspaceStageId = () => "",
  getStageCompositeClips = () => [],
  setSelectedStageCompositeStageId = () => {},
  syncControlValue = () => {},
  callApi = async () => null,
  refresh = async () => null,
  refreshStageComposite = async () => null,
  ensureCompositeOutputProfile = async () => null,
  renderJsonDetail = () => {},
  fileName = (value) => value || "",
  activity = () => {},
} = {}) {
  function checkSetupOnceBanner() {
    const banner = $("setup-once-banner");
    if (!banner) return;
    const stages = getState()?.workspace_stage_entries || [];
    banner.hidden = !(stages.length > 1 && stages[0]?.name && stages[0]?.media_loaded);
  }

  function renderWorkspaceStages() {
    const state = getState();
    const list = $("workspace-stage-list");
    if (!list) return;
    const entries = state?.workspace_stage_entries || [];
    list.innerHTML = "";
    const showScoreBadges = $("match-setting-show-score")?.checked ?? true;
    entries.forEach((entry) => {
      const card = documentObject.createElement("div");
      card.className = "match-stage-card";
      card.dataset.stageId = entry.stage_id;
      if (entry.stage_id === getCurrentWorkspaceStageId()) card.classList.add("selected");

      const thumb = documentObject.createElement("div");
      thumb.className = "match-stage-thumb";
      thumb.textContent = entry.thumbnail_path ? "Thumb" : "Clip";

      const number = documentObject.createElement("div");
      number.className = "match-stage-number";
      number.textContent = String(entry.stage_number || entry.order_index || list.children.length + 1);

      const info = documentObject.createElement("div");
      info.className = "match-stage-info";

      const name = documentObject.createElement("h4");
      name.className = "match-stage-name";
      name.textContent = entry.display_name || entry.stage_id || "Untitled Stage";

      const meta = documentObject.createElement("div");
      meta.className = "match-stage-meta";
      const mediaStatus = entry.source_media_present === false ? "No media" : "Media ready";
      const statusSpan = documentObject.createElement("span");
      statusSpan.textContent = mediaStatus;
      meta.appendChild(statusSpan);

      if (entry.override_count || Object.keys(entry.override_values || {}).length) {
        const badge = documentObject.createElement("span");
        badge.className = "badge badge-custom";
        badge.textContent = "Custom";
        meta.appendChild(badge);
      }
      if (entry.inherited_from_first) {
        const badge = documentObject.createElement("span");
        badge.className = "badge badge-shared";
        badge.textContent = "Shared";
        meta.appendChild(badge);
      }
      if (entry.status === "complete") {
        const badge = documentObject.createElement("span");
        badge.className = "badge badge-shared";
        badge.style.cssText = "background: rgba(34,197,94,0.15); color: #22c55e; border: 1px solid rgba(34,197,94,0.3);";
        badge.textContent = "Complete";
        meta.appendChild(badge);
      }
      if (showScoreBadges && entry.metric_summary?.score != null) {
        const scoreSpan = documentObject.createElement("span");
        scoreSpan.textContent = `Score: ${entry.metric_summary.score}`;
        scoreSpan.style.color = "var(--accent)";
        meta.appendChild(scoreSpan);
      }

      info.appendChild(name);
      info.appendChild(meta);

      const actions = documentObject.createElement("div");
      actions.className = "match-stage-actions";

      const openBtn = documentObject.createElement("button");
      openBtn.className = "match-stage-action";
      openBtn.type = "button";
      openBtn.textContent = "Open";
      openBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        setSelectedStageCompositeStageId(entry.stage_id);
        await callApi("/api/workspace/stage/open", { stage_id: entry.stage_id });
        windowObject.setActiveSurface?.("single");
      });

      const removeBtn = documentObject.createElement("button");
      removeBtn.className = "match-stage-action";
      removeBtn.type = "button";
      removeBtn.textContent = "Remove";
      removeBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        if (!windowObject.confirm("Remove this stage from the match?")) return;
        await callApi("/api/workspace/stage/remove", { stage_id: entry.stage_id });
        await refresh();
      });

      const resetBtn = documentObject.createElement("button");
      resetBtn.className = "match-stage-action";
      resetBtn.type = "button";
      resetBtn.textContent = "Reset";
      resetBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        await callApi("/api/workspace/stage/override/reset", { stage_id: entry.stage_id });
        await refresh();
      });

      actions.append(openBtn, removeBtn, resetBtn);
      card.append(thumb, number, info, actions);
      card.addEventListener("click", () => {
        documentObject.querySelectorAll(".match-stage-card").forEach((candidate) => candidate.classList.remove("selected"));
        card.classList.add("selected");
        setSelectedStageCompositeStageId(entry.stage_id);
      });
      list.append(card);
    });

    checkSetupOnceBanner();
    const recap = $("match-recap-panel");
    if (recap && entries.length) {
      recap.innerHTML = `
        <div style="margin-bottom:8px"><strong>Match Recap</strong> - ${entries.length} stages</div>
        <div style="display:flex;flex-direction:column;gap:4px;margin-bottom:8px">
          ${entries.map((entry, index) => `
            <label style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text)">
              <input type="checkbox" class="recap-stage-check" data-stage-id="${entry.stage_id}" checked style="width:auto;min-height:auto;margin:0" />
              ${index + 1}. ${entry.display_name || entry.stage_id}
            </label>
          `).join("")}
        </div>
        <div class="control-grid" style="margin-bottom:8px">
          <label style="font-size:11px">Transition
            <select id="recap-transition" style="font-size:11px;min-height:24px">
              <option value="cut">Cut</option>
              <option value="fade">Fade</option>
              <option value="dissolve">Dissolve</option>
            </select>
          </label>
          <label style="font-size:11px">Result Card
            <select id="recap-result-card" style="font-size:11px;min-height:24px">
              <option value="none">None</option>
              <option value="end">At End</option>
              <option value="each">Per Stage</option>
            </select>
          </label>
        </div>
        <button id="recap-render" class="match-action-button" type="button" style="width:100%">Render Recap</button>
      `;
      $("recap-render")?.addEventListener("click", async () => {
        const selected = [...documentObject.querySelectorAll(".recap-stage-check:checked")].map((checkbox) => checkbox.dataset.stageId);
        await callApi("/api/workspace/recap/render", {
          stage_ids: selected,
          transition: $("recap-transition")?.value || "cut",
          result_card: $("recap-result-card")?.value || "none",
        });
      });
    } else if (recap) {
      recap.innerHTML = '<p class="hint">Create or open a workspace to build a Match Recap.</p>';
    }

    const sharedDefaults = state?.workspace_shared_defaults || {};
    syncControlValue($("shared-frame-profile"), sharedDefaults.frame_profile || "source");
    syncControlValue($("shared-metric-captions"), sharedDefaults.metric_captions || "none");
    syncControlValue($("shared-lead-in"), sharedDefaults.lead_in_card || "none");
    syncControlValue($("shared-brand-mark"), sharedDefaults.brand_mark || "none");

    const overrideEditor = $("stage-override-editor");
    const overrideGrids = overrideEditor?.querySelectorAll(".control-grid");
    const overrideButton = $("override-apply");
    if (overrideEditor && entries.length && getCurrentWorkspaceStageId()) {
      const activeEntry = entries.find((candidate) => candidate.stage_id === getCurrentWorkspaceStageId());
      const overrides = activeEntry?.override_values || {};
      overrideEditor.querySelector("p")?.setAttribute("hidden", "");
      overrideGrids?.forEach((grid) => grid.removeAttribute("hidden"));
      if (overrideButton) overrideButton.removeAttribute("hidden");
      syncControlValue($("override-frame-profile"), overrides.frame_profile || "");
      syncControlValue($("override-metric-captions"), overrides.metric_captions || "");
    } else if (overrideEditor) {
      const hint = overrideEditor.querySelector("p");
      if (hint) hint.removeAttribute("hidden");
      overrideGrids?.forEach((grid) => grid.setAttribute("hidden", ""));
      if (overrideButton) overrideButton.setAttribute("hidden", "");
    }

    const emptyState = documentObject.querySelector(".match-empty-state");
    const sectionHeader = documentObject.querySelector("#view-match .workspace-action-bar");
    const workspaceSections = documentObject.querySelector("#view-match .workspace-sections");
    const matchSidebar = documentObject.querySelector("#view-match .workspace-sidebar");
    const hasWorkspace = Boolean(state?.workspace || state?.workspace_stage_entries?.length);
    const hasStages = entries.length > 0;
    if (emptyState) emptyState.hidden = hasWorkspace;
    if (sectionHeader) sectionHeader.hidden = !hasWorkspace;
    if (workspaceSections) workspaceSections.hidden = !hasWorkspace;
    if (matchSidebar) matchSidebar.hidden = false;
    if (!hasStages && hasWorkspace && list.children.length === 0) {
      list.innerHTML = '<p class="hint" style="padding:12px">No stages yet. Add your first stage.</p>';
    }
  }

  function renderStageComposite() {
    const list = $("stage-composite-list");
    if (!list) return;
    list.innerHTML = "";
    const stageId = getCurrentWorkspaceStageId();
    if (!stageId) {
      list.innerHTML = '<div class="hint">Select a workspace stage to edit Stage Composite clips.</div>';
      return;
    }
    const clips = getStageCompositeClips();
    if (!clips.length) list.innerHTML = '<div class="hint">No clips loaded for this stage.</div>';
    clips.forEach((clip) => {
      const row = documentObject.createElement("div");
      row.className = "automation-row";
      row.dataset.clipId = clip.clip_id;
      const summary = documentObject.createElement("div");
      summary.innerHTML = `<strong>${fileName(clip.source_path || clip.clip_id)}</strong><br><small>${clip.angle_role || "primary"} • sync ${clip.sync_offset_ms || 0} ms • audio ${clip.audio_muted ? "muted" : clip.audio_gain ?? 1}</small>`;
      const actions = documentObject.createElement("div");
      actions.className = "automation-row-actions";
      const align = documentObject.createElement("button");
      align.type = "button";
      align.textContent = "Angle Align";
      align.addEventListener("click", () => callApi("/api/angle/align", { stage_id: stageId, reference_clip_id: clip.clip_id }));
      const audio = documentObject.createElement("button");
      audio.type = "button";
      audio.textContent = "Audio Mix";
      audio.addEventListener("click", async () => {
        await callApi("/api/audio/mix", { stage_id: stageId, clip_id: clip.clip_id, gain: clip.audio_gain === 0 ? 1 : 0, muted: !clip.audio_muted });
        await refreshStageComposite(stageId);
      });
      const cut = documentObject.createElement("button");
      cut.type = "button";
      cut.textContent = "Cut Override";
      cut.addEventListener("click", async () => {
        const outputId = await ensureCompositeOutputProfile(stageId);
        if (!outputId) return;
        await callApi("/api/angle/director/override", { stage_id: stageId, clip_id: clip.clip_id, output_id: outputId, position: 0, start_ms: 0, duration_ms: 1000 });
        const plan = await callApi("/api/angle/director/plan", { stage_id: stageId, output_id: outputId });
        renderJsonDetail("output-profile-detail", plan);
      });
      const remove = documentObject.createElement("button");
      remove.type = "button";
      remove.textContent = "Remove";
      remove.addEventListener("click", async () => {
        await callApi("/api/workspace/stage/clip/remove", { stage_id: stageId, clip_id: clip.clip_id });
        await refreshStageComposite(stageId);
      });
      actions.append(align, audio, cut, remove);
      row.append(summary, actions);
      list.append(row);
    });
  }

  function persistMatchSettings() {
    const settings = {
      showScoreBadges: $("match-setting-show-score")?.checked ?? true,
      rememberStageSelection: $("match-setting-remember-stage")?.checked ?? true,
    };
    windowObject.localStorage.setItem("splitshot.match.settings", JSON.stringify(settings));
    activity("ui.match.settings.save", settings);
  }

  function applySavedMatchSettings() {
    try {
      const settings = JSON.parse(windowObject.localStorage.getItem("splitshot.match.settings") || "{}");
      if ($("match-setting-show-score")) $("match-setting-show-score").checked = settings.showScoreBadges ?? true;
      if ($("match-setting-remember-stage")) $("match-setting-remember-stage").checked = settings.rememberStageSelection ?? true;
    } catch {}
  }

  return Object.freeze({
    applySavedMatchSettings,
    persistMatchSettings,
    renderStageComposite,
    renderWorkspaceStages,
  });
}
