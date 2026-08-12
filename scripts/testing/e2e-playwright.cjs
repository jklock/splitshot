const { chromium } = require('playwright');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const port = process.env.E2E_PORT || '8765';
const logDir = process.env.E2E_LOG_DIR || path.join(os.tmpdir(), 'splitshot-e2e-logs');
const artifactRoot = process.env.E2E_ARTIFACT_ROOT || logDir;
const primaryVideoPath = process.env.E2E_PRIMARY_VIDEO_PATH || process.env.E2E_VIDEO_PATH || '';
const secondaryVideoPath = process.env.E2E_SECONDARY_VIDEO_PATH || '';
const practiscorePath = process.env.E2E_PRACTISCORE_PATH || '';
const exportDir = process.env.E2E_EXPORT_DIR || path.join(artifactRoot, 'exports');
const canonicalExportFile = path.join(exportDir, 'e2e-export-test.mp4');
const baseUrl = `http://127.0.0.1:${port}`;
const artifacts = [];
const failures = [];
const timings = [];
const actionLedger = [];
const requestLedger = [];
const caseObservations = new Map();
const e2eScope = process.env.SPLITSHOT_E2E_SCOPE || '';
const stopAfterExport = e2eScope === 'export-proof';
const isReleaseProof = e2eScope === 'release-proof';

const THRESHOLDS = {
  tool_switch_settled_ms: 5000,
  profile_create_ms: 5000,
  profile_edit_ms: 5000,
  review_source_update_ms: 2000,
  export_badges_ms: 2000,
  source_commit_ms: 2000,
  trim_apply_ms: 30000,
  trim_clear_ms: 30000,
  queue_process_ms: 120000,
};

function fail(msg) {
  failures.push(msg);
  warn(msg);
}

function log(msg) {
  const line = `[E2E ${new Date().toISOString()}] ${msg}`;
  console.log(line);
  try { fs.appendFileSync(path.join(logDir, 'e2e.log'), line + '\n'); } catch {}
}

function warn(msg) {
  const line = `[E2E ${new Date().toISOString()}] WARN ${msg}`;
  console.warn(line);
  try { fs.appendFileSync(path.join(logDir, 'e2e.log'), line + '\n'); } catch {}
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function writeJson(filePath, payload) {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, JSON.stringify(payload, null, 2));
  artifacts.push(filePath);
}

function writeText(filePath, text) {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, String(text ?? ''), 'utf8');
  artifacts.push(filePath);
}

function passCases(caseIds, evidence, detail = '') {
  for (const id of caseIds) {
    caseObservations.set(id, {
      id,
      status: 'passed',
      evidence: Array.isArray(evidence) ? evidence : [evidence],
      detail,
    });
  }
}

function recordTiming(name, elapsedMs, thresholdMs) {
  const entry = {
    name,
    elapsed_ms: elapsedMs,
    threshold_ms: thresholdMs,
    passed: thresholdMs == null ? true : elapsedMs <= thresholdMs,
  };
  timings.push(entry);
  log(`timing ${name}: ${elapsedMs}ms${thresholdMs == null ? '' : ` (threshold ${thresholdMs}ms)`}`);
  if (!entry.passed) {
    fail(`timing threshold exceeded for ${name}: ${elapsedMs}ms > ${thresholdMs}ms`);
  }
  return entry;
}

async function measureStep(name, thresholdMs, action) {
  const start = Date.now();
  const result = await action();
  recordTiming(name, Date.now() - start, thresholdMs);
  return result;
}

async function screenshot(page, name) {
  try {
    const file = path.join(logDir, `screenshot-${name}.png`);
    await page.screenshot({ path: file, fullPage: true });
    const size = fs.statSync(file).size;
    log(`screenshot saved: ${name} (${(size / 1024).toFixed(1)} KB)`);
    artifacts.push(file);
  } catch (e) {
    warn(`screenshot failed: ${name} - ${e.message}`);
  }
}

async function dumpHtml(page, name) {
  try {
    const file = path.join(logDir, `page-${name}.html`);
    const html = await page.content();
    fs.writeFileSync(file, html);
    const size = fs.statSync(file).size;
    log(`page HTML saved: ${name} (${(size / 1024).toFixed(1)} KB)`);
    artifacts.push(file);
  } catch (e) {
    warn(`HTML dump failed: ${name} - ${e.message}`);
  }
}

async function waitForUiSettled(page, timeoutMs = 15000) {
  await page.waitForFunction(
    "() => document.getElementById('processing-bar')?.hidden !== false",
    null,
    { timeout: timeoutMs },
  ).catch(() => {});
  await page.waitForTimeout(150);
}

async function openTool(page, tool, screenshotName = '') {
  const startedAt = new Date().toISOString();
  await measureStep(`tool-switch:${tool}`, THRESHOLDS.tool_switch_settled_ms, async () => {
    await page.locator(`button[data-tool="${tool}"]`).click({ force: true, timeout: 30000 });
    await page.waitForFunction((targetTool) => activeTool === targetTool, tool, { timeout: 30000 });
    await page.waitForFunction(
      (targetTool) => document.querySelector(`[data-tool-pane="${targetTool}"]`)?.classList.contains('active'),
      tool,
      { timeout: 30000 },
    );
  });
  // Background media processing may legitimately continue after navigation. Keep it
  // out of the interaction-latency measurement, but still wait before capturing proof.
  await waitForUiSettled(page);
  actionLedger.push({ action: 'tool-switch', target: tool, count: 1, started_at: startedAt, status: 'passed' });
  if (screenshotName) await screenshot(page, screenshotName);
}

async function waitForDetectedShots(page, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  let lastShotCount = 0;
  while (Date.now() < deadline) {
    lastShotCount = await page.evaluate(() => state?.project?.analysis?.shots?.length || 0);
    if (lastShotCount > 0) return lastShotCount;
    await page.waitForTimeout(500);
  }
  return lastShotCount;
}

function validateMp4(exportFile) {
  const ffprobe = process.env.SPLITSHOT_PACKAGED_FFPROBE || 'ffprobe';
  const probe = execFileSync(
    ffprobe,
    ['-v', 'error', '-show_entries', 'format=format_name,duration,size', '-of', 'json', exportFile],
    { encoding: 'utf8', timeout: 60000 },
  );
  return JSON.parse(probe);
}

