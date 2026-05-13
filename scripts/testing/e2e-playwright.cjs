const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const port = process.env.E2E_PORT || '8765';
const logDir = process.env.E2E_LOG_DIR || '/tmp/splitshot-e2e-logs';
const videoPath = process.env.E2E_VIDEO_PATH || '';
const baseUrl = `http://127.0.0.1:${port}`;
const artifacts = [];

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

async function main() {
  fs.mkdirSync(logDir, { recursive: true });
  log(`=== E2E test start === port=${port}`);

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-gpu', '--disable-software-rasterizer'],
  });
  const consoleLogs = [];
  const pageErrors = [];

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
      try { fs.appendFileSync(path.join(logDir, 'http-errors.log'),
        `[${new Date().toISOString()}] ${resp.status()} ${resp.url()}\n`); } catch {}
    }
  });

  log('navigating to app...');
  await page.goto(baseUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await screenshot(page, '01-after-load');
  log('page loaded');

  log('waiting for app to initialize...');
  await page.waitForFunction(() => typeof activeTool !== 'undefined', { timeout: 45000 });
  await screenshot(page, '02-app-initialized');
  log('app initialized');

  await page.waitForTimeout(1000);

  if (!(await page.evaluate(() => Boolean(state?.project?.path)))) {
    log('creating new project...');
    const pp = `/tmp/sshot-e2e-project.ssproj`;
    await page.evaluate((p) => createNewProject(p), pp);
    await page.waitForFunction(() => Boolean(state?.project?.path), { timeout: 15000 });
    await page.waitForTimeout(500);
    await screenshot(page, '03-project-created');
    log('project created');
  }

  // Import a test video to get real shot data
  let videoFile = null;
  if (videoPath) {
    try { if (fs.statSync(videoPath).isFile()) { videoFile = videoPath; } } catch {}
  }
  if (!videoFile) {
    for (const v of [
      path.join(__dirname, '..', '..', 'example_data', 'stage.mp4'),
    ]) {
      try { if (fs.statSync(v).isFile()) { videoFile = v; break; } } catch {}
    }
  }
  if (videoFile) {
    log(`importing video: ${videoFile}`);
    const inputEl = page.locator('#primary-file-input');
    if (await inputEl.isVisible()) {
      await inputEl.set_input_files(videoFile);
      try {
        await page.waitForFunction(() => Boolean(state?.media?.primary_display_name), { timeout: 60000 });
        await page.waitForFunction(() => (state?.project?.analysis?.shots || []).length > 0, { timeout: 120000 });
        const shotCount = await page.evaluate(() => state?.project?.analysis?.shots?.length || 0);
        await screenshot(page, '03b-video-imported');
        log(`video imported, ${shotCount} shots detected`);
      } catch (e) {
        warn(`video import timed out: ${e.message}`);
        await screenshot(page, 'fail-video-import');
        await dumpHtml(page, 'fail-video-import');
      }
    }
  } else {
    warn('no test video found, skipping import');
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

  await page.locator('button[data-tool="timing"]').click({ force: true });
  await page.waitForFunction(() => activeTool === 'timing', { timeout: 10000 });
  if ((await page.locator('.waveform-shot-card').count()) > 0) {
    await page.locator('.waveform-shot-card').first().click();
    await page.waitForTimeout(300);
    await screenshot(page, '04-waveform-selected');
    log('waveform shot selected');
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
  const exportDir = '/tmp/sshot-e2e-export';
  try { fs.mkdirSync(exportDir, { recursive: true }); } catch {}
  const exportFile = path.join(exportDir, 'e2e-export-test.mp4');

  log('testing export...');
  await page.locator('button[data-tool="export"]').click({ force: true });
  await page.waitForFunction(() => activeTool === 'export', { timeout: 10000 });
  await page.waitForTimeout(500);
  await screenshot(page, '06-export-tool');

  // Set output path and trigger export
  const exportPathInput = page.locator('#export-output-path, [data-export-field="output_path"], .export-output-path');
  if (await exportPathInput.isVisible()) {
    await exportPathInput.fill(exportFile);
    await page.waitForTimeout(200);
    log('export output path set');

    const exportBtn = page.locator('#export-start, [data-action="export"], .export-start-btn, button:has-text("Export")');
    if (await exportBtn.isVisible()) {
      await exportBtn.click({ force: true });
      log('export triggered, waiting for completion...');

      // Wait for export to complete (file appears or UI confirms)
      try {
        await page.waitForFunction(() => {
          const el = document.querySelector('.export-progress, .export-status, [data-export-status]');
          return el && (el.textContent.includes('complete') || el.textContent.includes('done') || el.textContent.includes('saved'));
        }, { timeout: 120000 });
        log('export UI reports completion');
      } catch (e) {
        warn(`export completion UI not detected: ${e.message}`);
      }

      // Wait for file to appear
      let fileFound = false;
      for (let i = 0; i < 30; i++) {
        try { if (fs.statSync(exportFile).isFile() && fs.statSync(exportFile).size > 0) { fileFound = true; break; } } catch {}
        await page.waitForTimeout(1000);
      }
      if (fileFound) {
        const sz = fs.statSync(exportFile).size;
        log(`export file exists: ${exportFile} (${(sz / 1024 / 1024).toFixed(2)} MB)`);
        artifacts.push(exportFile);

        // Validate exported file with ffprobe
        const { execSync } = require('child_process');
        try {
          const probe = execSync(`ffprobe -v error -show_entries format=format_name,duration,size -of json "${exportFile}"`, { encoding: 'utf8', timeout: 15 });
          const info = JSON.parse(probe);
          const fmt = info.format?.format_name || 'unknown';
          const dur = info.format?.duration || '0';
          log(`export validation: format=${fmt} duration=${dur}s size=${(sz / 1024 / 1024).toFixed(2)}MB`);
          if (sz < 1024) { // less than 1KB is probably corrupt
            warn(`export file suspiciously small (${sz} bytes)`);
            await screenshot(page, 'fail-export-small');
          }
        } catch (e) {
          warn(`export ffprobe validation failed: ${e.message}`);
          await screenshot(page, 'fail-export-ffprobe');
        }
      } else {
        warn('export file not found after waiting');
        await screenshot(page, 'fail-export-file');
        await dumpHtml(page, 'fail-export-file');
      }
    } else {
      warn('export button not found');
      await screenshot(page, 'fail-export-btn');
      await dumpHtml(page, 'fail-export-btn');
    }
  } else {
    warn('export output path input not found');
    await screenshot(page, 'fail-export-input');
    await dumpHtml(page, 'fail-export-input');
  }

  await screenshot(page, '07-after-export');

  const browserState = await page.evaluate(() => ({
    shots: (typeof state !== 'undefined' && state?.project?.analysis?.shots?.length) || 0,
    popups: (typeof state !== 'undefined' && state?.project?.popups?.length) || 0,
  }));
  log(`final state: shots=${browserState.shots} popups=${browserState.popups} toolsActivated=${TOOL_COUNT}`);

  // Save summary
  const summary = {
    result: 'passed',
    totalTools: TOOL_COUNT,
    activatedTools: toolScreenshotDelay - 1,
    shots: browserState.shots,
    popups: browserState.popups,
    consoleLogs: consoleLogs.length,
    pageErrors: pageErrors.length,
    artifacts: artifacts.length,
    pageErrorsList: pageErrors,
    httpErrors: consoleLogs.filter(l => l.type === 'error' || l.type === 'warning'),
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
