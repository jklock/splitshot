export function createShotMLPane({
  $ = (id) => document.getElementById(id),
  getState = () => null,
  getShotMLSectionExpansion = () => new Map(),
  syncLocalProjectUiState = () => {},
  scheduleProjectUiStateApply = () => {},
  syncControlValue = () => {},
  syncControlChecked = () => {},
  formatConfidenceValue = (value) => String(value ?? ""),
  renderCollapsibleInspectorSections = () => {},
  callApi = async () => null,
} = {}) {
  function currentState() {
    return getState() || {};
  }

  function currentShotMLSectionExpansion() {
    return getShotMLSectionExpansion() || new Map();
  }

  function shotmlSettings() {
    return currentState()?.project?.analysis?.shotml_settings || {};
  }

  function shotmlControlValue(element) {
    if (!element) return null;
    if (element.type === "checkbox") return Boolean(element.checked);
    if (element.tagName === "SELECT") return element.value;
    const value = element.value;
    if (value === "") return "";
    return Number(value);
  }

  function readShotMLSettingsPayload() {
    const payload = {};
    document.querySelectorAll("[data-shotml-setting]").forEach((element) => {
      payload[element.dataset.shotmlSetting] = shotmlControlValue(element);
    });
    return payload;
  }

  function syncShotMLControls() {
    const settings = shotmlSettings();
    document.querySelectorAll("[data-shotml-setting]").forEach((element) => {
      const key = element.dataset.shotmlSetting;
      if (!key || settings[key] === undefined) return;
      if (element.type === "checkbox") {
        syncControlChecked(element, Boolean(settings[key]));
      } else {
        syncControlValue(element, settings[key]);
      }
    });
  }

  function proposalTypeLabel(type) {
    return {
      move_beep: "Move Beep",
      move_shot: "Move Shot",
      suppress_shot: "Suppress Shot",
      restore_shot: "Restore Shot",
      choose_close_pair_survivor: "Choose Close Pair",
    }[type] || String(type || "Proposal");
  }

  function proposalPreviewText(proposal) {
    const before = proposal.source_time_ms === null || proposal.source_time_ms === undefined
      ? "--"
      : `${(Number(proposal.source_time_ms) / 1000).toFixed(3)}s`;
    const after = proposal.target_time_ms === null || proposal.target_time_ms === undefined
      ? null
      : `${(Number(proposal.target_time_ms) / 1000).toFixed(3)}s`;
    const alternate = proposal.alternate_time_ms === null || proposal.alternate_time_ms === undefined
      ? null
      : `${(Number(proposal.alternate_time_ms) / 1000).toFixed(3)}s`;
    if (after) return `${before} to ${after}`;
    if (alternate) return `${before}; keep ${alternate}`;
    return before;
  }

  function renderShotMLProposals() {
    const list = $("shotml-proposal-list");
    const summary = $("shotml-proposal-summary");
    if (!list || !summary) return;
    const proposals = (currentState()?.project?.analysis?.timing_change_proposals || [])
      .filter((proposal) => proposal.status === "pending");
    summary.textContent = proposals.length
      ? `${proposals.length} pending proposal${proposals.length === 1 ? "" : "s"}.`
      : "No pending proposals.";
    list.replaceChildren();
    if (!proposals.length) {
      const empty = document.createElement("p");
      empty.className = "hint";
      empty.textContent = "Generate proposals after a ShotML run, then apply only the changes that match the video.";
      list.appendChild(empty);
      return;
    }
    proposals.forEach((proposal) => {
      const row = document.createElement("div");
      row.className = "shotml-proposal-row";
      const copy = document.createElement("div");
      copy.className = "shotml-proposal-copy";
      const title = document.createElement("strong");
      const shotLabel = proposal.shot_number ? ` Shot ${proposal.shot_number}` : "";
      title.textContent = `${proposalTypeLabel(proposal.proposal_type)}${shotLabel}`;
      const detail = document.createElement("span");
      const confidence = proposal.confidence === null || proposal.confidence === undefined
        ? ""
        : ` Confidence ${formatConfidenceValue(proposal.confidence)}.`;
      const support = proposal.support_confidence === null || proposal.support_confidence === undefined
        ? ""
        : ` Support ${formatConfidenceValue(proposal.support_confidence)}.`;
      detail.textContent = `${proposalPreviewText(proposal)}.${confidence}${support}`;
      const message = document.createElement("small");
      message.textContent = proposal.message || "Review this timing proposal before applying it.";
      copy.append(title, detail, message);
      const actions = document.createElement("div");
      actions.className = "shotml-proposal-actions";
      const apply = document.createElement("button");
      apply.type = "button";
      apply.textContent = "Apply";
      apply.addEventListener("click", () => callApi("/api/analysis/shotml/apply-proposal", { proposal_id: proposal.id }));
      const discard = document.createElement("button");
      discard.type = "button";
      discard.textContent = "Discard";
      discard.addEventListener("click", () => callApi("/api/analysis/shotml/discard-proposal", { proposal_id: proposal.id }));
      actions.append(apply, discard);
      row.append(copy, actions);
      list.appendChild(row);
    });
  }

  function isShotMLSectionExpanded(sectionId) {
    if (!sectionId) return false;
    if (currentShotMLSectionExpansion().has(sectionId)) return Boolean(currentShotMLSectionExpansion().get(sectionId));
    return false;
  }

  function setShotMLSectionExpanded(sectionId, expanded) {
    if (!sectionId) return;
    currentShotMLSectionExpansion().set(sectionId, Boolean(expanded));
    syncLocalProjectUiState();
    scheduleProjectUiStateApply();
  }

  function renderShotML() {
    syncShotMLControls();
    renderCollapsibleInspectorSections();
    const summary = $("shotml-run-summary");
    const lastRun = currentState()?.project?.analysis?.last_shotml_run_summary || {};
    if (summary) {
      summary.textContent = lastRun.shot_count === undefined
        ? ""
        : `${lastRun.shot_count} shots at threshold ${Number(lastRun.threshold ?? shotmlSettings().detection_threshold ?? 0.5).toFixed(2)}.`;
    }
    renderShotMLProposals();
  }

  return Object.freeze({
    shotmlSettings,
    shotmlControlValue,
    readShotMLSettingsPayload,
    syncShotMLControls,
    proposalTypeLabel,
    proposalPreviewText,
    renderShotMLProposals,
    isShotMLSectionExpanded,
    setShotMLSectionExpanded,
    renderShotML,
  });
}