async function waitForStableExportFile(page, exportFile, timeoutMs = 120000) {
  const deadline = Date.now() + timeoutMs;
  let lastSize = -1;
  let stableReads = 0;
  while (Date.now() < deadline) {
    let stat = null;
    try {
      stat = fs.statSync(exportFile);
    } catch {}
    if (stat?.isFile() && stat.size > 1024) {
      if (stat.size === lastSize) stableReads += 1;
      else {
        lastSize = stat.size;
        stableReads = 0;
      }
      if (stableReads >= 2) {
        try {
          return { size: stat.size, probe: validateMp4(exportFile) };
        } catch {}
      }
    }
    await page.waitForTimeout(1000);
  }
  return null;
}

async function setInputValue(page, selector, value) {
  await page.locator(selector).first().evaluate(
    (element, nextValue) => {
      element.value = String(nextValue);
      element.dispatchEvent(new Event('input', { bubbles: true }));
      element.dispatchEvent(new Event('change', { bubbles: true }));
    },
    value,
  );
  actionLedger.push({ action: 'set-input', target: selector, count: 1, value: String(value), status: 'passed' });
}

async function setSelectValue(page, selector, value) {
  await page.locator(selector).first().evaluate(
    (element, nextValue) => {
      element.value = String(nextValue);
      element.dispatchEvent(new Event('change', { bubbles: true }));
    },
    value,
  );
  actionLedger.push({ action: 'select-option', target: selector, count: 1, value: String(value), status: 'passed' });
}

const TOOL_TO_SHARD = {
  project: 'project-practiscore',
  media: 'media',
  merge: 'compose',
  'trim-sync': 'trim',
  scoring: 'score',
  timing: 'splits-waveform',
  markers: 'markers',
  overlay: 'overlay',
  review: 'review',
  export: 'export',
  'intro-outro': 'intro-outro',
  queue: 'queue',
  metrics: 'metrics',
  shotml: 'shotml',
  settings: 'settings',
};

async function collectRuntimeInventory(page) {
  const manifestPath = process.env.E2E_RELEASE_MANIFEST
    || path.join(__dirname, '..', '..', 'tests', 'release_validation', 'manifest-v1.json');
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  const shardIds = new Set(manifest.shards.map((item) => item.id));
  const inventory = [];
  const seen = new Map();
  const tools = await page.locator('button[data-tool]').evaluateAll(
    (nodes) => nodes.map((node) => node.getAttribute('data-tool')).filter(Boolean),
  );
  for (const tool of tools) {
    await openTool(page, tool);
    await page.evaluate(() => {
      document.querySelectorAll('details').forEach((node) => { node.open = true; });
      document.querySelectorAll('[data-settings-section].collapsed, [data-shotml-section].collapsed')
        .forEach((node) => node.classList.remove('collapsed'));
    });
    await page.waitForTimeout(100);
    const discovered = await page.evaluate((activePane) => {
      const pane = document.querySelector(`[data-tool-pane="${activePane}"]`);
      if (!pane) return [];
      const preferred = [
        'data-tool', 'data-settings-section', 'data-shotml-section', 'data-shotml-setting',
        'data-text-box-field', 'data-popup-field', 'data-merge-source-field', 'data-stage-field',
        'data-intro-outro-field', 'data-field', 'data-boundary-kind', 'data-text-box-action',
        'data-media-section', 'data-summary-metric', 'data-metric-id', 'data-remove-box',
        'data-stage-id', 'data-popup-action', 'name',
      ];
      const identity = (node) => {
        if (node.id) return `id:${node.id}`;
        for (const attribute of preferred) {
          const value = node.getAttribute(attribute);
          if (value) return `${attribute}:${value}`;
        }
        const label = node.getAttribute('aria-label') || node.getAttribute('title')
          || node.getAttribute('placeholder') || node.textContent || '';
        const normalized = label.replace(/\s+/g, ' ').trim().slice(0, 160);
        return normalized ? `${node.tagName.toLowerCase()}:${normalized}` : '';
      };
      const visible = (node) => {
        const style = getComputedStyle(node);
        const rect = node.getBoundingClientRect();
        return style.display !== 'none' && style.visibility !== 'hidden'
          && rect.width > 0 && rect.height > 0;
      };
      const selectors = [
        'button', 'input:not([type="hidden"])', 'select', 'textarea', 'details', 'video',
        'label', 'h1', 'h2', 'h3', '[role="button"]', '[role="status"]', '[aria-label]',
        '[title]', '[placeholder]', '.hint', '.status', '.progress-label',
      ].join(',');
      return Array.from(pane.querySelectorAll(selectors))
        .filter((node) => node.namespaceURI !== 'http://www.w3.org/2000/svg'
          || node.getAttribute('role') === 'button'
          || node.hasAttribute('tabindex'))
        .map((node) => ({
        identity: identity(node),
        pane: activePane,
        tag: node.tagName.toLowerCase(),
        type: String(node.type || ''),
        visible: visible(node),
        hidden: !visible(node),
        enabled: !node.disabled,
        selected: Boolean(node.selected || node.checked || node.getAttribute('aria-selected') === 'true'),
        accessible_name: node.getAttribute('aria-label') || node.getAttribute('title') || '',
        text: String(node.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 240),
        value: 'value' in node ? String(node.value || '') : '',
        options: node instanceof HTMLSelectElement
          ? Array.from(node.options).map((option) => ({ value: option.value, text: option.textContent?.trim() || '' }))
          : [],
        })).filter((item) => item.identity);
    }, tool);
    for (const item of discovered) {
      const base = `${item.pane}|${item.identity}`;
      const occurrence = seen.get(base) || 0;
      seen.set(base, occurrence + 1);
      inventory.push({ ...item, occurrence, shard: TOOL_TO_SHARD[item.pane] || '' });
    }
  }
  const shellNodes = await page.evaluate(() => Array.from(
    document.querySelectorAll('button[data-tool], #processing-bar, #processing-status, #export-log-modal'),
  ).map((node) => ({
    identity: node.id ? `id:${node.id}` : `data-tool:${node.getAttribute('data-tool')}`,
    pane: 'shell',
    tag: node.tagName.toLowerCase(),
    type: String(node.type || ''),
    visible: getComputedStyle(node).display !== 'none' && !node.hidden,
    hidden: getComputedStyle(node).display === 'none' || node.hidden,
    enabled: !node.disabled,
    selected: Boolean(node.getAttribute('aria-selected') === 'true'),
    accessible_name: node.getAttribute('aria-label') || node.getAttribute('title') || '',
    text: String(node.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 240),
    value: '',
    options: [],
    occurrence: 0,
    shard: 'shell',
  })));
  inventory.push(...shellNodes);
  const unknown = inventory.filter((item) => !shardIds.has(item.shard));
  if (unknown.length) fail(`runtime inventory has ${unknown.length} unmapped identities`);
  const caseMap = inventory.map((item) => ({
    identity: item.identity,
    occurrence: item.occurrence,
    pane: item.pane,
    shard: item.shard,
    mapped: shardIds.has(item.shard),
  }));
  writeJson(path.join(artifactRoot, 'runtime-inventory.json'), {
    manifest_id: manifest.manifest_id,
    discovered: inventory.length,
    identities: inventory,
  });
  writeJson(path.join(artifactRoot, 'inventory-case-map.json'), {
    manifest_id: manifest.manifest_id,
    discovered: inventory.length,
    mapped: caseMap.filter((item) => item.mapped).length,
    gaps: caseMap.filter((item) => !item.mapped).length,
    mappings: caseMap,
  });
  return { discovered: inventory.length, mapped: caseMap.length - unknown.length, gaps: unknown.length };
}

