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
const tertiaryVideoPath = process.env.E2E_TERTIARY_VIDEO_PATH || '';
const exportDir = process.env.E2E_EXPORT_DIR || path.join(artifactRoot, 'exports');
const baseUrl = `http://127.0.0.1:${port}`;
const artifacts = [];
const failures = [];
const timings = [];
const e2eScope = process.env.SPLITSHOT_E2E_SCOPE || '';
const stopAfterExport = e2eScope === 'export-proof';
const isReleaseProof = e2eScope === 'release-proof';

const THRESHOLDS = {
  tool_switch_settled_ms: 500,
  profile_create_ms: 750,
  profile_edit_ms: 750,
  review_source_update_ms: 750,
  export_badges_ms: 750,
  source_commit_ms: 750,
  trim_apply_ms: 3000,
  trim_clear_ms: 2000,
  export_ack_ms: 1000,
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
  await measureStep(`tool-switch:${tool}`, THRESHOLDS.tool_switch_settled_ms, async () => {
    await page.locator(`button[data-tool="${tool}"]`).click({ force: true, timeout: 10000 });
    await page.waitForFunction((targetTool) => activeTool === targetTool, tool, { timeout: 10000 });
    await waitForUiSettled(page);
  });
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
  await page.locator(selector).evaluate(
    (element, nextValue) => {
      element.value = String(nextValue);
      element.dispatchEvent(new Event('input', { bubbles: true }));
      element.dispatchEvent(new Event('change', { bubbles: true }));
    },
    value,
  );
}

async function setSelectValue(page, selector, value) {
  await page.locator(selector).evaluate(
    (element, nextValue) => {
      element.value = String(nextValue);
      element.dispatchEvent(new Event('change', { bubbles: true }));
    },
    value,
  );
}

async function alternateSelectValue(page, selector) {
  return page.locator(selector).evaluate(
    (select) => [...select.options].find((option) => option.value && option.value !== select.value)?.value || select.value,
  );
}

