import { createPaneBase } from "./pane-base.js";

export function createMetricsPane({
  $ = (id) => document.getElementById(id),
  documentObject = document,
  windowObject = window,
  getState = () => null,
  getMetricsSectionExpansion = () => new Map(),
  activity = () => {},
  syncLocalProjectUiState = () => {},
  scheduleProjectUiStateApply = () => {},
  scheduleReviewStageRestore = () => {},
  syncExpandWaveformButton = () => {},
  withPreservedScrollState = (_elements, callback) => callback(),
  splitRowShotMLConfidence = () => null,
  splitRowShotMLSplitMs = () => null,
  splitRowShotMLCumulativeMs = () => null,
  splitRowFinalTimeMs = () => null,
  splitRowSequenceTotalMs = () => null,
  splitRowActionSummary = () => "",
  splitRowActions = () => [],
  splitRowCumulativeMs = () => null,
  splitRowIntervalLabel = () => "",
  splitRowEntryLabel = () => "Entry",
  defaultScoreLetter = () => "A",
  formatPenaltyCountsText = () => "",
  splitSeconds = (value) => String(value ?? ""),
  numericMs = (value) => value,
  signedSeconds = (value) => String(value ?? ""),
  formatConfidenceValue = (value) => String(value ?? ""),
  formatNumber = (value) => String(value ?? ""),
  precise = (value) => String(value ?? ""),
  fileName = (value) => String(value ?? ""),
  renderDetailsList = () => {},
  setStatus = () => {},
  ensureSectionToggle = () => {},
  metricsTableColumns = [],
} = {}) {
  function currentState() {
    return getState() || {};
  }

  function metricsSectionExpansion() {
    return getMetricsSectionExpansion() || new Map();
  }

  const paneBase = createPaneBase({
    $,
    getRoot: () => $("cockpit-root"),
    getExpandedState: () => Boolean($("cockpit-root")?.classList.contains("metrics-expanded")),
    setExpandedState: () => {},
    expandedClass: "metrics-expanded",
    sectionId: "metrics-workbench",
    collapseClasses: ["waveform-expanded", "timing-expanded", "scoring-expanded", "markers-expanded"],
    syncUiState: () => {
      syncExpandWaveformButton();
      syncLocalProjectUiState();
    },
    persistUiState: () => {
      scheduleProjectUiStateApply();
    },
    activity,
    activityName: "metrics.expand",
    onExpand: () => {
      syncExpandWaveformButton();
      renderMetricsPanel();
    },
    onCollapse: () => {
      syncExpandWaveformButton();
      scheduleReviewStageRestore();
    },
  });

  function buildMetricsRows() {
    const state = currentState();
    const segmentsByShotId = new Map((state.timing_segments || []).map((segment) => [segment.shot_id, segment]));
    const beepMs = numericMs(state?.metrics?.beep_ms);
    const defaultScore = defaultScoreLetter();
    const importedRawSeconds = state?.scoring_summary?.imported_stage?.raw_seconds;
    const importedRawMs = importedRawSeconds === null || importedRawSeconds === undefined
      ? null
      : Math.round(Number(importedRawSeconds) * 1000);
    const shotRows = (state.split_rows || []).filter((item) => item.shot_id);
    const finalShotRowId = shotRows.length ? shotRows[shotRows.length - 1].shot_id : null;
    return (state.split_rows || []).map((row) => {
      const segment = row.shot_id ? (segmentsByShotId.get(row.shot_id) || null) : null;
      const absoluteMs = numericMs(row.absolute_time_ms);
      const fallbackCumulativeMs = numericMs(segment?.cumulative_ms) ?? (
        absoluteMs === null
          ? null
          : (beepMs === null ? absoluteMs : Math.max(0, absoluteMs - beepMs))
      );
      const confidence = splitRowShotMLConfidence(row);
      const shotmlSplitMs = splitRowShotMLSplitMs(row);
      const adjustmentMs = numericMs(row.adjustment_ms) ?? 0;
      const finalTimeMs = splitRowFinalTimeMs(row);
      const finalSplitMs = numericMs(row.split_ms);
      const shotmlCumulativeMs = splitRowShotMLCumulativeMs(row);
      const rawDeltaMs = importedRawMs === null || finalTimeMs === null || row.shot_id !== finalShotRowId
        ? null
        : finalTimeMs - importedRawMs;
      const penaltyCounts = segment?.penalty_counts || row.penalty_counts;
      return {
        rowId: row.row_id,
        rowType: row.row_type,
        shotId: row.shot_id,
        shotNumber: row.shot_number,
        label: splitRowEntryLabel(row),
        intervalLabel: splitRowIntervalLabel(row),
        intervalKind: String(row.interval_kind || ""),
        absoluteMs,
        splitMs: finalSplitMs,
        shotmlSplitMs,
        adjustmentMs,
        sequenceTotalMs: splitRowSequenceTotalMs(row),
        cumulativeMs: finalTimeMs ?? numericMs(row.cumulative_ms) ?? fallbackCumulativeMs,
        shotmlCumulativeMs,
        actionSummary: splitRowActionSummary(row),
        actions: splitRowActions(row).map((action) => ({
          eventId: action.event_id || null,
          kind: action.kind || "",
          label: action.label || "",
          placement: action.placement || "interval",
          synthetic: Boolean(action.synthetic),
          resetsSequence: Boolean(action.resets_sequence),
        })),
        resetsSequence: Boolean(row.resets_sequence),
        scoreLetter: segment?.score_letter || row.score_letter || defaultScore,
        penaltyText: formatPenaltyCountsText(penaltyCounts),
        confidence,
        practiscoreMs: importedRawMs,
        rawDeltaMs,
      };
    });
  }

  function metricsPractiScoreLabel(entry) {
    if (entry.rawDeltaMs === null || entry.rawDeltaMs === undefined) return "--";
    const prefix = entry.rawDeltaMs > 0 ? "+" : "";
    return `${prefix}${precise(entry.rawDeltaMs)}s`;
  }

  function renderMetricsTable(table) {
    if (!table) return;
    table.innerHTML = "";
    const rows = buildMetricsRows();
    table.style.gridTemplateColumns = "minmax(0, 1.15fr) minmax(0, 0.72fr) minmax(0, 0.72fr) minmax(0, 0.72fr) minmax(0, 0.72fr) minmax(0, 0.48fr) minmax(0, 1fr) minmax(0, 0.7fr) minmax(0, 0.7fr) minmax(0, 0.7fr) minmax(0, 1.15fr)";
    metricsTableColumns.forEach(([label]) => {
      const header = documentObject.createElement("div");
      header.className = "head";
      header.textContent = label;
      table.appendChild(header);
    });
    rows.forEach((entry) => {
      const cells = [
        entry.label,
        splitSeconds(entry.shotmlSplitMs),
        signedSeconds(entry.adjustmentMs || 0),
        splitSeconds(entry.splitMs),
        splitSeconds(entry.cumulativeMs),
        entry.scoreLetter || "--",
        entry.penaltyText || "--",
        entry.practiscoreMs === null || entry.practiscoreMs === undefined ? "--" : splitSeconds(entry.practiscoreMs),
        metricsPractiScoreLabel(entry),
        formatConfidenceValue(entry.confidence),
        entry.actionSummary || "--",
      ];
      cells.forEach((value) => {
        const cell = documentObject.createElement("div");
        cell.textContent = value || "--";
        table.appendChild(cell);
      });
    });
  }

  function renderMetricsTrendTable(table) {
    if (!table) return;
    table.innerHTML = "";
    const rows = buildMetricsRows();
    table.style.gridTemplateColumns = "minmax(0, 1.1fr) minmax(0, 0.68fr) minmax(0, 0.68fr) minmax(0, 0.5fr) minmax(0, 0.72fr) minmax(0, 1.05fr)";
    ["Shot", "Split", "Run", "Score", "ShotML", "Action"].forEach((label) => {
      const header = documentObject.createElement("div");
      header.className = "head";
      header.textContent = label;
      table.appendChild(header);
    });
    if (rows.length === 0) {
      const empty = documentObject.createElement("div");
      empty.className = "metrics-table-empty";
      empty.textContent = "No timing segments yet.";
      table.appendChild(empty);
      return;
    }
    rows.forEach((entry) => {
      [
        entry.intervalLabel ? `${entry.label} ${entry.intervalLabel}` : entry.label,
        splitSeconds(entry.splitMs),
        splitSeconds(entry.sequenceTotalMs),
        entry.scoreLetter || "--",
        formatConfidenceValue(entry.confidence),
        entry.actionSummary || "--",
      ].forEach((value) => {
        const cell = documentObject.createElement("div");
        cell.textContent = value || "--";
        table.appendChild(cell);
      });
    });
  }

  function metricsSecondsValue(value) {
    if (value === null || value === undefined || value === "") return null;
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return null;
    return Number((numeric / 1000).toFixed(3));
  }

  function metricsPercentValue(value) {
    if (value === null || value === undefined || value === "") return null;
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return null;
    return Number((numeric * 100).toFixed(1));
  }

  function metricsMedian(values = []) {
    const sorted = values
      .map((value) => Number(value))
      .filter((value) => Number.isFinite(value))
      .sort((left, right) => left - right);
    if (sorted.length === 0) return null;
    const middle = Math.floor(sorted.length / 2);
    if (sorted.length % 2 === 1) return sorted[middle];
    return Number((((sorted[middle - 1] + sorted[middle]) / 2)).toFixed(3));
  }

  function metricsCategoryDefinition(id) {
    return {
      first_shot: { id: "first_shot", label: "First shot", shortLabel: "First", color: "#f59e0b" },
      shooting_interval: { id: "shooting_interval", label: "Shooting interval", shortLabel: "Shoot", color: "#39d06f" },
      transition: { id: "transition", label: "Transition / movement", shortLabel: "Move", color: "#4ea7ff" },
      reload_manipulation: { id: "reload_manipulation", label: "Reload / manipulation", shortLabel: "Reload", color: "#ef4444" },
      dead_time: { id: "dead_time", label: "Dead time", shortLabel: "Dead", color: "#f97316" },
      unknown: { id: "unknown", label: "Unknown", shortLabel: "Unknown", color: "#a855f7" },
    }[id] || { id: "unknown", label: "Unknown", shortLabel: "Unknown", color: "#a855f7" };
  }

  function metricsIntervalText(entry) {
    return [
      String(entry.intervalKind || ""),
      String(entry.intervalLabel || ""),
      String(entry.actionSummary || ""),
      ...(entry.actions || []).map((action) => `${action.kind || ""} ${action.label || ""}`),
    ]
      .join(" ")
      .trim()
      .toLowerCase();
  }

  function metricsMeaningfulIntervalLabel(entry) {
    const label = String(entry.intervalLabel || "").trim();
    if (!label || ["Draw", "Split", "Start"].includes(label)) return "";
    return label;
  }

  function metricsCadenceBaselineMs(entries = []) {
    const candidates = entries
      .filter((entry) => Number(entry.shotNumber || 0) > 1)
      .filter((entry) => numericMs(entry.splitMs) !== null)
      .filter((entry) => {
        const kind = String(entry.intervalKind || "").trim().toLowerCase();
        return !["reload", "malfunction", "custom_label"].includes(kind);
      })
      .map((entry) => Number(entry.splitMs))
      .filter((value) => value > 0)
      .sort((left, right) => left - right);
    const sample = candidates.slice(0, Math.max(1, Math.ceil(candidates.length * 0.6)));
    const baseline = metricsMedian(sample.length > 0 ? sample : candidates);
    return baseline === null ? 350 : Math.max(120, baseline);
  }

  function metricsIntervalClassification(entry, { cadenceBaselineMs = 350 } = {}) {
    const kind = String(entry.intervalKind || "").trim().toLowerCase();
    const labelText = metricsIntervalText(entry);
    const splitMs = numericMs(entry.splitMs);
    const transitionThresholdMs = Math.max(360, cadenceBaselineMs * 1.75);
    const deadTimeThresholdMs = Math.max(900, cadenceBaselineMs * 4.25);

    if (Number(entry.shotNumber || 0) === 1 || kind === "draw" || kind === "start") {
      return metricsCategoryDefinition("first_shot");
    }
    if (
      kind === "reload"
      || kind === "malfunction"
      || /(reload|malfunction|clear|rack|stoppage|jam|manip|mag\b)/.test(labelText)
    ) {
      return metricsCategoryDefinition("reload_manipulation");
    }
    if (/(transition|move|movement|position|entry|exit|cross|sprint|step|turn)/.test(labelText)) {
      return metricsCategoryDefinition("transition");
    }
    if (splitMs !== null && splitMs >= deadTimeThresholdMs) {
      return metricsCategoryDefinition("dead_time");
    }
    if (kind === "custom_label") {
      return metricsCategoryDefinition("unknown");
    }
    if (splitMs !== null && splitMs <= transitionThresholdMs) {
      return metricsCategoryDefinition("shooting_interval");
    }
    if (splitMs !== null) {
      return metricsCategoryDefinition("transition");
    }
    return metricsCategoryDefinition("unknown");
  }

  function metricsSegmentShortLabel(label) {
    const normalized = String(label || "").trim();
    if (!normalized) return "Segment";
    if (normalized.startsWith("Shooting sequence")) return normalized.replace("Shooting sequence", "Seq");
    if (normalized === "Start / first shot") return "Start";
    if (normalized === "Transition / movement") return "Move";
    if (normalized === "Reload / manipulation") return "Reload";
    if (normalized === "Dead time") return "Dead";
    if (normalized.length <= 10) return normalized;
    return `${normalized.slice(0, 9).trimEnd()}…`;
  }

  function metricsStageSegmentLabel(point, category = point.category) {
    const customLabel = metricsMeaningfulIntervalLabel(point);
    if (category.id === "first_shot") return "Start / first shot";
    if (category.id === "reload_manipulation") return "Reload / manipulation";
    if (category.id === "transition") return customLabel || "Transition / movement";
    if (category.id === "dead_time") return customLabel || "Dead time";
    if (category.id === "unknown") return customLabel || "Unknown";
    return category.label;
  }

  function buildMetricsStageSegments(points = []) {
    const segments = [];
    let sequenceIndex = 0;
    let shootingSequence = null;
    const flushShootingSequence = () => {
      if (!shootingSequence) return;
      segments.push(shootingSequence);
      shootingSequence = null;
    };

    points.forEach((point) => {
      const durationS = Number(point.finalSplitS);
      if (!Number.isFinite(durationS)) return;
      if (point.category.id === "shooting_interval") {
        if (!shootingSequence) {
          sequenceIndex += 1;
          shootingSequence = {
            key: `shooting_sequence_${sequenceIndex}`,
            label: `Shooting sequence ${sequenceIndex}`,
            shortLabel: `Seq ${sequenceIndex}`,
            value: 0,
            category: metricsCategoryDefinition("shooting_interval"),
            pairLabels: [],
          };
        }
        shootingSequence.value = Number((shootingSequence.value + durationS).toFixed(3));
        shootingSequence.pairLabels.push(point.pairLabel);
        return;
      }

      flushShootingSequence();
      const label = metricsStageSegmentLabel(point, point.category);
      segments.push({
        key: `${point.category.id}_${point.shotNumber}`,
        label,
        shortLabel: metricsSegmentShortLabel(label),
        value: durationS,
        category: point.category,
        pairLabels: [point.pairLabel],
      });
    });

    flushShootingSequence();
    return segments;
  }

  function metricsGraphLabel(entry, fallbackShotNumber) {
    const shotNumber = entry.shotNumber || fallbackShotNumber;
    if (entry.intervalLabel) return `${entry.label} ${entry.intervalLabel}`;
    if (entry.label) return entry.label;
    return `Shot ${shotNumber}`;
  }

  function buildMetricsGraphSeries(rows = buildMetricsRows()) {
    const shotRows = rows.filter((entry) => entry.shotId);
    if (shotRows.length === 0) return [];
    const cadenceBaselineMs = metricsCadenceBaselineMs(shotRows);
    const graphPoints = shotRows.map((entry, index) => {
      const shotNumber = entry.shotNumber || index + 1;
      const category = metricsIntervalClassification(entry, { cadenceBaselineMs });
      const runTotalS = metricsSecondsValue(entry.cumulativeMs);
      const referenceRunS = metricsSecondsValue(entry.shotmlCumulativeMs);
      return {
        shotNumber,
        label: metricsGraphLabel(entry, index + 1),
        pairLabel: shotNumber === 1 ? "Start→1" : `${shotNumber - 1}→${shotNumber}`,
        intervalKind: entry.intervalKind,
        intervalLabel: entry.intervalLabel,
        actionSummary: entry.actionSummary,
        finalSplitS: metricsSecondsValue(entry.splitMs),
        shotmlSplitS: metricsSecondsValue(entry.shotmlSplitMs),
        runTotalS,
        referenceRunS,
        confidencePct: metricsPercentValue(entry.confidence),
        category,
        referenceDeltaS: runTotalS === null || referenceRunS === null
          ? null
          : Number((runTotalS - referenceRunS).toFixed(3)),
      };
    });
    const buildLine = (key, label, color) => ({
      key,
      label,
      color,
      points: graphPoints
        .filter((point) => point[key] !== null && point[key] !== undefined)
        .map((point) => ({ shotNumber: point.shotNumber, label: point.label, value: point[key] })),
    });
    const largestGapPoint = graphPoints.reduce((largest, point) => {
      if (!largest) return point;
      return Number(point.finalSplitS || 0) > Number(largest.finalSplitS || 0) ? point : largest;
    }, null);
    const intervalBars = graphPoints
      .filter((point) => point.shotNumber > 1 && point.finalSplitS !== null && point.finalSplitS !== undefined)
      .map((point) => ({
        key: point.pairLabel,
        label: point.pairLabel,
        shortLabel: point.pairLabel,
        value: point.finalSplitS,
        category: point.category,
        detail: point.intervalLabel || point.category.label,
        highlight: largestGapPoint?.shotNumber === point.shotNumber,
      }));
    const intervalMedian = metricsMedian(intervalBars.map((bar) => bar.value));
    const stageSegments = buildMetricsStageSegments(graphPoints).map((segment, index) => ({
      key: segment.key || `segment_${index + 1}`,
      label: segment.label,
      shortLabel: segment.shortLabel,
      value: segment.value,
      category: segment.category,
      highlight: false,
    }));
    const largestStageSegment = stageSegments.reduce((largest, segment) => {
      if (!largest) return segment;
      return Number(segment.value || 0) > Number(largest.value || 0) ? segment : largest;
    }, null);
    stageSegments.forEach((segment) => {
      if (!largestStageSegment) return;
      segment.highlight = segment.key === largestStageSegment.key;
    });
    const finalPoint = graphPoints[graphPoints.length - 1] || null;
    const largestDeltaPoint = graphPoints
      .filter((point) => point.referenceDeltaS !== null && point.referenceDeltaS !== undefined)
      .reduce((largest, point) => {
        if (!largest) return point;
        return Math.abs(Number(point.referenceDeltaS || 0)) > Math.abs(Number(largest.referenceDeltaS || 0)) ? point : largest;
      }, null);
    const shootingTotalS = stageSegments
      .filter((segment) => segment.category.id === "shooting_interval")
      .reduce((total, segment) => total + Number(segment.value || 0), 0);
    const nonShootingTotalS = stageSegments
      .filter((segment) => segment.category.id !== "shooting_interval")
      .reduce((total, segment) => total + Number(segment.value || 0), 0);

    const graphs = [
      {
        id: "shot_interval_timeline",
        type: "timeline",
        title: "Shot / Interval Timeline",
        subtitle: "Start signal to last shot, with dead time made obvious",
        unit: "s",
        points: graphPoints.map((point) => ({
          ...point,
          value: point.runTotalS,
          highlight: largestGapPoint?.shotNumber === point.shotNumber,
        })),
        summary: [
          { label: "Start→1", value: metricsGraphValueLabel(graphPoints[0]?.runTotalS ?? null, "s"), color: graphPoints[0]?.category?.color },
          { label: `Largest ${largestGapPoint?.pairLabel || "gap"}`, value: metricsGraphValueLabel(largestGapPoint?.finalSplitS ?? null, "s"), color: largestGapPoint?.category?.color },
          { label: "Last shot", value: metricsGraphValueLabel(finalPoint?.runTotalS ?? null, "s"), color: finalPoint?.category?.color },
        ],
        forceZeroMin: true,
      },
      {
        id: "split_interval_bars",
        type: "bars",
        title: "Split / Interval Bar Chart",
        subtitle: "Each shot pair shows where time was lost",
        unit: "s",
        bars: intervalBars,
        summary: [
          { label: "Median", value: metricsGraphValueLabel(intervalMedian, "s"), color: "#39d06f" },
          { label: `Largest ${largestGapPoint?.pairLabel || "gap"}`, value: metricsGraphValueLabel(largestGapPoint?.finalSplitS ?? null, "s"), color: largestGapPoint?.category?.color },
          { label: "Cadence ref", value: metricsGraphValueLabel(metricsSecondsValue(cadenceBaselineMs), "s"), color: "#4ea7ff" },
        ],
      },
      {
        id: "run_comparison_overlay",
        type: "lines",
        title: "Run Comparison Overlay",
        subtitle: "Current cumulative time vs the ShotML reference baseline",
        unit: "s",
        lines: [
          buildLine("runTotalS", "Current", "#ff7b22"),
          buildLine("referenceRunS", "ShotML Reference", "#4ea7ff"),
        ],
        summary: [
          { label: "Current", value: metricsGraphValueLabel(finalPoint?.runTotalS ?? null, "s"), color: "#ff7b22" },
          { label: "Reference", value: metricsGraphValueLabel(finalPoint?.referenceRunS ?? null, "s"), color: "#4ea7ff" },
          { label: "Final delta", value: metricsSignedValueLabel(finalPoint?.referenceDeltaS ?? null, "s"), color: largestDeltaPoint?.referenceDeltaS !== null && largestDeltaPoint?.referenceDeltaS !== undefined ? (largestDeltaPoint.referenceDeltaS > 0 ? "#ef4444" : "#39d06f") : "#a855f7" },
        ],
        forceZeroMin: true,
      },
      {
        id: "stage_segment_breakdown",
        type: "bars",
        title: "Stage Segment Breakdown",
        subtitle: "Grouped into first shot, shooting, movement, reload, and dead time",
        unit: "s",
        bars: stageSegments,
        summary: [
          { label: `Largest ${largestStageSegment?.shortLabel || "segment"}`, value: metricsGraphValueLabel(largestStageSegment?.value ?? null, "s"), color: largestStageSegment?.category?.color },
          { label: "Shooting", value: metricsGraphValueLabel(Number(shootingTotalS.toFixed(3)), "s"), color: metricsCategoryDefinition("shooting_interval").color },
          { label: "Non-shooting", value: metricsGraphValueLabel(Number(nonShootingTotalS.toFixed(3)), "s"), color: metricsCategoryDefinition("transition").color },
        ],
      },
    ];
    return graphs
      .map((graph) => ({
        ...graph,
        lines: Array.isArray(graph.lines)
          ? graph.lines.filter((line) => line.points.length > 0)
          : [],
      }))
      .filter((graph) => {
        if (graph.type === "timeline") return Array.isArray(graph.points) && graph.points.length > 0;
        if (graph.type === "bars") return Array.isArray(graph.bars) && graph.bars.length > 0;
        return graph.lines.length > 0;
      });
  }

  function metricsGraphValueLabel(value, unit) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
    const numeric = Number(value);
    if (unit === "%") return `${numeric.toFixed(1)}%`;
    return `${numeric.toFixed(3)}s`;
  }

  function metricsSignedValueLabel(value, unit) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
    const numeric = Number(value);
    const prefix = numeric > 0 ? "+" : "";
    if (unit === "%") return `${prefix}${numeric.toFixed(1)}%`;
    return `${prefix}${numeric.toFixed(3)}s`;
  }

  function metricsSignedMillisecondsText(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
    const numeric = Number(value);
    const prefix = numeric > 0 ? "+" : "";
    return `${prefix}${splitSeconds(numeric)}`;
  }

  function createSvgNode(tagName) {
    return documentObject.createElementNS("http://www.w3.org/2000/svg", tagName);
  }

  function metricsGraphRange(lines, unit, { forceZeroMin = false } = {}) {
    const values = lines.flatMap((line) => line.points.map((point) => point.value)).filter((value) => Number.isFinite(value));
    if (values.length === 0) return null;
    let min = Math.min(...values);
    let max = Math.max(...values);
    if (unit === "%") {
      min = Math.min(0, min);
      max = Math.max(100, max);
    }
    if (forceZeroMin || (unit !== "%" && values.every((value) => value >= 0))) {
      min = Math.min(0, min);
    }
    if (min === max) {
      const padding = min === 0 ? 1 : Math.max(0.5, Math.abs(min) * 0.15);
      min -= padding;
      max += padding;
    }
    return { min, max };
  }

  function metricsGraphSummaryItems(graph) {
    if (Array.isArray(graph.summary) && graph.summary.length > 0) return graph.summary;
    return (graph.lines || []).map((line) => {
      const lastPoint = line.points[line.points.length - 1] || null;
      return {
        label: line.label,
        value: metricsGraphValueLabel(lastPoint?.value ?? null, graph.unit),
        color: line.color,
      };
    });
  }

  function appendMetricsSvgTitle(node, text) {
    if (!node || !text) return;
    const title = createSvgNode("title");
    title.textContent = text;
    node.appendChild(title);
  }

  function createMetricsGraphCanvas({ compact = true } = {}) {
    const svg = createSvgNode("svg");
    svg.classList.add("metrics-graph-svg");
    svg.setAttribute("viewBox", compact ? "0 0 260 132" : "0 0 320 150");
    svg.setAttribute("preserveAspectRatio", "none");
    const viewWidth = compact ? 260 : 320;
    const viewHeight = compact ? 132 : 150;
    const padding = { left: 12, right: 10, top: 10, bottom: 22 };
    const plotWidth = viewWidth - padding.left - padding.right;
    const plotHeight = viewHeight - padding.top - padding.bottom;
    return { svg, viewWidth, viewHeight, padding, plotWidth, plotHeight };
  }

  function shouldRenderMetricsAxisLabel(index, count, compact, highlighted = false) {
    if (highlighted || count <= 1 || index === 0 || index === count - 1) return true;
    const step = Math.ceil(count / (compact ? 4 : 6));
    return step <= 1 ? true : index % step === 0;
  }

  function renderMetricsLineGraphSvg(graph, { compact = true } = {}) {
    const range = metricsGraphRange(graph.lines || [], graph.unit, { forceZeroMin: graph.forceZeroMin !== false });
    if (!range) return null;
    const { svg, viewWidth, viewHeight, padding, plotWidth, plotHeight } = createMetricsGraphCanvas({ compact });
    const pointCount = Math.max(...graph.lines.map((line) => line.points.length));
    const xFor = (index) => padding.left + (pointCount <= 1 ? plotWidth / 2 : (index / (pointCount - 1)) * plotWidth);
    const yFor = (value) => padding.top + ((range.max - value) / Math.max(0.0001, range.max - range.min)) * plotHeight;

    [0, 0.5, 1].forEach((ratio) => {
      const y = padding.top + (plotHeight * ratio);
      const gridLine = createSvgNode("line");
      gridLine.setAttribute("x1", String(padding.left));
      gridLine.setAttribute("x2", String(viewWidth - padding.right));
      gridLine.setAttribute("y1", String(y));
      gridLine.setAttribute("y2", String(y));
      gridLine.setAttribute("class", "metrics-graph-grid-line");
      svg.appendChild(gridLine);
    });

    graph.lines.forEach((line) => {
      const polyline = createSvgNode("polyline");
      polyline.setAttribute(
        "points",
        line.points.map((point, index) => `${xFor(index)},${yFor(point.value)}`).join(" "),
      );
      polyline.setAttribute("fill", "none");
      polyline.setAttribute("stroke", line.color);
      polyline.setAttribute("stroke-width", compact ? "2" : "2.5");
      polyline.setAttribute("stroke-linejoin", "round");
      polyline.setAttribute("stroke-linecap", "round");
      polyline.setAttribute("class", "metrics-graph-line");
      appendMetricsSvgTitle(polyline, `${line.label}: ${line.points.map((point) => `Shot ${point.shotNumber} ${metricsGraphValueLabel(point.value, graph.unit)}`).join(" • ")}`);
      svg.appendChild(polyline);
      line.points.forEach((point, index) => {
        const dot = createSvgNode("circle");
        dot.setAttribute("cx", String(xFor(index)));
        dot.setAttribute("cy", String(yFor(point.value)));
        dot.setAttribute("r", compact ? "3" : "3.5");
        dot.setAttribute("fill", line.color);
        dot.setAttribute("class", "metrics-graph-dot");
        appendMetricsSvgTitle(dot, `${line.label} • Shot ${point.shotNumber}: ${metricsGraphValueLabel(point.value, graph.unit)}`);
        svg.appendChild(dot);
      });
    });

    const firstLabel = graph.axisStartLabel || (graph.lines[0]?.points[0]?.shotNumber !== undefined ? `Shot ${graph.lines[0].points[0].shotNumber}` : "");
    const lastPoint = graph.lines[0]?.points[graph.lines[0].points.length - 1] || null;
    const lastLabel = graph.axisEndLabel || (lastPoint?.shotNumber !== undefined ? `Shot ${lastPoint.shotNumber}` : "");
    if (firstLabel) {
      const firstText = createSvgNode("text");
      firstText.setAttribute("x", String(padding.left));
      firstText.setAttribute("y", String(viewHeight - 6));
      firstText.setAttribute("text-anchor", "start");
      firstText.setAttribute("class", "metrics-graph-axis-label");
      firstText.textContent = firstLabel;
      svg.appendChild(firstText);
    }
    if (lastLabel) {
      const lastText = createSvgNode("text");
      lastText.setAttribute("x", String(viewWidth - padding.right));
      lastText.setAttribute("y", String(viewHeight - 6));
      lastText.setAttribute("text-anchor", "end");
      lastText.setAttribute("class", "metrics-graph-axis-label");
      lastText.textContent = lastLabel;
      svg.appendChild(lastText);
    }
    return svg;
  }

  function renderMetricsTimelineGraphSvg(graph, { compact = true } = {}) {
    const points = (graph.points || []).filter((point) => point.value !== null && point.value !== undefined);
    if (points.length === 0) return null;
    const { svg, viewWidth, viewHeight, padding, plotWidth, plotHeight } = createMetricsGraphCanvas({ compact });
    const totalValue = Math.max(...points.map((point) => Number(point.value || 0)), 0.001);
    const baselineY = padding.top + (plotHeight / 2);
    const xForValue = (value) => padding.left + ((Number(value || 0) / totalValue) * plotWidth);

    const baseline = createSvgNode("line");
    baseline.setAttribute("x1", String(padding.left));
    baseline.setAttribute("x2", String(viewWidth - padding.right));
    baseline.setAttribute("y1", String(baselineY));
    baseline.setAttribute("y2", String(baselineY));
    baseline.setAttribute("class", "metrics-graph-baseline");
    svg.appendChild(baseline);

    const startDot = createSvgNode("circle");
    startDot.setAttribute("cx", String(padding.left));
    startDot.setAttribute("cy", String(baselineY));
    startDot.setAttribute("r", compact ? "2.5" : "3");
    startDot.setAttribute("fill", "#f8fafc");
    startDot.setAttribute("class", "metrics-graph-timeline-start");
    appendMetricsSvgTitle(startDot, "Start 0.000s");
    svg.appendChild(startDot);

    let previousX = padding.left;
    points.forEach((point, index) => {
      const x = xForValue(point.value);
      const segment = createSvgNode("line");
      segment.setAttribute("x1", String(previousX));
      segment.setAttribute("x2", String(x));
      segment.setAttribute("y1", String(baselineY));
      segment.setAttribute("y2", String(baselineY));
      segment.setAttribute("stroke", point.category.color);
      segment.setAttribute("stroke-width", point.highlight ? (compact ? "5" : "6") : (compact ? "4" : "4.5"));
      segment.setAttribute("class", "metrics-graph-timeline-segment");
      appendMetricsSvgTitle(segment, `${point.pairLabel} • ${metricsGraphValueLabel(point.finalSplitS, graph.unit)} • ${point.category.label}`);
      svg.appendChild(segment);

      const dot = createSvgNode("circle");
      dot.setAttribute("cx", String(x));
      dot.setAttribute("cy", String(baselineY));
      dot.setAttribute("r", point.highlight ? (compact ? "4" : "4.5") : (compact ? "3.2" : "3.6"));
      dot.setAttribute("fill", point.category.color);
      dot.setAttribute("class", "metrics-graph-dot");
      appendMetricsSvgTitle(dot, `Shot ${point.shotNumber} • ${metricsGraphValueLabel(point.value, graph.unit)} • ${point.category.label}`);
      svg.appendChild(dot);

      if (!compact && point.highlight) {
        const label = createSvgNode("text");
        label.setAttribute("x", String((previousX + x) / 2));
        label.setAttribute("y", String(baselineY - 10));
        label.setAttribute("text-anchor", "middle");
        label.setAttribute("class", "metrics-graph-highlight-label");
        label.textContent = `${point.pairLabel} ${metricsGraphValueLabel(point.finalSplitS, graph.unit)}`;
        svg.appendChild(label);
      }

      if (!compact && shouldRenderMetricsAxisLabel(index, points.length, compact, point.highlight)) {
        const axis = createSvgNode("text");
        axis.setAttribute("x", String(x));
        axis.setAttribute("y", String(baselineY + 16));
        axis.setAttribute("text-anchor", "middle");
        axis.setAttribute("class", "metrics-graph-axis-label");
        axis.textContent = `S${point.shotNumber}`;
        svg.appendChild(axis);
      }

      previousX = x;
    });

    const startText = createSvgNode("text");
    startText.setAttribute("x", String(padding.left));
    startText.setAttribute("y", String(viewHeight - 6));
    startText.setAttribute("text-anchor", "start");
    startText.setAttribute("class", "metrics-graph-axis-label");
    startText.textContent = "Start 0.000s";
    svg.appendChild(startText);

    const finalPoint = points[points.length - 1] || null;
    if (finalPoint) {
      const endText = createSvgNode("text");
      endText.setAttribute("x", String(viewWidth - padding.right));
      endText.setAttribute("y", String(viewHeight - 6));
      endText.setAttribute("text-anchor", "end");
      endText.setAttribute("class", "metrics-graph-axis-label");
      endText.textContent = `Shot ${finalPoint.shotNumber} ${metricsGraphValueLabel(finalPoint.value, graph.unit)}`;
      svg.appendChild(endText);
    }
    return svg;
  }

  function renderMetricsBarGraphSvg(graph, { compact = true } = {}) {
    const bars = (graph.bars || []).filter((bar) => bar.value !== null && bar.value !== undefined);
    if (bars.length === 0) return null;
    const { svg, viewWidth, viewHeight, padding, plotWidth, plotHeight } = createMetricsGraphCanvas({ compact });
    const maxValue = Math.max(...bars.map((bar) => Number(bar.value || 0)), 0.001);
    const yFor = (value) => padding.top + ((maxValue - Number(value || 0)) / Math.max(0.0001, maxValue)) * plotHeight;
    const columnWidth = plotWidth / Math.max(1, bars.length);
    const barWidth = Math.max(6, columnWidth * (compact ? 0.56 : 0.64));

    [0, 0.5, 1].forEach((ratio) => {
      const y = padding.top + (plotHeight * ratio);
      const gridLine = createSvgNode("line");
      gridLine.setAttribute("x1", String(padding.left));
      gridLine.setAttribute("x2", String(viewWidth - padding.right));
      gridLine.setAttribute("y1", String(y));
      gridLine.setAttribute("y2", String(y));
      gridLine.setAttribute("class", "metrics-graph-grid-line");
      svg.appendChild(gridLine);
    });

    const baseline = createSvgNode("line");
    baseline.setAttribute("x1", String(padding.left));
    baseline.setAttribute("x2", String(viewWidth - padding.right));
    baseline.setAttribute("y1", String(padding.top + plotHeight));
    baseline.setAttribute("y2", String(padding.top + plotHeight));
    baseline.setAttribute("class", "metrics-graph-baseline");
    svg.appendChild(baseline);

    bars.forEach((bar, index) => {
      const x = padding.left + (index * columnWidth) + ((columnWidth - barWidth) / 2);
      const y = yFor(bar.value);
      const rect = createSvgNode("rect");
      rect.setAttribute("x", String(x));
      rect.setAttribute("y", String(y));
      rect.setAttribute("width", String(barWidth));
      rect.setAttribute("height", String(Math.max(1, (padding.top + plotHeight) - y)));
      rect.setAttribute("fill", bar.category.color);
      rect.setAttribute("class", `metrics-graph-bar${bar.highlight ? " highlight" : ""}`);
      appendMetricsSvgTitle(rect, `${bar.label}: ${metricsGraphValueLabel(bar.value, graph.unit)} • ${bar.category.label}`);
      svg.appendChild(rect);

      if (bar.highlight || (!compact && bars.length <= 8)) {
        const valueText = createSvgNode("text");
        valueText.setAttribute("x", String(x + (barWidth / 2)));
        valueText.setAttribute("y", String(Math.max(padding.top + 9, y - 4)));
        valueText.setAttribute("text-anchor", "middle");
        valueText.setAttribute("class", "metrics-graph-bar-value");
        valueText.textContent = metricsGraphValueLabel(bar.value, graph.unit);
        svg.appendChild(valueText);
      }

      if (shouldRenderMetricsAxisLabel(index, bars.length, compact, bar.highlight)) {
        const axis = createSvgNode("text");
        axis.setAttribute("x", String(x + (barWidth / 2)));
        axis.setAttribute("y", String(viewHeight - 6));
        axis.setAttribute("text-anchor", "middle");
        axis.setAttribute("class", "metrics-graph-axis-label");
        axis.textContent = bar.shortLabel || bar.label;
        svg.appendChild(axis);
      }
    });

    return svg;
  }

  function renderMetricsGraphSvg(graph, { compact = true } = {}) {
    if (graph.type === "timeline") return renderMetricsTimelineGraphSvg(graph, { compact });
    if (graph.type === "bars") return renderMetricsBarGraphSvg(graph, { compact });
    return renderMetricsLineGraphSvg(graph, { compact });
  }

  function renderMetricsGraphCard(graph, { compact = true } = {}) {
    const card = documentObject.createElement("article");
    card.className = "metric-card metrics-graph-card";
    if (!compact) card.classList.add("metrics-graph-card-wide");
    const header = documentObject.createElement("div");
    header.className = "metrics-graph-header";
    const title = documentObject.createElement("strong");
    title.textContent = graph.title;
    const subtitle = documentObject.createElement("span");
    subtitle.className = "hint";
    subtitle.textContent = graph.subtitle;
    header.append(title, subtitle);
    card.appendChild(header);

    const summary = documentObject.createElement("div");
    summary.className = "metrics-graph-summary";
    metricsGraphSummaryItems(graph).forEach((item) => {
      const chip = documentObject.createElement("span");
      chip.className = "metrics-graph-chip";
      chip.style.setProperty("--metrics-graph-chip-color", item.color || "var(--accent)");
      chip.textContent = [item.label, item.value].filter(Boolean).join(" ").trim();
      summary.appendChild(chip);
    });
    card.appendChild(summary);

    const svg = renderMetricsGraphSvg(graph, { compact });
    if (svg) card.appendChild(svg);
    return card;
  }

  function renderMetricsGraphs(container, graphs, { compact = true } = {}) {
    if (!(container instanceof HTMLElement)) return;
    container.innerHTML = "";
    if (graphs.length === 0) {
      const empty = documentObject.createElement("p");
      empty.className = "hint metrics-graph-empty";
      empty.textContent = "Graphs appear once the run has timing rows to chart.";
      container.appendChild(empty);
      return;
    }
    graphs.forEach((graph) => container.appendChild(renderMetricsGraphCard(graph, { compact })));
  }

  function isMetricsSectionExpanded(sectionId) {
    return metricsSectionExpansion().get(sectionId) !== false;
  }

  function setMetricsSectionExpanded(sectionId, expanded) {
    metricsSectionExpansion().set(sectionId, Boolean(expanded));
  }

  function renderMetricsSections() {
    documentObject.querySelectorAll("[data-metrics-section]").forEach((section) => {
      if (!(section instanceof HTMLElement)) return;
      const sectionId = section.dataset.metricsSection || "";
      const expanded = isMetricsSectionExpanded(sectionId);
      section.classList.toggle("collapsed", !expanded);
      ensureSectionToggle(section, expanded, () => {
        setMetricsSectionExpanded(sectionId, !expanded);
        renderMetricsSections();
      });
    });
  }

  function buildMetricsGraphCsvSections(rows = buildMetricsRows()) {
    return buildMetricsGraphSeries(rows).map((graph) => {
      if (graph.type === "timeline") {
        return {
          name: `graph_${graph.id}`,
          headers: ["shot_number", "shot_label", "pair_label", "cumulative_s", "interval_s", "category_id", "category_label", "interval_label", "actions"],
          rows: (graph.points || []).map((point) => [
            point.shotNumber ?? "",
            point.label || "",
            point.pairLabel || "",
            point.value ?? "",
            point.finalSplitS ?? "",
            point.category?.id || "",
            point.category?.label || "",
            point.intervalLabel || "",
            point.actionSummary || "",
          ]),
        };
      }
      if (graph.type === "bars") {
        return {
          name: `graph_${graph.id}`,
          headers: ["order", "label", "short_label", "value_s", "category_id", "category_label"],
          rows: (graph.bars || []).map((bar, index) => [
            index + 1,
            bar.label || "",
            bar.shortLabel || "",
            bar.value ?? "",
            bar.category?.id || "",
            bar.category?.label || "",
          ]),
        };
      }
      const headers = ["shot_number", "shot_label", ...graph.lines.map((line) => line.key)];
      const recordByShotNumber = new Map();
      graph.lines.forEach((line) => {
        line.points.forEach((point) => {
          const existing = recordByShotNumber.get(point.shotNumber) || { shot_number: point.shotNumber, shot_label: point.label };
          existing[line.key] = point.value;
          recordByShotNumber.set(point.shotNumber, existing);
        });
      });
      const sectionRows = [...recordByShotNumber.values()]
        .sort((left, right) => Number(left.shot_number || 0) - Number(right.shot_number || 0))
        .map((record) => headers.map((header) => record[header] ?? ""));
      return {
        name: `graph_${graph.id}`,
        headers,
        rows: sectionRows.length > 0 ? sectionRows : [["", "", ...graph.lines.map(() => "")]],
      };
    });
  }

  function metricsScoringDetailRows(summary) {
    const imported = summary.imported_stage || {};
    const shortPenaltyLabels = {
      procedural_errors: "PE",
      failures_to_do_right: "FTDR",
      finger_pe: "FPE",
      flagrant_penalties: "FP",
      non_threats: "NS",
      manual_misses: "M",
    };
    const penaltyFieldRows = (summary.penalty_fields || []).map((field) => {
      const count = Number(field.count || 0);
      const value = Number(field.value || 0);
      const suffix = field.unit === "seconds" ? "s" : " pts";
      return [
        shortPenaltyLabels[field.id] || field.label || field.id,
        `${formatNumber(count, 2)} x ${formatNumber(value, 2)}${suffix}`,
      ];
    });
    const importedRows = [
      ["Stage #", imported.stage_number !== null && imported.stage_number !== undefined ? String(imported.stage_number) : ""],
      ["Competitor", imported.competitor_name || ""],
      ["Place", imported.competitor_place !== null && imported.competitor_place !== undefined ? String(imported.competitor_place) : ""],
    ];
    return [
      ...importedRows,
      ["Ruleset", summary.ruleset_name || ""],
      ["Sport", summary.sport || ""],
      ["Mode", summary.mode || ""],
      [summary.display_label || "Result", summary.display_value || ""],
      ["Raw Time", summary.raw_seconds !== null && summary.raw_seconds !== undefined ? `${formatNumber(summary.raw_seconds, 2)}s` : ""],
      ["Official Raw", summary.official_raw_seconds !== null && summary.official_raw_seconds !== undefined ? `${formatNumber(summary.official_raw_seconds, 2)}s` : ""],
      ["Raw Delta", summary.raw_delta_seconds !== null && summary.raw_delta_seconds !== undefined ? `${formatNumber(summary.raw_delta_seconds, 2)}s` : ""],
      ["Final Time", summary.final_time !== null && summary.final_time !== undefined ? `${formatNumber(summary.final_time, 2)}s` : ""],
      ["Official Final", summary.official_final_time !== null && summary.official_final_time !== undefined ? `${formatNumber(summary.official_final_time, 2)}s` : ""],
      ["Final Delta", summary.final_delta_seconds !== null && summary.final_delta_seconds !== undefined ? `${formatNumber(summary.final_delta_seconds, 2)}s` : ""],
      ["Shot Points", formatNumber(summary.shot_points, 2)],
      ["Shot Penalties", formatNumber(summary.shot_penalties, 2)],
      ["Field Penalties", formatNumber(summary.field_penalties, 2)],
      [summary.penalty_label || "Penalties", formatNumber(summary.total_penalties, 2)],
      ["Hit Factor", summary.hit_factor !== null && summary.hit_factor !== undefined ? formatNumber(summary.hit_factor, 2) : ""],
      ...penaltyFieldRows,
    ];
  }

  function renderMetricsPanel() {
    const summaryGrid = $("metrics-summary-grid");
    const trendList = $("metrics-trend-list");
    const scoreStatus = $("metrics-score-status");
    if (!summaryGrid || !trendList || !scoreStatus) return;
    const state = currentState();
    const scoringSummary = state.metrics?.scoring_summary || state.scoring_summary || {};
    const rows = buildMetricsRows();
    const graphs = buildMetricsGraphSeries(rows);

    const summaryCards = [
      ["Draw", splitSeconds(state.metrics?.draw_ms), "First-shot timing"],
      ["Raw", splitSeconds(state.metrics?.raw_time_ms ?? state.metrics?.stage_time_ms), "Beep to final shot"],
      ["Shots", String(state.metrics?.total_shots || 0), "Current timeline shots"],
      ["Avg Split", splitSeconds(state.metrics?.average_split_ms), "Average split"],
      ["Beep", splitSeconds(state.metrics?.beep_ms), "Start marker"],
      [scoringSummary.display_label || "Result", scoringSummary.display_value || "--", scoringSummary.sport || "Scoring summary"],
      ["Shot Points", formatNumber(scoringSummary.shot_points, 2), "Raw score total"],
      ["Penalties", formatNumber(scoringSummary.total_penalties, 2), scoringSummary.penalty_label || "Penalty summary"],
    ];
    summaryGrid.innerHTML = "";
    summaryCards.forEach(([label, value, caption]) => {
      const card = documentObject.createElement("article");
      card.className = "metric-card";
      const eyebrow = documentObject.createElement("small");
      eyebrow.textContent = label;
      const strong = documentObject.createElement("strong");
      strong.textContent = value;
      const hint = documentObject.createElement("span");
      hint.className = "hint";
      hint.textContent = caption;
      card.append(eyebrow, strong, hint);
      summaryGrid.appendChild(card);
    });

    withPreservedScrollState([trendList], () => renderMetricsTrendTable(trendList));

    const summary = scoringSummary;
    const imported = summary.imported_stage || {};
    scoreStatus.dataset.importedSource = imported.source_name || "";
    scoreStatus.dataset.importedStage = imported.stage_number ?? "";
    scoreStatus.dataset.importedCompetitor = imported.competitor_name || "";
    scoreStatus.dataset.importedPlace = imported.competitor_place ?? "";
    scoreStatus.textContent = summary.enabled
      ? `${summary.display_label || "Result"} ${summary.display_value || "--"}`
      : "Scoring disabled.";
    const details = metricsScoringDetailRows(summary);
    renderDetailsList("metrics-score-summary", details);
    renderMetricsGraphs($("metrics-graph-list"), graphs, { compact: true });
    renderMetricsGraphs($("metrics-workbench-graphs"), graphs, { compact: false });
    renderMetricsSections();
    renderMetricsTable($("metrics-workbench-table"));
  }

  function metricsFileStem() {
    const state = currentState();
    const raw = state?.project?.name || fileName(state?.project?.primary_video?.path || "") || "splitshot";
    return raw
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "splitshot";
  }

  function csvEscape(value) {
    const text = value === null || value === undefined ? "" : String(value);
    return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  }

  function downloadTextFile(filename, text, mimeType = "text/plain") {
    const blob = new Blob([text], { type: `${mimeType};charset=utf-8` });
    const url = windowObject.URL.createObjectURL(blob);
    const link = documentObject.createElement("a");
    link.href = url;
    link.download = filename;
    documentObject.body.appendChild(link);
    link.click();
    link.remove();
    windowObject.setTimeout(() => windowObject.URL.revokeObjectURL(url), 0);
  }

  function buildMetricsCsv() {
    const state = currentState();
    const summary = state.scoring_summary || {};
    const rows = buildMetricsRows();
    const imported = summary.imported_stage || {};
    const comparisonShooters = Array.isArray(state?.practiscore_options?.competitors)
      ? state.practiscore_options.competitors
      : [];
    const penaltyFieldRows = (summary.penalty_fields || []).map((field) => [
      field.id || "",
      field.label || "",
      field.unit || "",
      field.count ?? "",
      field.value ?? "",
      (Number(field.count || 0) * Number(field.value || 0)) || "",
    ]);
    const sections = [
      {
        name: "run_summary",
        headers: [
          "project_name",
          "video_file",
          "shooter_name",
          "stage_number",
          "stage_name",
          "match_type",
          "ruleset",
          "sport",
          "competitor_place",
          "stage_place",
          "class_place",
          "result_label",
          "result_value",
          "raw_time_s",
          "raw_delta_s",
          "final_time_s",
          "final_delta_s",
          "shot_points",
          "shot_penalties",
          "field_penalties",
          "total_penalties",
          "hit_factor",
        ],
        rows: [[
          state.project?.name || "",
          fileName(state.project?.primary_video?.path || ""),
          imported.competitor_name || state.project?.scoring?.competitor_name || "",
          imported.stage_number ?? state.project?.scoring?.stage_number ?? "",
          imported.stage_name || "",
          imported.match_type || state?.practiscore_options?.detected_match_type || state.project?.scoring?.match_type || "",
          summary.ruleset || "",
          summary.sport || "",
          imported.competitor_place ?? state.project?.scoring?.competitor_place ?? "",
          imported.stage_place ?? "",
          imported.class_place ?? "",
          summary.display_label || "Result",
          summary.display_value || "",
          summary.raw_seconds ?? "",
          summary.raw_delta_seconds ?? "",
          summary.final_time ?? "",
          summary.final_delta_seconds ?? "",
          summary.shot_points ?? "",
          summary.shot_penalties ?? "",
          summary.field_penalties ?? "",
          summary.total_penalties ?? "",
          summary.hit_factor ?? "",
        ]],
      },
      {
        name: "comparison_context",
        headers: [
          "competitor",
          "class",
          "division",
          "overall_place",
          "class_place",
          "stage_place",
          "raw_time_s",
          "final_time_s",
          "points",
          "stage_points",
          "hit_factor",
          "delta_to_selected_s",
        ],
        rows: comparisonShooters.length > 0
          ? comparisonShooters.map((competitor) => [
            competitor.name || "",
            competitor.class || "",
            competitor.division || "",
            competitor.place ?? "",
            competitor.class_place ?? "",
            competitor.stage_place ?? "",
            competitor.raw_seconds ?? "",
            competitor.final_time ?? "",
            competitor.points ?? "",
            competitor.stage_points ?? "",
            competitor.hit_factor ?? "",
            "",
          ])
          : [["", "", "", "", "", "", "", "", "", "", "", ""]],
      },
      {
        name: "per_shot_metrics",
        headers: [
          "shot_number",
          "segment_label",
          "interval_label",
          "actions",
          "shotml_split_s",
          "adjustment_s",
          "absolute_s",
          "split_s",
          "run_s",
          "cumulative_s",
          "practiscore_raw_s",
          "raw_delta_s",
          "score_letter",
          "penalties",
          "shotml_confidence",
        ],
        rows: rows.map((entry) => [
          entry.shotNumber || "",
          entry.label || "",
          entry.intervalLabel || "",
          entry.actionSummary || "",
          entry.shotmlSplitMs === null || entry.shotmlSplitMs === undefined ? "" : precise(entry.shotmlSplitMs),
          entry.adjustmentMs === null || entry.adjustmentMs === undefined ? "" : precise(entry.adjustmentMs),
          entry.absoluteMs === null ? "" : precise(entry.absoluteMs),
          entry.splitMs === null || entry.splitMs === undefined ? "" : precise(entry.splitMs),
          entry.sequenceTotalMs === null || entry.sequenceTotalMs === undefined ? "" : precise(entry.sequenceTotalMs),
          entry.cumulativeMs === null || entry.cumulativeMs === undefined ? "" : precise(entry.cumulativeMs),
          entry.practiscoreMs === null || entry.practiscoreMs === undefined ? "" : precise(entry.practiscoreMs),
          entry.rawDeltaMs === null || entry.rawDeltaMs === undefined ? "" : precise(entry.rawDeltaMs),
          entry.scoreLetter || "",
          entry.penaltyText || "",
          entry.confidence ?? "",
        ]),
      },
      {
        name: "scoring_breakdown",
        headers: ["penalty_id", "label", "unit", "count", "value", "total"],
        rows: [
          ...penaltyFieldRows,
          ["shot_points", "Shot Points", "points", "", summary.shot_points ?? "", summary.shot_points ?? ""],
          ["shot_penalties", "Shot Penalties", "points", "", summary.shot_penalties ?? "", summary.shot_penalties ?? ""],
          ["field_penalties", "Field Penalties", "points", "", summary.field_penalties ?? "", summary.field_penalties ?? ""],
          ["total_penalties", summary.penalty_label || "Total Penalties", "points", "", summary.total_penalties ?? "", summary.total_penalties ?? ""],
        ],
      },
      ...buildMetricsGraphCsvSections(rows),
    ];

    const output = [];
    sections.forEach((section, index) => {
      output.push(csvEscape(`# ${section.name}`));
      output.push(section.headers.map(csvEscape).join(","));
      section.rows.forEach((row) => output.push(row.map(csvEscape).join(",")));
      if (index < sections.length - 1) output.push("");
    });
    return output.join("\n");
  }

  function buildMetricsText() {
    const state = currentState();
    const summary = state.scoring_summary || {};
    const rows = buildMetricsRows();
    const graphs = buildMetricsGraphSeries(rows);
    const segmentGraph = graphs.find((graph) => graph.id === "stage_segment_breakdown") || null;
    const comparisonGraph = graphs.find((graph) => graph.id === "run_comparison_overlay") || null;
    const lines = [
      state.project?.name || "Untitled Project",
      `Video: ${fileName(state.project?.primary_video?.path || "")}`,
      `${summary.display_label || "Result"}: ${summary.display_value || "--"}`,
      `Raw Time: ${summary.raw_seconds !== null && summary.raw_seconds !== undefined ? `${formatNumber(summary.raw_seconds, 2)}s` : "--"}`,
      `Shots: ${state.metrics?.total_shots || 0}`,
      "",
      "Split Timeline",
    ];
    rows.forEach((entry) => {
      const parts = [
        entry.label || (entry.shotNumber ? `Shot ${entry.shotNumber}` : "Entry"),
        entry.intervalLabel ? `Interval ${entry.intervalLabel}` : "",
        entry.absoluteMs === null ? "Absolute --.--" : `Absolute ${precise(entry.absoluteMs)}s`,
        entry.splitMs === null || entry.splitMs === undefined ? "Split --.--" : `Split ${splitSeconds(entry.splitMs)}`,
        entry.cumulativeMs === null || entry.cumulativeMs === undefined ? "Total --.--" : `Total ${splitSeconds(entry.cumulativeMs)}`,
      ];
      if (entry.actionSummary) parts.push(`Actions ${entry.actionSummary}`);
      if (entry.scoreLetter) parts.push(`Score ${entry.scoreLetter}`);
      if (entry.penaltyText) parts.push(entry.penaltyText);
      parts.push(`Adjustment ${signedSeconds(entry.adjustmentMs || 0)}`);
      if (entry.rawDeltaMs !== null && entry.rawDeltaMs !== undefined) parts.push(`PractiScore ${metricsPractiScoreLabel(entry)}`);
      if (entry.confidence !== null && entry.confidence !== undefined && entry.confidence !== "") parts.push(`ShotML ${formatConfidenceValue(entry.confidence)}`);
      lines.push(`- ${parts.join(" | ")}`);
    });
    if (segmentGraph?.bars?.length) {
      lines.push("", "Stage Segments");
      segmentGraph.bars.forEach((bar) => {
        lines.push(`- ${bar.label}: ${metricsGraphValueLabel(bar.value, segmentGraph.unit)} (${bar.category.label})`);
      });
    }
    if (comparisonGraph?.summary?.length) {
      lines.push("", comparisonGraph.title);
      comparisonGraph.summary.forEach((item) => {
        lines.push(`- ${item.label}: ${item.value}`);
      });
    }
    return lines.join("\n");
  }

  function exportMetrics(kind) {
    const state = currentState();
    if (!state?.project) return;
    const stem = metricsFileStem();
    if (kind === "csv") {
      downloadTextFile(`${stem}-metrics.csv`, buildMetricsCsv(), "text/csv");
      setStatus("Downloaded metrics CSV.");
      return;
    }
    downloadTextFile(`${stem}-metrics.txt`, buildMetricsText(), "text/plain");
    setStatus("Downloaded metrics summary.");
  }

  function setMetricsExpanded(expanded, { persistUiState = true } = {}) {
    return paneBase.setExpanded(expanded, { persistUiState });
  }

  return Object.freeze({
    buildMetricsRows,
    metricsPractiScoreLabel,
    renderMetricsTable,
    renderMetricsTrendTable,
    metricsSecondsValue,
    metricsPercentValue,
    metricsMedian,
    metricsCategoryDefinition,
    metricsIntervalText,
    metricsMeaningfulIntervalLabel,
    metricsCadenceBaselineMs,
    metricsIntervalClassification,
    metricsSegmentShortLabel,
    metricsStageSegmentLabel,
    buildMetricsStageSegments,
    metricsGraphLabel,
    buildMetricsGraphSeries,
    metricsGraphValueLabel,
    metricsSignedValueLabel,
    createSvgNode,
    metricsGraphRange,
    metricsGraphSummaryItems,
    appendMetricsSvgTitle,
    createMetricsGraphCanvas,
    shouldRenderMetricsAxisLabel,
    renderMetricsLineGraphSvg,
    renderMetricsTimelineGraphSvg,
    renderMetricsBarGraphSvg,
    renderMetricsGraphSvg,
    renderMetricsGraphCard,
    renderMetricsGraphs,
    isMetricsSectionExpanded,
    setMetricsSectionExpanded,
    renderMetricsSections,
    buildMetricsGraphCsvSections,
    metricsScoringDetailRows,
    renderMetricsPanel,
    metricsFileStem,
    csvEscape,
    downloadTextFile,
    buildMetricsCsv,
    buildMetricsText,
    exportMetrics,
    setMetricsExpanded,
  });
}