async function alternateSelectValue(page, selector) {
  return page.locator(selector).first().evaluate(
    (select) => [...select.options].find((option) => option.value && option.value !== select.value)?.value || select.value,
  );
}

async function ensureMergeCardExpanded(card) {
  const body = card.locator('.merge-media-card-body').first();
  if (await body.evaluate((element) => Boolean(element?.hidden))) {
    await card.locator('button[aria-label*="PiP item controls"]').click({ force: true });
    await body.waitFor({ state: 'visible', timeout: 30000 });
  }
}

async function ensureTrimCardVisible(page, sourceId) {
  await openTool(page, 'trim-sync');
  const card = page.locator(`.trim-source-card[data-source-id="${sourceId}"]`).first();
  await card.waitFor({ state: 'visible', timeout: 30000 });
  return card;
}

async function queueAndProcessCurrentStage(page, artifactRoot, screenshotPrefix) {
  await openTool(page, 'queue', `${screenshotPrefix}-queue`);
  const activeStageId = await page.evaluate(() => String(state?.project?.active_stage_id || ''));
  if (!activeStageId) throw new Error('active stage id missing before queue processing');
  await page.locator(`.queue-membership-btn[data-stage-id="${activeStageId}"]`).click({ force: true });
  await waitForCondition(
    page,
    () => {
      const entry = (state?.project?.queue || [])[0];
      return Boolean(entry) && (entry.status === 'queued' || entry.status === 'stale');
    },
    null,
    30000,
  );
  await screenshot(page, `${screenshotPrefix}-queued`);
  const processResponsePromise = page.waitForResponse(
    (response) => response.url().endsWith('/api/project/queue/process') && response.request().method() === 'POST',
    { timeout: 180000 },
  );
  await page.locator('#queue-process-btn').click({ force: true });
  const processResponse = await processResponsePromise;
  const payload = await processResponse.json().catch(() => null);
  const queueEntries = Array.isArray(payload?.project?.queue) ? payload.project.queue : [];
  const outputPath = String(queueEntries[0]?.output_path || '');
  if (String(payload?.status || '').includes('Processed ')) {
    await waitForUiSettled(page, 30000);
  }
  await screenshot(page, `${screenshotPrefix}-processed`);
  if (!outputPath) {
    fail('queue processing completed without output_path');
    return null;
  }
  await page.waitForFunction(
    (expectedPath) => {
      const entries = state?.project?.queue || [];
      return entries.some((entry) => entry?.output_path === expectedPath);
    },
    outputPath,
    { timeout: 30000 },
  ).catch(() => {});
  const exportValidation = await waitForStableExportFile(page, outputPath, 180000);
  if (!exportValidation) {
    fail('queue output file did not stabilize as a valid MP4');
    return null;
  }
  ensureDir(path.dirname(canonicalExportFile));
  fs.copyFileSync(outputPath, canonicalExportFile);
  artifacts.push(canonicalExportFile);
  writeJson(path.join(artifactRoot, 'queue-process-response.json'), payload || {});
  artifacts.push(outputPath);
  writeJson(path.join(artifactRoot, 'export-metadata.json'), exportValidation);
  return outputPath;
}

async function waitForCondition(page, condition, arg, timeoutMs = 15000) {
  await page.waitForFunction(condition, arg, { timeout: timeoutMs });
}

async function assertNoHorizontalOverflow(page, label) {
  const result = await page.evaluate(
    () => {
      const inspector = document.querySelector('.inspector');
      const pane = document.querySelector(`[data-tool-pane="${activeTool}"]`);
      const paneRect = pane?.getBoundingClientRect?.() || { left: 0, right: 0 };
      const offenders = [];
      const elements = pane
        ? Array.from(pane.querySelectorAll('label, button, input, select, textarea, .review-source-status, .merge-source-trim-status'))
        : [];
      for (const element of elements) {
        const rect = element.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) continue;
        if (rect.right > paneRect.right + 1 || rect.left < paneRect.left - 1) {
          offenders.push({
            text: element.textContent?.trim?.() || element.getAttribute('aria-label') || element.id || element.className || '<unknown>',
            left: rect.left,
            right: rect.right,
            pane_left: paneRect.left,
            pane_right: paneRect.right,
          });
        }
      }
      return {
        active_tool: activeTool,
        inspector_client_width: inspector?.clientWidth || 0,
        inspector_scroll_width: inspector?.scrollWidth || 0,
        pane_client_width: pane?.clientWidth || 0,
        pane_scroll_width: pane?.scrollWidth || 0,
        body_client_width: document.documentElement.clientWidth,
        body_scroll_width: document.documentElement.scrollWidth,
        offenders,
      };
    },
  );
  if (
    result.inspector_scroll_width > result.inspector_client_width + 2
    || result.pane_scroll_width > result.pane_client_width + 2
    || result.body_scroll_width > result.body_client_width + 2
    || result.offenders.length > 0
  ) {
    warn(`horizontal/clipped control audit failed during ${label} (non-fatal)`)
    writeJson(path.join(artifactRoot, 'overflow-warning.json'), result);
  }
}

async function writeStateSummary(page, filePath) {
  const summary = await page.evaluate(
    () => JSON.parse(JSON.stringify({
      activeTool,
      project_path: state?.project?.path || '',
      shots: state?.project?.analysis?.shots?.length || 0,
      merge_sources: state?.project?.merge_sources || [],
      output_profiles: state?.output_profiles || [],
      export: state?.project?.export || {},
      overlay: state?.project?.overlay || {},
    })),
  );
  writeJson(filePath, summary);
}