async function ensureMergeCardExpanded(card) {
  const body = card.locator('.merge-media-card-body');
  if (await body.evaluate((element) => Boolean(element?.hidden))) {
    await card.locator('button[aria-label*="PiP item controls"]').click({ force: true });
    await body.waitFor({ state: 'visible', timeout: 10000 });
  }
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
    fail(`horizontal/clipped control audit failed during ${label}`);
    writeJson(path.join(artifactRoot, 'overflow-failure.json'), result);
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

async function openTimingWorkbench(page) {
  await openTool(page, 'timing');
  const expandButton = page.locator('#expand-timing');
  if (await expandButton.count()) {
    const workbench = page.locator('#timing-workbench');
    if (!(await workbench.isVisible().catch(() => false))) {
      await expandButton.click({ force: true, timeout: 5000 });
      await workbench.waitFor({ state: 'visible', timeout: 10000 });
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
  const badgeSize = await alternateSelectValue(page, '#badge-size');
  await page.locator('#badge-size').selectOption(badgeSize);
  await waitForCondition(page, (value) => state?.project?.overlay?.badge_size === value, badgeSize);

  await openTool(page, 'export', 'export-before-profile');
  await measureStep('output-profile-create', THRESHOLDS.profile_create_ms, async () => {
    await page.locator('#create-output-profile').click();
    await page.waitForFunction(
      () => {
        const select = document.getElementById('output-profile-select');
        return Boolean(select?.value) && (state?.output_profiles || []).length > 0;
      },
      null,
      { timeout: 10000 },
    );
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

  await openTool(page, 'review', 'review-before-retained');
  const hasReviewSource = await page.locator('#review-source-status').count() > 0;
  if (hasReviewSource) {
    if ((await page.locator('#review-source-status').textContent())?.trim() !== 'Live') {
      fail('review source should start at Live before a retained source is chosen');
    }
    await measureStep('review-source-retained', THRESHOLDS.review_source_update_ms, async () => {
      await page.locator('#review-source-select').selectOption(sourceId);
      await page.locator('#review-set-source').click();
      await page.waitForFunction(
        (payload) => {
          const profile = (state?.output_profiles || []).find((item) => item.output_id === payload.profileId);
          return profile?.review_source_id === payload.sourceId
            && document.getElementById('review-source-status')?.textContent?.startsWith('Retained: ') === true;
        },
        { profileId, sourceId },
        { timeout: 10000 },
      );
    });
    await screenshot(page, 'review-retained');

    await openTool(page, 'overlay');
    await openTool(page, 'export');
    await openTool(page, 'review');
    await waitForCondition(
      page,
      (expectedId) => {
        const select = document.getElementById('review-source-select');
        return select?.value === expectedId
          && document.getElementById('review-source-status')?.textContent?.startsWith('Retained: ') === true;
      },
      sourceId,
    );

    await measureStep('review-source-live', THRESHOLDS.review_source_update_ms, async () => {
      await page.locator('#review-source-select').selectOption('');
      await page.locator('#review-set-source').click();
      await page.waitForFunction(
        (profileIdArg) => {
          const profile = (state?.output_profiles || []).find((item) => item.output_id === profileIdArg);
          return (!profile?.review_source_id || profile.review_source_id === '')
            && document.getElementById('review-source-status')?.textContent === 'Live';
        },
        profileId,
        { timeout: 10000 },
      );
    });
    await screenshot(page, 'review-live');

    await measureStep('review-source-retained-second-pass', THRESHOLDS.review_source_update_ms, async () => {
      await page.locator('#review-source-select').selectOption(sourceId);
      await page.locator('#review-set-source').click();
      await page.waitForFunction(
        (payload) => {
          const profile = (state?.output_profiles || []).find((item) => item.output_id === payload.profileId);
          return profile?.review_source_id === payload.sourceId
            && document.getElementById('review-source-status')?.textContent?.startsWith('Retained: ') === true;
        },
        { profileId, sourceId },
        { timeout: 10000 },
      );
    });
  } else {
    log('review source controls not present — skipping review source section');
    await screenshot(page, 'review-skip-source');
  }

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
      { timeout: 10000 },
    );
  });
  await screenshot(page, 'overlay-badges-exported');
  return { profileId, badgeSize };
}

async function runReleaseProof(page) {
  if (!primaryVideoPath || !secondaryVideoPath || !tertiaryVideoPath) {
    fail('release-proof requires primary, secondary, and tertiary video paths');
    return;
  }
  const exportFile = path.join(exportDir, 'e2e-export-test.mp4');
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

  await openTool(page, 'merge', 'release-02-merge-pane');
  await page.locator('#merge-media-input').setInputFiles([secondaryVideoPath, tertiaryVideoPath]);
  await waitForCondition(page, () => (state?.project?.merge_sources || []).length === 2, null, 30000);
  await page.locator('#merge-enabled').check();
  await waitForCondition(page, () => state?.project?.merge?.enabled === true, null);
  await page.locator('#merge-layout').selectOption('pip');
  await waitForCondition(page, () => state?.project?.merge?.layout === 'pip', null);
  await screenshot(page, 'release-03-merge-sources');

  const firstCard = page.locator('.merge-media-card').first();
  const sourceId = await firstCard.getAttribute('data-source-id');
  if (!sourceId) fail('merge source id missing for release-proof flow');
  await ensureMergeCardExpanded(firstCard);
  await screenshot(page, 'release-04-merge-card-expanded');

  await page.locator('#expand-waveform').click().catch(() => {});
  await waitForUiSettled(page);
  await screenshot(page, 'release-05-waveform-expanded');

  await firstCard.evaluate((card) => {
    const button = Array.from(card.querySelectorAll('button')).find((candidate) => /beep sync/i.test(candidate.textContent || ''));
    if (!(button instanceof HTMLButtonElement)) throw new Error('beep sync button not found');
    button.click();
  });
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
    await setSelectValue(page, `.merge-media-card[data-source-id="${sourceId}"] [data-merge-source-field="placement_mode"]`, 'above_below');
    await waitForUiSettled(page);
  });
  await screenshot(page, 'release-07-role-layout-committed');

  await setInputValue(page, `.merge-media-card[data-source-id="${sourceId}"] input[data-trim-start]`, '0.5');
  await setInputValue(page, `.merge-media-card[data-source-id="${sourceId}"] input[data-trim-end]`, '1.5');
  await measureStep('trim-apply', THRESHOLDS.trim_apply_ms, async () => {
    await firstCard.evaluate((card) => {
      const button = Array.from(card.querySelectorAll('button')).find((candidate) => (candidate.textContent || '').trim() === 'Apply');
      if (!(button instanceof HTMLButtonElement)) throw new Error('trim Apply button not found');
      button.click();
    });
    await waitForCondition(
      page,
      (targetSourceId) => {
        const source = (state?.project?.merge_sources || []).find((item) => item.id === targetSourceId);
        const trim = source?.trim_derivative;
        return Boolean(trim?.derivative_path)
          && trim.active_path_kind === 'local_derivative'
          && document.querySelector(`.merge-media-card[data-source-id="${targetSourceId}"] .merge-source-trim-status`)?.textContent === 'Trim active';
      },
      sourceId,
      120000,
    );
  });
  await screenshot(page, 'release-08-trim-active');

  const profile = await configureOutputProfileReviewAndBadges(page, sourceId);
  await openTimingWorkbench(page);
  await screenshot(page, 'release-09-timing-workbench');

  for (const tool of ['project', 'merge', 'scoring', 'timing', 'markers', 'overlay', 'review', 'export', 'metrics', 'shotml', 'settings']) {
    await openTool(page, tool, `pane-${tool}`);
    await assertNoHorizontalOverflow(page, tool);
  }

  await openTool(page, 'export', 'release-10-export-pane');
  await page.locator('#output-profile-select').selectOption(profile.profileId);
  await page.waitForFunction(
    (profileIdArg) => document.getElementById('output-profile-select')?.value === profileIdArg,
    profile.profileId,
    { timeout: 10000 },
  );
  await page.locator('#export-path').fill(exportFile);

  await measureStep('export-acknowledged', THRESHOLDS.export_ack_ms, async () => {
    await page.locator('#export-video').click({ force: true });
    await page.waitForFunction(
      () => {
        const status = String(state?.status || '');
        const lastLog = String(state?.project?.export?.last_log || '');
        const processingHidden = document.getElementById('processing-bar')?.hidden;
        return status.includes('Export') || lastLog.length > 0 || processingHidden === false;
      },
      null,
      { timeout: 10000 },
    );
  });
  const exportValidation = await waitForStableExportFile(page, exportFile, 180000);
  if (!exportValidation) {
    fail('export file did not stabilize as a valid MP4');
  } else {
    artifacts.push(exportFile);
    writeJson(path.join(artifactRoot, 'export-metadata.json'), exportValidation);
  }
  await page.locator('#show-export-log').click();
  await page.waitForFunction(() => document.getElementById('export-log-modal')?.hidden === false, null, { timeout: 10000 });
  await screenshot(page, 'release-11-export-log');
  const exportLog = await page.evaluate(() => String(state?.project?.export?.last_log || ''));
  writeText(path.join(artifactRoot, 'export-log.txt'), exportLog);
  await page.locator('#close-export-log').click();
  await page.waitForFunction(() => document.getElementById('export-log-modal')?.hidden === true, null, { timeout: 10000 });

  await openTool(page, 'merge', 'release-12-before-trim-clear');
  await ensureMergeCardExpanded(page.locator(`.merge-media-card[data-source-id="${sourceId}"]`));
  await measureStep('trim-clear', THRESHOLDS.trim_clear_ms, async () => {
    await page.locator(`.merge-media-card[data-source-id="${sourceId}"]`).evaluate((card) => {
      const button = Array.from(card.querySelectorAll('button')).find((candidate) => (candidate.textContent || '').trim() === 'Clear');
      if (!(button instanceof HTMLButtonElement)) throw new Error('trim Clear button not found');
      button.click();
    });
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

  await page.reload({ waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForFunction(() => Boolean(state?.project?.path), null, { timeout: 45000 });
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
    (expectedSourceId) => {
      const status = document.getElementById('review-source-status')?.textContent || '';
      const select = document.getElementById('review-source-select');
      return select?.value === expectedSourceId && status.startsWith('Retained: ');
    },
    sourceId,
    15000,
  );

  await writeStateSummary(page, path.join(artifactRoot, 'state-summary.json'));
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

  const exportFile = path.join(exportDir, 'e2e-export-test.mp4');
  ensureDir(exportDir);
  await openTool(page, 'export', '06-export-tool');
  const exportPathInput = page.locator('#export-path');
  if (await exportPathInput.isVisible()) {
    await exportPathInput.fill(exportFile);
    const exportBtn = page.locator('#export-video');
    if (await exportBtn.isVisible()) {
      await exportBtn.click({ force: true });
      await page.waitForFunction(() => String(state?.status || '').includes('Exported video to '), null, { timeout: 180000 });
      const exportValidation = await waitForStableExportFile(page, exportFile);
      if (!exportValidation) fail('export file did not stabilize as a valid MP4');
      else artifacts.push(exportFile);
    } else fail('export button not found');
  } else fail('export output path input not found');
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
    if (resp.status() >= 400) {
      httpErrors.push({ status: resp.status(), url: resp.url(), time: new Date().toISOString() });
      try { fs.appendFileSync(path.join(logDir, 'http-errors.log'), `[${new Date().toISOString()}] ${resp.status()} ${resp.url()}\n`); } catch {}
    }
  });

  try {
    await page.goto(baseUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await screenshot(page, '01-after-load');
    await page.waitForFunction(() => typeof activeTool !== 'undefined', null, { timeout: 45000 });
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

    await context.close();
    await browser.close();
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
