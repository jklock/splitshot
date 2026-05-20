const { chromium } = require('playwright');
const fs = require('fs');
const os = require('os');
const path = require('path');

const port = process.env.E2E_PORT || '8765';
const logDir = process.env.E2E_LOG_DIR || path.join(os.tmpdir(), 'splitshot-e2e-logs');
const videoPath = process.env.E2E_VIDEO_PATH || '';
const baseUrl = `http://127.0.0.1:${port}`;
const artifacts = [];
const failures = [];
const e2eScope = process.env.SPLITSHOT_E2E_SCOPE || '';
const stopAfterExport = e2eScope === 'export-proof';

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

async function openTimingWorkbench(page) {
  await page.locator('button[data-tool="timing"]').click({ force: true, timeout: 10000 });
  await page.waitForFunction(() => activeTool === 'timing', null, { timeout: 10000 });
  const expandButton = page.locator('#expand-timing');
  if (await expandButton.count()) {
    const workbench = page.locator('#timing-workbench');
    if (!(await workbench.isVisible().catch(() => false))) {
      await expandButton.click({ force: true, timeout: 5000 });
      await workbench.waitFor({ state: 'visible', timeout: 10000 });
    }
  }
  await page.waitForTimeout(300);
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
  const { execFileSync } = require('child_process');
  const ffprobe = process.env.SPLITSHOT_PACKAGED_FFPROBE || 'ffprobe';
  const probe = execFileSync(
    ffprobe,
    ['-v', 'error', '-show_entries', 'format=format_name,duration,size', '-of', 'json', exportFile],
    { encoding: 'utf8', timeout: 60000 }
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
      if (stat.size === lastSize) {
        stableReads += 1;
      } else {
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

async function main() {
  fs.mkdirSync(logDir, { recursive: true });
  log(`=== E2E test start === port=${port}`);

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-gpu', '--disable-software-rasterizer'],
  });
  const consoleLogs = [];
  const pageErrors = [];
  const httpErrors = [];

  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
  });
  const page = await context.newPage();

  page.on('console', msg => {
    const entry = { type: msg.type(), text: msg.text(), time: new Date().toISOString() };
    consoleLogs.push(entry);
    try { fs.appendFileSync(path.join(logDir, 'console.log'), `[${entry.time}] ${entry.type}: ${entry.text}\n`); } catch {}
  });
  page.on('pageerror', err => {
    const entry = { message: err.message, stack: err.stack, time: new Date().toISOString() };
    pageErrors.push(entry);
    try { fs.appendFileSync(path.join(logDir, 'page-errors.log'), `[${entry.time}] ${entry.message}\n${entry.stack}\n---\n`); } catch {}
  });
  page.on('response', resp => {
    if (resp.status() >= 400) {
      httpErrors.push({ status: resp.status(), url: resp.url(), time: new Date().toISOString() });
      try { fs.appendFileSync(path.join(logDir, 'http-errors.log'),
        `[${new Date().toISOString()}] ${resp.status()} ${resp.url()}\n`); } catch {}
    }
  });

  log('navigating to app...');
  await page.goto(baseUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await screenshot(page, '01-after-load');
  log('page loaded');

  log('waiting for app to initialize...');
  await page.waitForFunction(() => typeof activeTool !== 'undefined', null, { timeout: 45000 });
  await screenshot(page, '02-app-initialized');
  log('app initialized');

  await page.waitForTimeout(1000);

  if (!(await page.evaluate(() => Boolean(state?.project?.path)))) {
    log('creating new project...');
    const pp = path.join(os.tmpdir(), 'sshot-e2e-project.ssproj');
    await page.evaluate((p) => createNewProject(p), pp);
    await page.waitForFunction(() => Boolean(state?.project?.path), null, { timeout: 15000 });
    await page.waitForTimeout(500);
    await screenshot(page, '03-project-created');
    log('project created');
  }

  // Helper: multipart POST to API, return parsed response
  async function apiUpload(url, filePath, fileName, mimeType) {
    const fs_api = require('fs');
    const http_api = require('http');
    const boundary = '----BD' + Date.now().toString(36);
    const fileData = fs_api.readFileSync(filePath);
    const header = `--${boundary}\r\nContent-Disposition: form-data; name="file"; filename="${fileName}"\r\nContent-Type: ${mimeType}\r\n\r\n`;
    const footer = `\r\n--${boundary}--\r\n`;
    const body = Buffer.concat([Buffer.from(header), fileData, Buffer.from(footer)]);
    return new Promise((resolve) => {
      const req = http_api.request(`http://127.0.0.1:${port}${url}`, {
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

  // Import video via API directly (bypasses UI, triggers analysis synchronously, gets full state back)
  let videoFile = null;
  if (videoPath) {
    try { if (fs.statSync(videoPath).isFile()) { videoFile = videoPath; } } catch {}
  }
  if (!videoFile) {
    for (const v of [path.join(__dirname, '..', '..', 'tests', 'fixtures', 'media', 'stage.mp4')]) {
      try { if (fs.statSync(v).isFile()) { videoFile = v; break; } } catch {}
    }
  }
  if (videoFile) {
    log(`uploading video to /api/files/primary: ${videoFile}`);
    const r = await apiUpload('/api/files/primary', videoFile, 'e2e-test.mp4', 'video/mp4');
    if (r.status === 200 && r.body) {
      let shotCount = r.body?.project?.analysis?.shots?.length || 0;
      log(`primary analysis: ${shotCount} shots, waveform=${Boolean(r.body?.project?.analysis?.waveform_primary)}`);
      try { await page.evaluate((d) => { if (typeof applyRemoteState === 'function') applyRemoteState(d); }, r.body); } catch {}
      shotCount = await waitForDetectedShots(page, 5000);
      log(`primary analysis settled: ${shotCount} shots`);
      if (shotCount <= 0) {
        fail('primary analysis produced 0 shots after upload');
        await screenshot(page, 'fail-zero-shots');
        await dumpHtml(page, 'fail-zero-shots');
        const summary = {
          result: 'failed',
          totalTools: 0,
          activatedTools: 0,
          shots: 0,
          popups: 0,
          consoleLogs: consoleLogs.length,
          pageErrors: pageErrors.length,
          artifacts: artifacts.length,
          pageErrorsList: pageErrors,
          httpErrors,
          failures,
        };
        fs.writeFileSync(path.join(logDir, 'summary.json'), JSON.stringify(summary, null, 2));
        await context.close();
        await browser.close();
        process.exit(1);
      }
    } else {
      fail(`primary upload failed: ${r.status} ${JSON.stringify(r.body).slice(0, 200)}`);
    }
    await screenshot(page, '03b-video-imported');
  } else {
    fail('no test video found');
  }

  const tools = ['project', 'merge', 'scoring', 'timing', 'markers',
                 'overlay', 'review', 'export', 'metrics', 'settings'];
  const TOOL_COUNT = tools.length;
  let toolScreenshotDelay = 1;
  for (const t of tools) {
    const btn = page.locator(`button[data-tool="${t}"]`);
    if (await btn.isVisible()) {
      await btn.click({ force: true });
      try {
        await page.waitForFunction((tool) => activeTool === tool, t, { timeout: 15000 });
      } catch (e) {
        warn(`tool ${t} activation timed out`);
        await screenshot(page, `fail-tool-${t}`);
        await dumpHtml(page, `fail-tool-${t}`);
      }
      await page.waitForTimeout(300);
      if (toolScreenshotDelay % 3 === 0) {
        await screenshot(page, `tool-${t}`);
      }
      toolScreenshotDelay++;
      log(`tool activated: ${t}`);
    }
  }

  try {
    await openTimingWorkbench(page);
  } catch (e) {
    warn(`timing button click failed (continuing): ${e.message}`);
  }
  if ((await page.locator('.waveform-shot-card').count()) > 0) {
    try {
      const targetShotId = await page.evaluate(() => state?.timing_segments?.[0]?.shot_id || null);
      await page.locator('.waveform-shot-card').first().evaluate((card) => {
        card.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
      });
      if (targetShotId) {
        await page.waitForFunction((shotId) => selectedShotId === shotId, targetShotId, { timeout: 10000 });
      } else {
        await page.waitForTimeout(300);
      }
      await screenshot(page, '04-waveform-selected');
      log('waveform shot selected');
    } catch (e) {
      warn(`waveform click failed: ${e.message}`);
    }
  } else {
    warn('no waveform shot cards found');
  }

  for (const t of ['markers', 'overlay', 'review', 'settings', 'scoring']) {
    await page.locator(`button[data-tool="${t}"]`).click({ force: true });
    try {
      await page.waitForFunction((tool) => activeTool === tool, t, { timeout: 10000 });
    } catch (e) {
      warn(`post-tool ${t} activation timed out`);
      await screenshot(page, `fail-post-${t}`);
      await dumpHtml(page, `fail-post-${t}`);
    }
    await page.waitForTimeout(300);
  }

  // === Export verification ===
  const exportDir = process.env.E2E_EXPORT_DIR || path.join(path.dirname(logDir), 'e2e-exports');
  try { fs.mkdirSync(exportDir, { recursive: true }); } catch {}
  const exportFile = path.join(exportDir, 'e2e-export-test.mp4');
  let exportValidationPassed = false;

  log('testing export...');
  await page.locator('button[data-tool="export"]').click({ force: true });
  await page.waitForFunction(() => activeTool === 'export', null, { timeout: 10000 });
  await page.waitForTimeout(500);
  await screenshot(page, '06-export-tool');

  // Set output path and trigger export
  const exportPathInput = page.locator('#export-path');
  if (await exportPathInput.isVisible()) {
    await exportPathInput.fill(exportFile);
    await page.waitForTimeout(200);
    log('export output path set');

    const exportBtn = page.locator('#export-video');
    if (await exportBtn.isVisible()) {
      await exportBtn.click({ force: true });
      log('export triggered, waiting for completion...');

      // Wait for export to complete (state/status update or file appears)
      try {
        await page.waitForFunction(() => {
          const status = String(state?.status || '');
          return status.includes('Exported video to ');
        }, null, { timeout: 180000 });
        log('export state reports completion');
      } catch (e) {
        fail(`export completion state not detected: ${e.message}`);
        await screenshot(page, 'fail-export-completion');
        await dumpHtml(page, 'fail-export-completion');
      }

      const exportValidation = await waitForStableExportFile(page, exportFile);
      if (exportValidation) {
        const sz = exportValidation.size;
        log(`export file exists: ${exportFile} (${(sz / 1024 / 1024).toFixed(2)} MB)`);
        artifacts.push(exportFile);
        const fmt = exportValidation.probe.format?.format_name || 'unknown';
        const dur = exportValidation.probe.format?.duration || '0';
        log(`export validation: format=${fmt} duration=${dur}s size=${(sz / 1024 / 1024).toFixed(2)}MB`);
        exportValidationPassed = true;
      } else {
        let sizeHint = 'missing';
        try { sizeHint = String(fs.statSync(exportFile).size); } catch {}
        fail(`export file did not stabilize as a valid MP4 (size=${sizeHint} bytes)`);
        await screenshot(page, 'fail-export-file');
        await screenshot(page, 'fail-export-ffprobe');
        await dumpHtml(page, 'fail-export-file');
      }
    } else {
      fail('export button not found');
      await screenshot(page, 'fail-export-btn');
      await dumpHtml(page, 'fail-export-btn');
    }
  } else {
    fail('export output path input not found');
    await screenshot(page, 'fail-export-input');
    await dumpHtml(page, 'fail-export-input');
  }

  await screenshot(page, '07-after-export');
  if (!exportValidationPassed || stopAfterExport) {
    log(`stopping after export: scope=${e2eScope || 'full'} exportValidationPassed=${exportValidationPassed}`);
  } else {

    const browserState = await page.evaluate(() => ({
      shots: (typeof state !== 'undefined' && state?.project?.analysis?.shots?.length) || 0,
      popups: (typeof state !== 'undefined' && state?.project?.popups?.length) || 0,
    }));
    log(`final state: shots=${browserState.shots} popups=${browserState.popups} toolsActivated=${TOOL_COUNT}`);

    // === PractiScore import via browser file input ===
    const practiscorePaths = [
      path.join(__dirname, '..', '..', 'example_data', 'IDPA', 'IDPA.csv'),
      path.join(__dirname, '..', '..', 'example_data', 'practiscore.csv'),
    ];
    let practiscoreFile = null;
    for (const p of practiscorePaths) {
      try { if (fs.statSync(p).isFile()) { practiscoreFile = p; break; } } catch {}
    }
    if (practiscoreFile) {
      log('importing PractiScore data...');
      const practiscoreInput = page.locator('#practiscore-file-input');
      await practiscoreInput.setInputFiles(practiscoreFile);
      await page.waitForFunction(() => Boolean(state?.practiscore_options?.has_source), null, { timeout: 30000 });
      const psState = await page.evaluate(() => ({
        hasSource: Boolean(state?.practiscore_options?.has_source),
        sourceName: String(state?.practiscore_options?.source_name || ''),
        stageNumbers: Array.isArray(state?.practiscore_options?.stage_numbers) ? state.practiscore_options.stage_numbers.length : 0,
        importedSource: String(state?.project?.scoring?.imported_stage?.source_name || ''),
        competitorName: String(state?.project?.scoring?.imported_stage?.competitor_name || ''),
      }));
      log(`PractiScore: has_source=${psState.hasSource} source=${psState.sourceName || psState.importedSource} stages=${psState.stageNumbers} competitor=${psState.competitorName || 'n/a'}`);
      if (!psState.hasSource || (!psState.sourceName && !psState.importedSource)) {
        fail('PractiScore import did not retain imported source in browser state');
        await screenshot(page, 'fail-practiscore-upload');
        await dumpHtml(page, 'fail-practiscore-upload');
      }
      await screenshot(page, '08-practiscore');
    } else {
      warn('no PractiScore CSV found');
    }

    // === Merge: import second video via browser file input ===
    if (videoFile) {
      log('testing merge with second video...');
      const mergeCountBefore = await page.evaluate(() => (state?.project?.merge_sources || []).length);
      await page.locator('#merge-media-input').setInputFiles(videoFile);
      await page.waitForFunction((before) => (state?.project?.merge_sources || []).length > before, mergeCountBefore, { timeout: 30000 });
      const sources = await page.evaluate(() => (state?.project?.merge_sources || []).map((source) => ({
          id: source.id,
          path: source?.asset?.path || '',
          mediaKind: source?.media_kind || source?.asset?.media_kind || '',
        })));
      log(`merge sources: ${sources.length} (from browser state)`);
      if (sources.length > 0) {
        log(`  first source: ${sources[0].path || sources[0].id} (${sources[0].mediaKind || 'unknown'})`);
      } else {
        fail('merge import did not add any sources');
        await screenshot(page, 'fail-merge-state');
        await dumpHtml(page, 'fail-merge-state');
      }
      await screenshot(page, '09-merge');
    } else {
      warn('no video for merge test');
    }

    // === Timing: add a custom event ===
    log('testing timing events...');
    await openTimingWorkbench(page);
    const eventsBefore = await page.evaluate(() => state?.project?.analysis?.events?.length || 0);
    const kindSelect = page.locator('#timing-event-kind');
    if (await kindSelect.isVisible()) {
      await kindSelect.selectOption('custom_label');
      await page.waitForTimeout(100);
    }
    const labelInput = page.locator('#timing-event-label');
    if (await labelInput.isVisible()) {
      await labelInput.fill('E2E auto timing event');
      await page.waitForTimeout(100);
    }
    const addEventBtn = page.locator('#add-timing-event');
    if (await addEventBtn.isVisible()) {
      await addEventBtn.click();
      await page.waitForFunction((before) => (state?.project?.analysis?.events?.length || 0) > before, eventsBefore, { timeout: 10000 });
      const eventsAfter = await page.evaluate(() => state?.project?.analysis?.events?.length || 0);
      log(`timing events: ${eventsBefore} -> ${eventsAfter}`);
      if (eventsAfter <= eventsBefore) {
        fail(`timing event add did not change event count (${eventsBefore} -> ${eventsAfter})`);
        await screenshot(page, 'fail-timing-event');
        await dumpHtml(page, 'fail-timing-event');
      }
      await screenshot(page, '10-timing-event');
    } else {
      fail('add-timing-event button not found');
      await screenshot(page, 'fail-timing-event-button');
      await dumpHtml(page, 'fail-timing-event-button');
    }

    // Final check: poll for shot detection one more time (analysis may still be running)
    {
      const deadline = Date.now() + 180000; // 3 more minutes
      let finalShots = 0;
      while (Date.now() < deadline) {
        finalShots = await page.evaluate(() => state?.project?.analysis?.shots?.length || 0);
        if (finalShots > 0) break;
        await new Promise(r => setTimeout(r, 5000));
      }
      log(`final state: shots=${finalShots} popups=${browserState.popups} toolsActivated=${TOOL_COUNT}`);
      if (finalShots <= 0) {
        fail('primary analysis produced 0 shots');
        await screenshot(page, 'fail-zero-shots');
        await dumpHtml(page, 'fail-zero-shots');
      }
      browserState.shots = finalShots;
    }
  }

  const browserState = await page.evaluate(() => ({
    shots: (typeof state !== 'undefined' && state?.project?.analysis?.shots?.length) || 0,
    popups: (typeof state !== 'undefined' && state?.project?.popups?.length) || 0,
  }));

  // Save summary
  const result = failures.length === 0 && pageErrors.length === 0 ? 'passed' : 'failed';
  const summary = {
    result,
    totalTools: TOOL_COUNT,
    activatedTools: toolScreenshotDelay - 1,
    shots: browserState.shots,
    popups: browserState.popups,
    consoleLogs: consoleLogs.length,
    pageErrors: pageErrors.length,
    artifacts: artifacts.length,
    pageErrorsList: pageErrors,
    httpErrors,
    failures,
  };
  fs.writeFileSync(path.join(logDir, 'summary.json'), JSON.stringify(summary, null, 2));
  log(`summary saved: ${JSON.stringify(summary)}`);

  if (pageErrors.length > 0) {
    warn(`${pageErrors.length} page errors detected:`);
    for (const e of pageErrors) {
      warn(`  ${e.message}`);
    }
  }

  await context.close();
  await browser.close();
  if (result === 'failed') {
    log('=== E2E test failed ===');
    process.exit(1);
  }
  log('=== E2E test passed ===');
  process.exit(0);
}

main().catch(async err => {
  console.error('PW: FAILED -', err.message);
  console.error(err.stack);
  try {
    const summary = {
      result: 'failed',
      error: err.message,
      stack: err.stack,
      consoleLogs: 0,
      pageErrors: 0,
    };
    fs.writeFileSync(path.join(logDir, 'summary.json'), JSON.stringify(summary, null, 2));
  } catch {}
  process.exit(1);
});