async function writeScreenshotManifest() {
  const screenshots = artifacts.filter((item) => item.endsWith('.png')).map((item) => path.basename(item));
  writeJson(path.join(artifactRoot, 'screenshots.json'), screenshots);
}

async function writeContactSheetHtml() {
  const screenshots = artifacts.filter((item) => item.endsWith('.png'));
  const html = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Packaged Release Proof Contact Sheet</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #111827; color: #f3f4f6; margin: 0; padding: 24px; }
    h1 { margin: 0 0 16px; font-size: 24px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }
    figure { margin: 0; padding: 12px; background: #1f2937; border-radius: 12px; }
    figcaption { margin-top: 8px; font-size: 13px; word-break: break-all; }
    img { width: 100%; height: auto; border-radius: 8px; display: block; }
  </style>
</head>
<body>
  <h1>Packaged Release Proof Contact Sheet</h1>
  <div class="grid">
    ${screenshots.map((file) => `<figure><img src="${path.relative(artifactRoot, file)}" alt="${path.basename(file)}"><figcaption>${path.basename(file)}</figcaption></figure>`).join('\n')}
  </div>
</body>
</html>`;
  writeText(path.join(artifactRoot, 'contact-sheet.html'), html);
}

function domActionProbeInitializer() {
    if (window.__e2eDomActionProbeInstalled) return;
    window.__e2eDomActionProbeInstalled = true;
    try {
      window.__e2eDomActions = JSON.parse(sessionStorage.getItem('splitshot.e2eDomActions') || '[]');
    } catch {
      window.__e2eDomActions = [];
    }
    const preferred = [
      'data-tool', 'data-settings-section', 'data-shotml-section', 'data-shotml-setting',
      'data-text-box-field', 'data-popup-field', 'data-merge-source-field', 'data-stage-field',
      'data-intro-outro-field', 'data-field', 'data-boundary-kind', 'data-text-box-action',
      'data-media-section', 'data-summary-metric', 'data-metric-id', 'data-remove-box',
      'data-stage-id', 'data-popup-action', 'name',
    ];
    const identity = (node) => {
      if (!(node instanceof Element)) return '';
      if (node.id) return `id:${node.id}`;
      for (const attribute of preferred) {
        const value = node.getAttribute(attribute);
        if (value) return `${attribute}:${value}`;
      }
      const label = node.getAttribute('aria-label') || node.getAttribute('title')
        || node.textContent || '';
      const normalized = label.replace(/\s+/g, ' ').trim().slice(0, 160);
      return normalized ? `${node.tagName.toLowerCase()}:${normalized}` : '';
    };
    for (const eventName of ['click', 'change', 'input']) {
      document.addEventListener(eventName, (event) => {
        const target = event.target instanceof Element ? event.target : null;
        const key = identity(target);
        if (!key) return;
        window.__e2eDomActions.push({
          event: eventName,
          identity: key,
          trusted: event.isTrusted,
          time: new Date().toISOString(),
        });
        sessionStorage.setItem('splitshot.e2eDomActions', JSON.stringify(window.__e2eDomActions));
      }, true);
    }
}

async function installDomActionProbe(page) {
  await page.addInitScript(domActionProbeInitializer);
  await page.evaluate(domActionProbeInitializer);
}

async function openTimingWorkbench(page) {
  await openTool(page, 'timing');
  const expandButton = page.locator('#expand-timing');
  if (await expandButton.count()) {
    const workbench = page.locator('#timing-workbench');
    if (!(await workbench.isVisible().catch(() => false))) {
      await expandButton.click({ force: true, timeout: 5000 });
      await workbench.waitFor({ state: 'visible', timeout: 30000 });
    }
  }
  await waitForUiSettled(page);
}

async function apiUpload(url, filePath, fileName, mimeType) {
  const httpApi = require('http');
  const boundary = '----BD' + Date.now().toString(36);
  const fileData = fs.readFileSync(filePath);
  const header = `--${boundary}\r\nContent-Disposition: form-data; name="file"; filename="${fileName}"\r\nContent-Type: ${mimeType}\r\n\r\n`;
  const footer = `\r\n--${boundary}--\r\n`;
  const body = Buffer.concat([Buffer.from(header), fileData, Buffer.from(footer)]);
  return new Promise((resolve) => {
    const req = httpApi.request(`http://127.0.0.1:${port}${url}`, {
      method: 'POST',
      headers: { 'Content-Type': `multipart/form-data; boundary=${boundary}`, 'Content-Length': body.length },
    }, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        try { resolve({ status: res.statusCode, body: JSON.parse(data) }); }
        catch { resolve({ status: res.statusCode, body: data }); }
      });
    });
    req.on('error', (e) => resolve({ status: 0, error: e.message }));
    req.write(body);
    req.end();
  });
}

