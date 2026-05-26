export function createLibraryView({
  $ = (id) => document.getElementById(id),
  documentObject = document,
  windowObject = window,
  getLibrary = () => ({ stages: [], matches: [] }),
  getSelectedLibraryRecord = () => null,
  setSelectedLibraryRecord = () => {},
  callApi = async () => null,
  renderJsonDetail = () => {},
  activity = () => {},
} = {}) {
  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function currentRecords() {
    const library = getLibrary() || { stages: [], matches: [] };
    return [
      ...(library.stages || []).map((record) => ({ ...record, record_type: "stage" })),
      ...(library.matches || []).map((record) => ({ ...record, record_type: "match" })),
    ];
  }

  function libraryRecordId(record) {
    return record?.library_record_id || record?.stage_id || record?.match_id || "";
  }

  function recordDisplayName(record) {
    return record?.display_name || record?.competitor_name || libraryRecordId(record) || "Untitled";
  }

  function formatTimestamp(value) {
    if (!value) return "--";
    try {
      return new Date(value).toLocaleString();
    } catch {
      return String(value);
    }
  }

  function normalizedDiscipline(record) {
    const raw = String(record?.discipline || "")
      .trim()
      .toLowerCase()
      .replace(/[\s-]+/g, "_");
    if (raw.startsWith("uspsa")) return "uspsa";
    if (raw.startsWith("idpa")) return "idpa";
    return raw;
  }

  function recordMatchesSearch(record, searchTerm) {
    if (!searchTerm) return true;
    const haystack = [
      record?.display_name,
      record?.competitor_name,
      record?.event_date,
      record?.discipline,
      record?.stage_id,
      record?.match_id,
      record?.library_record_id,
    ]
      .map((value) => String(value || "").toLowerCase())
      .join(" ");
    return haystack.includes(searchTerm);
  }

  function resolveSelectedRecord(records = []) {
    const selectedRecordId = libraryRecordId(getSelectedLibraryRecord());
    const current = records.find((record) => libraryRecordId(record) === selectedRecordId) || null;
    const nextRecord = current || records[0] || null;
    if (nextRecord && libraryRecordId(nextRecord) !== selectedRecordId) {
      setSelectedLibraryRecord(nextRecord);
    }
    return nextRecord;
  }

  function renderInspectorPanels(records = [], selectedRecord = null, { searchTerm = "", filterDiscipline = "" } = {}) {
    const overviewStatus = $("library-overview-inspector-status");
    const overviewPanel = $("library-overview-inspector-panel");
    const analyticsStatus = $("library-analytics-inspector-status");
    const analyticsPanel = $("library-analytics-inspector-panel");
    const detailStatus = $("library-detail-actions-status");

    if (overviewStatus) {
      overviewStatus.textContent = `${records.length} visible record(s)${filterDiscipline ? ` • ${filterDiscipline.toUpperCase()}` : ""}`;
    }
    if (overviewPanel) {
      overviewPanel.innerHTML = `
        <dl class="details workspace-summary-list">
          <div><dt>Visible records</dt><dd>${escapeHtml(records.length)}</dd></div>
          <div><dt>Search</dt><dd>${escapeHtml(searchTerm || "No search filter")}</dd></div>
          <div><dt>Discipline</dt><dd>${escapeHtml(filterDiscipline ? filterDiscipline.toUpperCase() : "All disciplines")}</dd></div>
          <div><dt>Selected</dt><dd>${escapeHtml(selectedRecord ? recordDisplayName(selectedRecord) : "No record selected")}</dd></div>
        </dl>
      `;
    }

    if (analyticsStatus) {
      analyticsStatus.textContent = selectedRecord
        ? `${recordDisplayName(selectedRecord)} • ${selectedRecord.discipline || "No discipline"}`
        : "Charts reflect the current filter scope.";
    }
    if (analyticsPanel) {
      analyticsPanel.innerHTML = `
        <dl class="details workspace-summary-list">
          <div><dt>Current scope</dt><dd>${escapeHtml(filterDiscipline ? filterDiscipline.toUpperCase() : "All records")}</dd></div>
          <div><dt>Selected record</dt><dd>${escapeHtml(selectedRecord ? recordDisplayName(selectedRecord) : "No record selected")}</dd></div>
          <div><dt>Event date</dt><dd>${escapeHtml(selectedRecord?.event_date || "--")}</dd></div>
          <div><dt>Updated</dt><dd>${escapeHtml(formatTimestamp(selectedRecord?.updated_at || selectedRecord?.event_date))}</dd></div>
        </dl>
        <p class="hint workspace-panel-note">Use the Performance rail to switch between overview, filters, detail actions, analytics notes, backup, and settings while keeping the selected record in view below.</p>
      `;
    }

    if (detailStatus) {
      detailStatus.textContent = selectedRecord
        ? `Working with ${recordDisplayName(selectedRecord)}`
        : "Select a record to reopen, tag, or annotate it.";
    }
  }

  function renderLibrarySummaryTiles() {
    const container = $("library-summary-tiles");
    if (!container) return;
    const library = getLibrary() || { stages: [], matches: [] };
    const stageRecords = library.stages || [];
    const matchRecords = library.matches || [];
    const records = currentRecords();
    const totalStages = stageRecords.length;
    const totalMatches = matchRecords.length;
    const personalBest = records.filter((record) => record.score != null).sort((a, b) => (b.score || 0) - (a.score || 0))[0];
    const personalBestVal = personalBest ? `${personalBest.score} (${personalBest.display_name || "--"})` : "--";
    const recentCount = records.filter((record) => {
      if (!record.event_date) return false;
      const recordDate = new Date(record.event_date);
      const monthAgo = new Date();
      monthAgo.setMonth(monthAgo.getMonth() - 1);
      return recordDate >= monthAgo;
    }).length;
    container.innerHTML = `
      <div class="library-tile"><span class="library-tile-value">${totalStages}</span><span class="library-tile-label">Total Stages</span></div>
      <div class="library-tile"><span class="library-tile-value">${totalMatches}</span><span class="library-tile-label">Total Matches</span></div>
      <div class="library-tile"><span class="library-tile-value">${escapeHtml(personalBestVal)}</span><span class="library-tile-label">Personal Best</span></div>
      <div class="library-tile"><span class="library-tile-value">${recentCount}</span><span class="library-tile-label">Recent (30d)</span></div>
    `;
  }

  function renderLibraryTags() {
    const container = $("library-tag-list");
    if (!container) return;
    const tags = getSelectedLibraryRecord()?.tags || [];
    container.innerHTML = tags.map((tag) => `
      <span class="library-tag">
        ${escapeHtml(tag)}
        <span class="tag-remove" data-tag="${escapeHtml(tag)}" title="Remove tag">×</span>
      </span>
    `).join("") || '<span class="hint" style="font-size:0.6875rem">No tags</span>';
  }

  function renderPersonalBests() {
    const container = $("personal-bests-list");
    if (!container) return;
    const records = currentRecords();
    if (records.length === 0) {
      container.innerHTML = '<p class="hint">Add records to see personal bests.</p>';
      return;
    }
    const sorted = [...records].filter((record) => record.score != null).sort((a, b) => b.score - a.score).slice(0, 5);
    container.innerHTML = sorted.map((record, index) => `
      <div class="library-record-row">
        <span class="record-rank">#${index + 1}</span>
        <span class="record-name">${escapeHtml(record.display_name || record.competitor_name || "Unknown")}</span>
        <span class="record-score">${escapeHtml(record.score)}</span>
        <span class="record-discipline">${escapeHtml(record.discipline || "")}</span>
      </div>
    `).join("");
  }

  async function fetchLibraryAnalytics(discipline) {
    try {
      return await callApi("/api/library/analytics/trend", {
        metric_key: "score",
        discipline: discipline || "",
      });
    } catch {
      return null;
    }
  }

  function renderAnalyticsCharts(data) {
    const scoreTrend = Array.isArray(data?.trend_points) ? data.trend_points : [];
    const disciplineBreakdown = Array.isArray(data?.discipline_breakdown) ? data.discipline_breakdown : [];
    const totalRecords = Number(data?.total_records ?? data?.records ?? 0);

    const trendEl = $("analytics-score-trend");
    if (trendEl) {
      if (scoreTrend.length === 0) {
        trendEl.innerHTML = '<p class="hint">Add scored Performance records to see a score trend.</p>';
      } else if (scoreTrend.length < 2) {
        trendEl.innerHTML = '<p class="hint">Add at least one more scored record to compare performance over time.</p>';
      } else {
        const maxScore = Math.max(...scoreTrend.map((entry) => entry.score || 0), 1);
        trendEl.innerHTML = `
          <div class="chart-bar-container" style="display:flex;align-items:flex-end;gap:2px;height:120px;padding:4px">
            ${scoreTrend.map((entry) => {
              const height = Math.round(((entry.score || 0) / maxScore) * 100);
              return `<div class="chart-bar" style="height:${height}%;flex:1;background:var(--surface-2);min-width:8px;position:relative" title="${escapeHtml(entry.date || "")}: ${escapeHtml(entry.score || 0)}">
                <span style="position:absolute;top:-18px;left:50%;transform:translateX(-50%);font-size:9px;color:var(--muted)">${escapeHtml(entry.score || "")}</span>
              </div>`;
            }).join("")}
          </div>
        `;
      }
    }

    const disciplineEl = $("analytics-discipline-chart");
    if (disciplineEl) {
      if (disciplineBreakdown.length === 0) {
        disciplineEl.innerHTML = '<p class="hint">Add Performance records to see discipline breakdown.</p>';
      } else {
        const maxCount = Math.max(...disciplineBreakdown.map((entry) => entry.count), 1);
        disciplineEl.innerHTML = `
          <div class="discipline-bars">
            ${disciplineBreakdown.map((entry) => `
              <div class="discipline-bar">
                <span class="bar-label">${escapeHtml(String(entry.discipline || "").toUpperCase())}</span>
                <span class="bar-fill" style="width:${Math.round((entry.count / maxCount) * 100)}%">${escapeHtml(entry.count)}</span>
              </div>
            `).join("")}
          </div>
        `;
      }
    }

    const outlierEl = $("analytics-outliers");
    if (outlierEl) {
      if (Array.isArray(data?.outliers) && data.outliers.length > 0) {
        outlierEl.innerHTML = data.outliers.map((entry) => `
          <div class="library-record-row">
            <span class="record-name">${escapeHtml(entry.name || "Unknown")}</span>
            <span class="record-score">${escapeHtml(entry.score)}</span>
            <span class="record-discipline">${escapeHtml(entry.direction === "high" ? "High" : "Low")}</span>
          </div>
        `).join("");
      } else if (totalRecords === 0) {
        outlierEl.innerHTML = '<p class="hint">Add Performance records to see outlier detection.</p>';
      } else if (totalRecords < 4) {
        outlierEl.innerHTML = '<p class="hint">Add more records to surface statistically meaningful outliers.</p>';
      } else {
        outlierEl.innerHTML = '<p class="hint">No significant outliers detected.</p>';
      }
    }
  }

  function renderPerformanceLibrary() {
    renderLibrarySummaryTiles();
    const list = $("library-record-list");
    if (!list) return;
    const allRecords = currentRecords();
    const filterDiscipline = $("library-filter-discipline")?.value || "";
    const sortBy = $("library-sort")?.value || "event_date";
    const searchTerm = String($("library-search")?.value || "").trim().toLowerCase();
    let filtered = [...allRecords];
    if (filterDiscipline) {
      filtered = filtered.filter((record) => normalizedDiscipline(record) === filterDiscipline);
    }
    if (searchTerm) {
      filtered = filtered.filter((record) => recordMatchesSearch(record, searchTerm));
    }
    if (sortBy === "score") filtered.sort((a, b) => (b.score || 0) - (a.score || 0));
    else if (sortBy === "display_name") filtered.sort((a, b) => (a.display_name || "").localeCompare(b.display_name || ""));
    else if (sortBy === "discipline") filtered.sort((a, b) => (a.discipline || "").localeCompare(b.discipline || ""));
    const selectedRecord = resolveSelectedRecord(filtered);
    const selectedRecordId = libraryRecordId(selectedRecord);
    const detailStatus = $("library-detail-status");
    const overviewStatus = $("library-overview-status");
    const recordsStatus = $("library-records-status");
    const emptyState = documentObject.querySelector(".library-empty-state");
    const reviewGrid = documentObject.querySelector("#view-library .library-review-grid");
    const librarySidebar = documentObject.querySelector("#view-library .workspace-sidebar");
    const libraryTitle = $("library-workspace-title");
    const libraryStatus = $("library-workspace-status");
    const hasAnyRecords = allRecords.length > 0;
    const hasVisibleRecords = filtered.length > 0;
    list.innerHTML = "";
    if (!filtered.length) {
      list.innerHTML = `<div class="hint">${hasAnyRecords ? "No records match the current filters." : "No performance records yet."}</div>`;
      renderPersonalBests();
      if (detailStatus) detailStatus.textContent = "Select a Performance record.";
      const recordDetail = $("library-record-detail");
      if (recordDetail) recordDetail.textContent = "Select a library record.";
      renderInspectorPanels([], null, { searchTerm, filterDiscipline });
      if (emptyState) emptyState.hidden = hasAnyRecords;
      if (reviewGrid) reviewGrid.hidden = !hasAnyRecords;
      if (librarySidebar) librarySidebar.hidden = false;
      if (libraryTitle) libraryTitle.textContent = "Performance Library";
      if (libraryStatus) {
        libraryStatus.textContent = hasAnyRecords
          ? `0 visible record(s)${searchTerm ? ` • search: ${searchTerm}` : ""}`
          : "Waiting for performance records.";
      }
      return;
    }
    if (overviewStatus) {
      overviewStatus.textContent = `${filtered.length} visible record(s)${searchTerm ? ` • search: ${searchTerm}` : ""}`;
    }
    if (recordsStatus) {
      recordsStatus.textContent = `${filtered.length} record(s) sorted by ${sortBy.replace("_", " ")}`;
    }
    filtered.forEach((record) => {
      const id = record.library_record_id || record.stage_id || record.match_id;
      const row = documentObject.createElement("div");
      row.className = "library-record-row";
      row.dataset.recordId = id;
      if (selectedRecordId && id === selectedRecordId) row.classList.add("selected");
      row.innerHTML = `
        <span class="library-record-name">${escapeHtml(record.display_name || id || "Untitled")}</span>
        <span class="library-record-date">${escapeHtml(record.event_date || "--")}</span>
        <span class="library-record-discipline">${escapeHtml(record.discipline || "--")}</span>
        <span class="library-record-score">${escapeHtml(record.score != null ? record.score : "--")}</span>
      `;
      row.addEventListener("click", () => {
        documentObject.querySelectorAll(".library-record-row").forEach((candidate) => candidate.classList.remove("selected"));
        row.classList.add("selected");
        setSelectedLibraryRecord(record);
        if (detailStatus) {
          detailStatus.textContent = `${recordDisplayName(record)} • ${record.discipline || "No discipline"}`;
        }
        renderJsonDetail("library-record-detail", record);
        const tagsEditor = $("library-tags-editor");
        const notesEditor = $("library-notes-editor");
        const recordActions = $("library-record-actions");
        if (tagsEditor) tagsEditor.hidden = false;
        if (notesEditor) notesEditor.hidden = false;
        if (recordActions) recordActions.hidden = false;
        renderLibraryTags();
        const notesText = $("library-notes-text");
        if (notesText) notesText.value = record.notes || "";
        renderInspectorPanels(filtered, record, { searchTerm, filterDiscipline });
      });
      list.appendChild(row);
    });
    renderPersonalBests();

    if (selectedRecord && selectedRecordId) {
      const tagsEditor = $("library-tags-editor");
      const notesEditor = $("library-notes-editor");
      const recordActions = $("library-record-actions");
      if (tagsEditor) tagsEditor.hidden = false;
      if (notesEditor) notesEditor.hidden = false;
      if (recordActions) recordActions.hidden = false;
      if (detailStatus) {
        detailStatus.textContent = `${recordDisplayName(selectedRecord)} • ${selectedRecord.discipline || "No discipline"}`;
      }
      renderJsonDetail("library-record-detail", selectedRecord);
      renderLibraryTags();
      const notesText = $("library-notes-text");
      if (notesText) notesText.value = selectedRecord.notes || "";
    } else {
      const tagsEditor = $("library-tags-editor");
      const notesEditor = $("library-notes-editor");
      const recordActions = $("library-record-actions");
      if (tagsEditor) tagsEditor.hidden = true;
      if (notesEditor) notesEditor.hidden = true;
      if (recordActions) recordActions.hidden = true;
      const recordDetail = $("library-record-detail");
      if (recordDetail) recordDetail.textContent = "Select a library record.";
      const notesText = $("library-notes-text");
      if (notesText) notesText.value = "";
      if (detailStatus) detailStatus.textContent = "Select a Performance record.";
    }
    renderInspectorPanels(filtered, selectedRecord, { searchTerm, filterDiscipline });

    if (emptyState) emptyState.hidden = true;
    if (reviewGrid) reviewGrid.hidden = false;
    if (librarySidebar) librarySidebar.hidden = false;
    if (libraryTitle) libraryTitle.textContent = "Performance Library";
    if (libraryStatus) {
      libraryStatus.textContent = hasVisibleRecords
        ? `${filtered.length} visible record(s)${searchTerm ? ` • search: ${searchTerm}` : ""}`
        : "Waiting for performance records.";
    }
  }

  function addLibraryTag(tag) {
    const record = getSelectedLibraryRecord();
    if (!record) return;
    record.tags = record.tags || [];
    if (!record.tags.includes(tag)) {
      record.tags.push(tag);
      renderLibraryTags();
    }
  }

  function removeLibraryTag(tag) {
    const record = getSelectedLibraryRecord();
    if (!record?.tags) return;
    record.tags = record.tags.filter((candidate) => candidate !== tag);
    renderLibraryTags();
  }

  function saveLibraryNotes(notes) {
    const record = getSelectedLibraryRecord();
    if (!record) return;
    record.notes = notes;
    activity("ui.library.notes.save");
  }

  function persistLibrarySettings() {
    const settings = {
      defaultSort: $("library-setting-default-sort")?.value || "event_date",
      autoRefresh: $("library-setting-auto-refresh")?.checked ?? true,
    };
    windowObject.localStorage.setItem("splitshot.library.settings", JSON.stringify(settings));
    activity("ui.library.settings.save", settings);
  }

  function applySavedLibrarySettings() {
    try {
      const settings = JSON.parse(windowObject.localStorage.getItem("splitshot.library.settings") || "{}");
      if ($("library-setting-default-sort")) $("library-setting-default-sort").value = settings.defaultSort || "event_date";
      if ($("library-sort")) $("library-sort").value = settings.defaultSort || "event_date";
      if ($("library-setting-auto-refresh")) $("library-setting-auto-refresh").checked = settings.autoRefresh ?? true;
    } catch {}
  }

  function libraryAutoRefreshEnabled() {
    return $("library-setting-auto-refresh")?.checked ?? true;
  }

  return Object.freeze({
    addLibraryTag,
    applySavedLibrarySettings,
    fetchLibraryAnalytics,
    libraryAutoRefreshEnabled,
    persistLibrarySettings,
    removeLibraryTag,
    renderAnalyticsCharts,
    renderLibrarySummaryTiles,
    renderLibraryTags,
    renderPerformanceLibrary,
    renderPersonalBests,
    saveLibraryNotes,
  });
}