async function configureOutputProfileReviewAndBadges(page, sourceId) {
  await openTool(page, 'overlay', 'overlay-before-profile');
  await page.locator('#show-overlay').check();
  // Use XL badge size for reliable OCR in Windows CI
  const badgeSize = 'XL';
  await page.locator('#badge-size').selectOption(badgeSize);
  await waitForCondition(page, (value) => state?.project?.overlay?.badge_size === value, badgeSize);

  await openTool(page, 'export', 'export-before-profile');
  await measureStep('output-profile-create', THRESHOLDS.profile_create_ms, async () => {
    // Create profile via direct API call (bypasses button click + state polling)
    const result = await page.evaluate(async () => {
      const r = await fetch('/api/output-profiles/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_name: 'Release Proof Profile', profile_kind: 'stage_output' }),
      });
      const data = await r.json();
      return { ok: r.ok, count: (data.output_profiles || []).length, error: data.error || '' };
    });
    if (!result.ok || result.count === 0) {
      fail(`output profile create failed: ok=${result.ok} count=${result.count} error=${result.error}`);
    }
    // Reload page to pick up fresh state
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForFunction('() => Boolean(state?.project?.path)', null, { timeout: 15000 });
    await page.waitForFunction(
      () => (state?.output_profiles || []).length > 0,
      null,
      { timeout: 10000 },
    );
    await openTool(page, 'export');
    await waitForUiSettled(page);
  });
  const profileId = await page.locator('#output-profile-select').inputValue();
  if (!profileId) fail('output profile was not auto-selected');
  if (await page.locator('#output-profile-name').isDisabled()) fail('output profile name should be enabled after create');
  if (await page.locator('#output-profile-type').isDisabled()) fail('output profile type should be enabled after create');
  if (await page.locator('#output-profile-frame').isDisabled()) fail('output profile frame should be enabled after create');

  const frameProfile = await alternateSelectValue(page, '#output-profile-frame');
  const profileKind = await alternateSelectValue(page, '#output-profile-type');
  await measureStep('output-profile-edit', THRESHOLDS.profile_edit_ms, async () => {
    await setInputValue(page, '#output-profile-name', 'Packaged Release Proof Profile');
    await page.locator('#output-profile-frame').selectOption(frameProfile);
    await page.locator('#output-profile-type').selectOption(profileKind);
    await waitForCondition(
      page,
      (payload) => {
        const profile = (state?.output_profiles || []).find((item) => item.output_id === payload.profileId);
        return Boolean(profile)
          && profile.profile_name === 'Packaged Release Proof Profile'
          && profile.profile_kind === payload.profileKind
          && profile.frame_profile === payload.frameProfile;
      },
      { profileId, profileKind, frameProfile },
    );
  });
  await screenshot(page, 'export-profile-created');

  await openTool(page, 'review', 'review-before-text-boxes');
  const originalBoxCount = await page.locator('.text-box-card[data-box-id]').count();
  await measureStep('review-add-custom-box', THRESHOLDS.review_source_update_ms, async () => {
    await page.locator('#review-add-text-box').click();
    await page.waitForFunction(
      (count) => (state?.project?.overlay?.text_boxes || []).length === count + 1,
      originalBoxCount,
      { timeout: 30000 },
    );
  });
  actionLedger.push({ action: 'click', target: '#review-add-text-box', count: 1, status: 'passed' });
  const customCard = page.locator('.text-box-card[data-box-id]').last();
  await customCard.locator('[data-text-box-field="text"]').fill('Packaged custom review box');
  await customCard.locator('[data-text-box-field="text"]').blur();
  await waitForCondition(
    page,
    () => (state?.project?.overlay?.text_boxes || [])
      .some((box) => box.source === 'manual' && box.text === 'Packaged custom review box'),
    null,
    30000,
  );

  await measureStep('review-add-summary-box', THRESHOLDS.review_source_update_ms, async () => {
    await page.locator('#review-add-imported-box').click();
    await page.waitForFunction(
      () => (state?.project?.overlay?.text_boxes || [])
        .some((box) => box.source === 'imported_summary'),
      null,
      { timeout: 30000 },
    );
  });
  actionLedger.push({ action: 'click', target: '#review-add-imported-box', count: 1, status: 'passed' });
  const summaryCard = page.locator('.text-box-card[data-box-id]')
    .filter({ has: page.locator('[data-text-box-field="source"][value="imported_summary"]') })
    .first();
  const summaryPreview = page.locator('.text-box-card[data-box-id] [data-text-box-preview]').last();
  if (!(await summaryPreview.inputValue()).includes('Overall')) {
    fail('review summary box did not render authentic imported standings text');
  }
  if (await page.locator('.text-box-card button[aria-label*="Minimize"]').count()) {
    fail('Review text-box editors must remain expanded without minimize controls');
  }
  if (await summaryCard.count()) await summaryCard.scrollIntoViewIfNeeded();
  await screenshot(page, 'review-text-boxes');
  passCases(
    [
      'review.always-expanded-no-minimize', 'review.summary-custom-boxes',
      'review.authentic-match-text',
    ],
    ['e2e-logs/screenshot-review-text-boxes.png', 'action-ledger.json', 'request-ledger.json'],
  );

  await openTool(page, 'overlay', 'overlay-export-badges');
  await measureStep('export-badges', THRESHOLDS.export_badges_ms, async () => {
    await page.locator('#export-badges').click();
    await page.waitForFunction(
      (payload) => {
        const profile = (state?.output_profiles || []).find((item) => item.output_id === payload.profileId);
        if (!profile?.metric_caption_preset) return false;
        const parsed = JSON.parse(profile.metric_caption_preset);
        return parsed.badge_size === payload.badgeSize;
      },
      { profileId, badgeSize },
      { timeout: 30000 },
    );
  });
  await screenshot(page, 'overlay-badges-exported');
  return { profileId, badgeSize };
}

async function configureIntroOutro(page) {
  await openTool(page, 'intro-outro', 'intro-outro-before-media');
  for (const [kind, mediaPath, fadeIn, fadeOut] of [
    ['intro', primaryVideoPath, '0.4', '0.6'],
    ['outro', secondaryVideoPath, '0.7', '0.9'],
  ]) {
    await page.locator(`[data-boundary-kind="${kind}"]`).click();
    actionLedger.push({ action: 'click', target: `[data-boundary-kind="${kind}"]`, count: 1, status: 'passed' });
    const response = await page.evaluate(
      async (payload) => callApi('/api/project/in-out/media', payload),
      { kind, path: mediaPath },
    );
    if (!response?.project) throw new Error(`${kind} media selection failed`);
    await waitForCondition(
      page,
      (expectedKind) => Boolean(state?.project?.[`${expectedKind}_clip`]?.asset?.path),
      kind,
      30000,
    );
    await setInputValue(page, '#intro-outro-fade-in', fadeIn);
    await setInputValue(page, '#intro-outro-fade-out', fadeOut);
    await waitForCondition(
      page,
      ({ expectedKind, expectedIn, expectedOut }) => {
        const clip = state?.project?.[`${expectedKind}_clip`];
        return Number(clip?.fade_in_s) === Number(expectedIn)
          && Number(clip?.fade_out_s) === Number(expectedOut);
      },
      { expectedKind: kind, expectedIn: fadeIn, expectedOut: fadeOut },
      30000,
    );
    await page.locator('#intro-outro-add-text').click();
    actionLedger.push({ action: 'click', target: '#intro-outro-add-text', count: 1, status: 'passed' });
    await page.locator('#intro-outro-add-match').click();
    actionLedger.push({ action: 'click', target: '#intro-outro-add-match', count: 1, status: 'passed' });
    await waitForCondition(
      page,
      (expectedKind) => {
        const boxes = state?.project?.[`${expectedKind}_clip`]?.overlay?.text_boxes || [];
        return boxes.some((box) => box.source === 'manual')
          && boxes.some((box) => box.source === 'match_summary');
      },
      kind,
      30000,
    );
    const matchText = await page.locator('.intro-outro-preview-badge').last().innerText();
    if (!matchText.includes('Overall') || !matchText.includes('Points Down')) {
      fail(`${kind} match-results overlay did not show authentic standings fields`);
    }
    await screenshot(page, `intro-outro-${kind}`);
  }
  await page.locator('[data-boundary-kind="intro"]').click();
  await waitForCondition(page, () => document.querySelector('.intro-outro-kind-tabs .active')?.textContent === 'Intro', null);
  passCases(
    [
      'intro-outro.independent-video-audio-fades',
      'intro-outro.manual-match-summary-fields',
    ],
    ['e2e-logs/screenshot-intro-outro-intro.png', 'e2e-logs/screenshot-intro-outro-outro.png'],
  );
}

async function processCombinedOutput(page, artifactRoot) {
  await openTool(page, 'queue', 'combined-before');
  await page.locator('#queue-include-intro').check();
  await page.locator('#queue-include-outro').check();
  await waitForCondition(
    page,
    () => state?.project?.queue_settings?.include_intro === true
      && state?.project?.queue_settings?.include_outro === true,
    null,
    30000,
  );
  const requeue = page.locator('.queue-membership-btn').filter({ hasText: 'Requeue' }).first();
  if (await requeue.count()) await requeue.click();
  await waitForCondition(
    page,
    () => (state?.project?.queue || []).some((entry) => ['queued', 'stale'].includes(entry.status)),
    null,
    30000,
  );
  const responsePromise = page.waitForResponse(
    (response) => response.url().endsWith('/api/project/queue/process')
      && response.request().method() === 'POST',
    { timeout: 600000 },
  );
  await page.locator('#queue-combined-btn').click();
  const response = await responsePromise;
  const payload = await response.json();
  const outputPath = String(payload?.project?.last_combined_output_path || '');
  if (!outputPath) throw new Error('combined queue processing returned no output path');
  const validation = await waitForStableExportFile(page, outputPath, 600000);
  if (!validation) throw new Error('combined output did not stabilize as a valid MP4');
  const destination = path.join(exportDir, 'combined-output.mp4');
  fs.copyFileSync(outputPath, destination);
  artifacts.push(destination);
  writeJson(path.join(artifactRoot, 'combined-output-metadata.json'), validation);
  await screenshot(page, 'combined-processed');
  passCases(
    ['queue.process-one-file', 'intro-outro.combined-output-boundaries', 'output.combined-real-video'],
    ['exports/combined-output.mp4', 'combined-output-metadata.json', 'e2e-logs/screenshot-combined-processed.png'],
  );
  return outputPath;
}

async function runReleaseProof(page) {
  if (!primaryVideoPath || !secondaryVideoPath || !practiscorePath) {
    fail('release-proof requires committed primary, secondary, and PractiScore paths');
    return;
  }
  ensureDir(exportDir);

  const uploadResponse = await apiUpload('/api/files/primary', primaryVideoPath, path.basename(primaryVideoPath), 'video/mp4');
  if (uploadResponse.status !== 200 || !uploadResponse.body) {
    fail(`primary upload failed: ${uploadResponse.status}`);
    return;
  }
  try { await page.evaluate((payload) => { if (typeof applyRemoteState === 'function') applyRemoteState(payload); }, uploadResponse.body); } catch {}
  const shotCount = await waitForDetectedShots(page, 30000);
  if (shotCount <= 0) fail('primary analysis produced 0 shots after upload');
  await screenshot(page, 'release-01-primary-imported');
  passCases(
    ['media.preview-continuity'],
    ['e2e-logs/screenshot-release-01-primary-imported.png', 'request-ledger.json'],
  );

  const practiscoreResponse = await apiUpload(
    '/api/files/practiscore',
    practiscorePath,
    path.basename(practiscorePath),
    'text/csv',
  );
  if (practiscoreResponse.status !== 200 || !practiscoreResponse.body) {
    fail(`PractiScore upload failed: ${practiscoreResponse.status}`);
    return;
  }
  try {
    await page.evaluate(
      (payload) => { if (typeof applyRemoteState === 'function') applyRemoteState(payload); },
      practiscoreResponse.body,
    );
  } catch {}
  writeJson(path.join(artifactRoot, 'practiscore-import-response.json'), practiscoreResponse.body);
  await page.waitForFunction(
    () => state?.practiscore_options?.detected_match_type === 'idpa'
      && (state?.practiscore_options?.competitors || []).length === 27
      && (state?.practiscore_options?.stage_numbers || []).length === 4,
    null,
    { timeout: 30000 },
  );
  await screenshot(page, 'release-01b-practiscore-imported');
  passCases(
    [
      'project.practiscore-import-idpa', 'project.practiscore-27-competitors',
      'project.practiscore-four-stages', 'project.practiscore-standings-penalties',
      'score.authentic-import-reference', 'metrics.real-27-cohort',
    ],
    ['practiscore-import-response.json', 'e2e-logs/screenshot-release-01b-practiscore-imported.png'],
  );

  await openTool(page, 'merge', 'release-02-merge-pane');
  await page.locator('#merge-media-input').setInputFiles(secondaryVideoPath);
  await waitForCondition(page, () => (state?.project?.merge_sources || []).length === 1, null, 30000);
  await openTool(page, 'merge');
  await page.locator('#merge-enabled').check();
  await waitForCondition(page, () => state?.project?.merge?.enabled === true, null);
  await page.locator('#merge-layout').selectOption('pip');
  await waitForCondition(page, () => state?.project?.merge?.layout === 'pip', null);
  await screenshot(page, 'release-03-merge-sources');
  passCases(
    ['compose.enablement', 'compose.source-disclosures'],
    ['e2e-logs/screenshot-release-03-merge-sources.png', 'request-ledger.json'],
  );

  const firstCard = page.locator('.merge-media-card').first();
  const sourceId = await firstCard.getAttribute('data-source-id');
  if (!sourceId) fail('merge source id missing for release-proof flow');
  await ensureMergeCardExpanded(firstCard);
  await screenshot(page, 'release-04-merge-card-expanded');

  await page.locator('#expand-waveform').click().catch(() => {});
  await waitForUiSettled(page);
  await screenshot(page, 'release-05-waveform-expanded');

  const trimCard = await ensureTrimCardVisible(page, sourceId);
  await trimCard.locator('.trim-analyze-btn').click({ force: true });
  await waitForCondition(
    page,
    (targetSourceId) => {
      const source = (state?.project?.merge_sources || []).find((item) => item.id === targetSourceId);
      return Boolean(source)
        && source.sync_analysis_status === 'ready'
        && source.sync_offset_source === 'auto';
    },
    sourceId,
    120000,
  );
  await screenshot(page, 'release-06-sync-ready');

  await measureStep('per-source-layout', THRESHOLDS.source_commit_ms, async () => {
    await openTool(page, 'merge');
    await setSelectValue(page, `.merge-media-card[data-source-id="${sourceId}"] [data-merge-source-field="placement_mode"]`, 'above_below');
    await waitForUiSettled(page);
  });
  await screenshot(page, 'release-07-role-layout-committed');

  const trimCardForApply = await ensureTrimCardVisible(page, sourceId);
  await setInputValue(page, `.trim-source-card[data-source-id="${sourceId}"] input[data-trim-start]`, '0.5');
  await setInputValue(page, `.trim-source-card[data-source-id="${sourceId}"] input[data-trim-end]`, '1.5');
  await measureStep('trim-apply', THRESHOLDS.trim_apply_ms, async () => {
    await trimCardForApply.locator('.trim-apply-btn').click({ force: true });
    await waitForCondition(
      page,
      (targetSourceId) => {
        const source = (state?.project?.merge_sources || []).find((item) => item.id === targetSourceId);
        const trim = source?.trim_derivative;
        return Boolean(trim?.derivative_path)
          && trim.active_path_kind === 'local_derivative';
      },
      sourceId,
      120000,
    );
  });
  await screenshot(page, 'release-08-trim-active');
  passCases(
    ['trim.sync-analysis'],
    ['e2e-logs/screenshot-release-08-trim-active.png', 'request-ledger.json'],
  );

  const profile = await configureOutputProfileReviewAndBadges(page, sourceId);
  await configureIntroOutro(page);
  await openTimingWorkbench(page);
  await screenshot(page, 'release-09-timing-workbench');

  for (const tool of ['project', 'merge', 'scoring', 'timing', 'markers', 'overlay', 'review', 'export', 'metrics', 'shotml', 'settings']) {
    await openTool(page, tool, `pane-${tool}`);
    await assertNoHorizontalOverflow(page, tool);
  }

  await openTool(page, 'export', 'release-10-export-pane');
  await measureStep('queue-process', THRESHOLDS.queue_process_ms, async () => {
    const outputPath = await queueAndProcessCurrentStage(page, artifactRoot, 'release-10');
    if (!outputPath) return;
  });
  await openTool(page, 'queue');
  await page.locator('#queue-show-log').click();
  await page.waitForFunction(() => document.getElementById('export-log-modal')?.hidden === false, null, { timeout: 30000 });
  await screenshot(page, 'release-11-export-log');
  const exportLog = await page.evaluate(() => String(state?.project?.export?.last_log || ''));
  writeText(path.join(artifactRoot, 'export-log.txt'), exportLog);
  passCases(
    [
      'queue.output-reveal-log-statuses',
      'queue.individual-processing', 'queue.live-final-aggregate-progress',
      'queue.logs-success-validation-errors', 'queue.owns-execution',
      'export.queue-handoff', 'export.settings-only', 'output.individual-real-video',
    ],
    ['exports/e2e-export-test.mp4', 'queue-process-response.json', 'export-log.txt'],
  );
  await page.locator('#close-export-log').click();
  await page.waitForFunction(() => document.getElementById('export-log-modal')?.hidden === true, null, { timeout: 30000 });
  await processCombinedOutput(page, artifactRoot);

  const trimCardForClear = await ensureTrimCardVisible(page, sourceId);
  await screenshot(page, 'release-12-before-trim-clear');
  await measureStep('trim-clear', THRESHOLDS.trim_clear_ms, async () => {
    await trimCardForClear.locator('.trim-clear-btn').click({ force: true });
    await waitForCondition(
      page,
      (targetSourceId) => {
        const source = (state?.project?.merge_sources || []).find((item) => item.id === targetSourceId);
        const trim = source?.trim_derivative;
        return Boolean(source)
          && (!trim?.derivative_path)
          && trim?.active_path_kind !== 'local_derivative';
      },
      sourceId,
      30000,
    );
  });
  await screenshot(page, 'release-13-trim-cleared');

  await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForFunction(() => Boolean(state?.project?.path), null, { timeout: 60000 });
  await openTool(page, 'merge', 'release-14-reloaded-merge');
  await waitForCondition(
    page,
    (targetSourceId) => {
      const source = (state?.project?.merge_sources || []).find((item) => item.id === targetSourceId);
      const trim = source?.trim_derivative;
      const role = source?.camera_role || source?.angle_role || '';
      return (role === 'follow' || role === 'detail')
        && source?.placement?.mode === 'above_below'
        && source?.sync_analysis_status === 'ready'
        && (!trim?.derivative_path)
        && trim?.active_path_kind !== 'local_derivative';
    },
    sourceId,
    30000,
  );

  await openTool(page, 'review', 'release-15-reloaded-review');
  await waitForCondition(
    page,
    () => {
      const boxes = state?.project?.overlay?.text_boxes || [];
      return boxes.some((box) => box.source === 'manual' && box.text === 'Packaged custom review box')
        && boxes.some((box) => box.source === 'imported_summary');
    },
    null,
    15000,
  );

  await writeStateSummary(page, path.join(artifactRoot, 'state-summary.json'));
  passCases(
    ['compose.lifecycle-persistence', 'review.lifecycle-persistence', 'project.practiscore-persistence'],
    ['state-summary.json', 'e2e-logs/screenshot-release-15-reloaded-review.png'],
  );
}

async function runStandardFlow(page) {
  let videoFile = '';
  if (primaryVideoPath) {
    try { if (fs.statSync(primaryVideoPath).isFile()) videoFile = primaryVideoPath; } catch {}
  }
  if (!videoFile) {
    const fallback = path.join(__dirname, '..', '..', 'tests', 'fixtures', 'media', 'stage.mp4');
    try { if (fs.statSync(fallback).isFile()) videoFile = fallback; } catch {}
  }
  if (!videoFile) {
    fail('no test video found');
    return;
  }

  log(`uploading video to /api/files/primary: ${videoFile}`);
  const r = await apiUpload('/api/files/primary', videoFile, 'e2e-test.mp4', 'video/mp4');
  if (r.status !== 200 || !r.body) {
    fail(`primary upload failed: ${r.status}`);
    return;
  }
  try { await page.evaluate((payload) => { if (typeof applyRemoteState === 'function') applyRemoteState(payload); }, r.body); } catch {}
  const shotCount = await waitForDetectedShots(page, 5000);
  if (shotCount <= 0) {
    fail('primary analysis produced 0 shots after upload');
    return;
  }
  await screenshot(page, '03b-video-imported');

  const tools = ['project', 'merge', 'scoring', 'timing', 'markers', 'overlay', 'review', 'export', 'metrics', 'settings'];
  for (const tool of tools) {
    await openTool(page, tool, `tool-${tool}`);
  }

  ensureDir(exportDir);
  await openTool(page, 'export', '06-export-tool');
  const outputPath = await queueAndProcessCurrentStage(page, artifactRoot, '06');
  if (!outputPath) fail('queue export did not return an output path');
  await screenshot(page, '07-after-export');
}

async function main() {
  ensureDir(logDir);
  ensureDir(artifactRoot);
  ensureDir(exportDir);
  log(`=== E2E test start === port=${port} scope=${e2eScope || 'standard'}`);

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-gpu', '--disable-software-rasterizer'],
  });
  const consoleLogs = [];
  const pageErrors = [];
  const httpErrors = [];
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();

  page.on('console', (msg) => {
    const entry = { type: msg.type(), text: msg.text(), time: new Date().toISOString() };
    consoleLogs.push(entry);
    try { fs.appendFileSync(path.join(logDir, 'console.log'), `[${entry.time}] ${entry.type}: ${entry.text}\n`); } catch {}
  });
  page.on('pageerror', (err) => {
    const entry = { message: err.message, stack: err.stack, time: new Date().toISOString() };
    pageErrors.push(entry);
    try { fs.appendFileSync(path.join(logDir, 'page-errors.log'), `[${entry.time}] ${entry.message}\n${entry.stack}\n---\n`); } catch {}
  });
  page.on('response', (resp) => {
    if (resp.url().includes('/api/')) {
      requestLedger.push({
        method: resp.request().method(),
        url: resp.url(),
        status: resp.status(),
        time: new Date().toISOString(),
      });
    }
    if (resp.status() >= 400) {
      httpErrors.push({ status: resp.status(), url: resp.url(), time: new Date().toISOString() });
      try { fs.appendFileSync(path.join(logDir, 'http-errors.log'), `[${new Date().toISOString()}] ${resp.status()} ${resp.url()}\n`); } catch {}
    }
  });

  try {
    await page.goto(baseUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await screenshot(page, '01-after-load');
    await page.waitForFunction(() => typeof activeTool !== 'undefined', null, { timeout: 60000 });
    await installDomActionProbe(page);
    await screenshot(page, '02-app-initialized');
    await page.waitForTimeout(500);

    if (!(await page.evaluate(() => Boolean(state?.project?.path)))) {
      const pp = path.join(os.tmpdir(), 'sshot-e2e-project.ssproj');
      await page.evaluate((p) => createNewProject(p), pp);
      await page.waitForFunction(() => Boolean(state?.project?.path), null, { timeout: 15000 });
      await page.waitForTimeout(250);
      await screenshot(page, '03-project-created');
    }

    if (isReleaseProof) await runReleaseProof(page);
    else await runStandardFlow(page);

    if (stopAfterExport) {
      log('stopping after export-proof scope');
    }

    const browserState = await page.evaluate(() => ({
      shots: state?.project?.analysis?.shots?.length || 0,
      popups: state?.project?.popups?.length || 0,
      merge_sources: state?.project?.merge_sources?.length || 0,
    }));

    const runtimeInventory = isReleaseProof
      ? await collectRuntimeInventory(page)
      : { discovered: 0, mapped: 0, gaps: 0 };
    const domActions = await page.evaluate(() => [...(window.__e2eDomActions || [])]);
    actionLedger.push(...domActions.map((item) => ({
      action: item.event,
      target: item.identity,
      count: 1,
      trusted: item.trusted,
      status: 'passed',
      time: item.time,
    })));
    writeJson(path.join(artifactRoot, 'action-ledger.json'), actionLedger);
    writeJson(path.join(artifactRoot, 'request-ledger.json'), requestLedger);
    writeJson(path.join(artifactRoot, 'case-observations.json'), {
      cases: [...caseObservations.values()].sort((left, right) => left.id.localeCompare(right.id)),
    });
    writeJson(path.join(artifactRoot, 'timings.json'), timings);
    await writeScreenshotManifest();
    await writeContactSheetHtml();

    const result = failures.length === 0 && pageErrors.length === 0 ? 'passed' : 'failed';
    const summary = {
      result,
      scope: e2eScope || 'standard',
      shots: browserState.shots,
      popups: browserState.popups,
      merge_sources: browserState.merge_sources,
      consoleLogs: consoleLogs.length,
      pageErrors: pageErrors.length,
      artifacts: artifacts.length,
      pageErrorsList: pageErrors,
      httpErrors,
      failures,
      timings,
      runtimeInventory,
      artifact_root: artifactRoot,
      export_dir: exportDir,
    };
    fs.writeFileSync(path.join(logDir, 'summary.json'), JSON.stringify(summary, null, 2));
    writeJson(path.join(artifactRoot, 'summary.json'), summary);
    log(`summary saved: ${JSON.stringify(summary)}`);

    if (pageErrors.length > 0) {
      warn(`${pageErrors.length} page errors detected`);
      for (const error of pageErrors) warn(`  ${error.message}`);
    }

    // This browser is the installed Electron process reached over CDP. Closing
    // its context/browser can terminate the app before the Python harness reads
    // final state and performs restart/audit proof. Process exit below safely
    // disconnects the CDP client without owning the installed app lifecycle.
    if (result === 'failed') {
      log('=== E2E test failed ===');
      process.exit(1);
    }
    log('=== E2E test passed ===');
    process.exit(0);
  } catch (err) {
    console.error('PW: FAILED -', err.message);
    console.error(err.stack);
    try {
      const summary = {
        result: 'failed',
        scope: e2eScope || 'standard',
        error: err.message,
        stack: err.stack,
        consoleLogs: consoleLogs.length,
        pageErrors: pageErrors.length,
        failures,
      };
      fs.writeFileSync(path.join(logDir, 'summary.json'), JSON.stringify(summary, null, 2));
      writeJson(path.join(artifactRoot, 'summary.json'), summary);
    } catch {}
    process.exit(1);
  }
}

main().catch(async (err) => {
  console.error('PW: FAILED -', err.message);
  console.error(err.stack);
  try {
    const summary = {
      result: 'failed',
      scope: e2eScope || 'standard',
      error: err.message,
      stack: err.stack,
      failures,
    };
    fs.writeFileSync(path.join(logDir, 'summary.json'), JSON.stringify(summary, null, 2));
    writeJson(path.join(artifactRoot, 'summary.json'), summary);
  } catch {}
  process.exit(1);
});
