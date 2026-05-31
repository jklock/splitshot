const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');
const { setTimeout: delay } = require('node:timers/promises');
const { _electron: playwrightElectron } = require('playwright');
const electronBinary = require('electron');

const REPO = path.resolve(__dirname, '..', '..');
const ELECTRON_APP_DIR = path.resolve(REPO, 'electron');
const REPO_PYTHON = path.join(
  REPO,
  '.venv',
  process.platform === 'win32' ? 'Scripts' : 'bin',
  `python${process.platform === 'win32' ? '.exe' : ''}`,
);

function canonicalPath(targetPath) {
  try {
    return fs.realpathSync(targetPath);
  } catch {
    return path.resolve(targetPath);
  }
}

function comparablePath(targetPath) {
  return canonicalPath(targetPath)
    .replaceAll('\\', '/')
    .toLowerCase();
}

function comparableBasename(targetPath) {
  return path.basename(targetPath || '')
    .replaceAll('\\', '/')
    .toLowerCase();
}

function createProjectBundle(name) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'splitshot-electron-smoke-'));
  const projectPath = path.join(root, `${name}.ssproj`);
  const script = [
    'from pathlib import Path',
    'import sys',
    'from splitshot.domain.models import Project',
    'from splitshot.persistence.projects import save_project',
    'save_project(Project(name=sys.argv[2]), Path(sys.argv[1]))',
  ].join('; ');
  const result = spawnSync(REPO_PYTHON, ['-c', script, projectPath, name], {
    cwd: REPO,
    encoding: 'utf8',
  });
  if (result.status !== 0) {
    throw new Error(result.stderr || result.stdout || 'Failed to create project bundle');
  }
  return projectPath;
}

async function waitForProjectPath(page, expectedProjectPath, timeoutMs = 20000) {
  const expectedCanonicalPath = comparablePath(expectedProjectPath);
  const expectedBasename = comparableBasename(expectedProjectPath);
  const deadline = Date.now() + timeoutMs;
  let lastProjectPath = '';
  while (Date.now() < deadline) {
    try {
      const projectPath = await page.evaluate(async () => {
        const response = await fetch('/api/state');
        const state = await response.json();
        return state.project?.path || '';
      });
      lastProjectPath = projectPath || '';
      if (!projectPath) {
        await delay(250);
        continue;
      }
      const actualCanonicalPath = comparablePath(projectPath);
      const actualBasename = comparableBasename(projectPath);
      if (actualCanonicalPath === expectedCanonicalPath || actualBasename === expectedBasename) {
        return;
      }
    } catch {}
    await delay(250);
  }
  throw new Error(`Timed out waiting for project path ${expectedProjectPath}; last seen=${lastProjectPath || '<empty>'}`);
}

async function fetchJsonWithTimeout(page, input, init = {}, { timeoutMs = 1000, retries = 20, retryDelayMs = 200 } = {}) {
  let lastError = null;
  for (let attempt = 0; attempt < retries; attempt += 1) {
    const result = await page.evaluate(async ({ input, init, timeoutMs }) => {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(new Error('timeout')), timeoutMs);
      try {
        const response = await fetch(input, {
          ...(init || {}),
          signal: controller.signal,
        });
        return {
          ok: true,
          status: response.status,
          payload: await response.json(),
        };
      } catch (error) {
        return {
          ok: false,
          error: String(error?.message || error || 'fetch failed'),
        };
      } finally {
        clearTimeout(timer);
      }
    }, { input, init, timeoutMs });
    if (result?.ok) {
      return result.payload;
    }
    lastError = new Error(result?.error || 'fetch failed');
    await delay(retryDelayMs);
  }
  throw lastError || new Error(`Timed out fetching ${input}`);
}

function simulatedExecutablePath() {
  return process.platform === 'win32'
    ? 'C:\\Program Files\\SplitShot\\SplitShot.exe'
    : '/Applications/SplitShot.app/Contents/MacOS/SplitShot';
}

const ELECTRON_TIMEOUT = 120_000;
const TEST_TIMEOUT = 4 * 60_000;

async function closeApp(app) {
  await Promise.race([
    app.close(),
    delay(15_000).then(() => {
      console.error('electron close timed out, forcing exit');
      app.process().kill();
    }),
  ]);
}

async function main() {
  console.log('Creating project bundles...');
  const startupProject = createProjectBundle('startup');
  console.log('  startup bundle created');
  const secondProject = createProjectBundle('second-instance');
  console.log('  second bundle created');
  const protocolProject = createProjectBundle('protocol');
  console.log('  protocol bundle created');
  const dialogPath = path.join(os.tmpdir(), 'splitshot-electron-picked.mp4');
  const practiScoreFixture = path.join(REPO, 'example_data', 'IDPA', 'IDPA.csv');
  const env = {
    ...process.env,
    CI: '1',
    SPLITSHOT_ELECTRON_TEST: '1',
    SPLITSHOT_TEST_PORT: '0',
    SPLITSHOT_ELECTRON_TEST_DIALOG_PATH: dialogPath,
    SPLITSHOT_ELECTRON_TEST_OPEN_EXTERNAL_CAPTURE: '1',
    SPLITSHOT_ELECTRON_PRACTISCORE_HOST_V1: '1',
    SPLITSHOT_ELECTRON_TEST_PRACTISCORE_HOST_FIXTURE: practiScoreFixture,
  };

  console.log('Launching Electron...');
  const electronApp = await playwrightElectron.launch({
    executablePath: electronBinary,
    args: [ELECTRON_APP_DIR, startupProject],
    cwd: ELECTRON_APP_DIR,
    env,
    timeout: ELECTRON_TIMEOUT,
  });
  console.log('  Electron launched');
  console.log('  electron pid:', electronApp.process().pid);

  console.log('Waiting for first window...');
  const window = await electronApp.firstWindow({ timeout: ELECTRON_TIMEOUT });
  console.log('  first window ready');

  try {
    console.log('Waiting for DOM content loaded...');
    await window.waitForLoadState('domcontentloaded', { timeout: ELECTRON_TIMEOUT });
    console.log('  DOM content loaded');

    console.log('Evaluating bridge API...');
    const bridge = await window.evaluate(() => ({
      getVersion: typeof window.splitshot?.getVersion === 'function',
      getPlatform: typeof window.splitshot?.getPlatform === 'function',
      openProjectDialog: typeof window.splitshot?.openProjectDialog === 'function',
      openPathDialog: typeof window.splitshot?.openPathDialog === 'function',
      openExternal: typeof window.splitshot?.openExternal === 'function',
      getPractiScoreHostFeature: typeof window.splitshot?.getPractiScoreHostFeature === 'function',
      getPractiScoreStateOverlay: typeof window.splitshot?.getPractiScoreStateOverlay === 'function',
      startPractiScoreSessionHost: typeof window.splitshot?.startPractiScoreSessionHost === 'function',
      getPractiScoreSessionStatusHost: typeof window.splitshot?.getPractiScoreSessionStatusHost === 'function',
      clearPractiScoreSessionHost: typeof window.splitshot?.clearPractiScoreSessionHost === 'function',
      listPractiScoreMatchesHost: typeof window.splitshot?.listPractiScoreMatchesHost === 'function',
      downloadPractiScoreSelectedMatchHost: typeof window.splitshot?.downloadPractiScoreSelectedMatchHost === 'function',
      updatePractiScoreHostOverlay: typeof window.splitshot?.updatePractiScoreHostOverlay === 'function',
      claimBackendSession: typeof window.splitshot?.claimBackendSession === 'function',
      getBackendSessionMetadata: typeof window.splitshot?.getBackendSessionMetadata === 'function',
      onOpenProject: typeof window.splitshot?.onOpenProject === 'function',
      testSimulateSecondInstance: typeof window.splitshot?.testSimulateSecondInstance === 'function',
      testOpenUrl: typeof window.splitshot?.testOpenUrl === 'function',
      testGetLastOpenExternal: typeof window.splitshot?.testGetLastOpenExternal === 'function',
    }));
    assert.deepEqual(bridge, {
      getVersion: true,
      getPlatform: true,
      openProjectDialog: true,
      openPathDialog: true,
      openExternal: true,
      getPractiScoreHostFeature: true,
      getPractiScoreStateOverlay: true,
      startPractiScoreSessionHost: true,
      getPractiScoreSessionStatusHost: true,
      clearPractiScoreSessionHost: true,
      listPractiScoreMatchesHost: true,
      downloadPractiScoreSelectedMatchHost: true,
      updatePractiScoreHostOverlay: true,
      claimBackendSession: true,
      getBackendSessionMetadata: true,
      onOpenProject: true,
      testSimulateSecondInstance: true,
      testOpenUrl: true,
      testGetLastOpenExternal: true,
    });
    console.log('  bridge API OK');

    console.log('Waiting for desktop route bridge install...');
    await window.waitForFunction(
      () => window.__splitshotDesktopRouteBridgeInstalled === true,
      null,
      { timeout: ELECTRON_TIMEOUT },
    );
    console.log('  desktop route bridge installed');

    console.log('Reading backend session metadata...');
    const backendSession = await window.evaluate(async () => {
      const claim = await window.splitshot.claimBackendSession();
      const metadata = await window.splitshot.getBackendSessionMetadata();
      return { claim, metadata };
    });
    assert.equal(backendSession.claim.session_id, backendSession.metadata.session_id);
    assert.equal(backendSession.claim.base_url, backendSession.metadata.base_url);
    assert.equal(backendSession.claim.health_path, '/api/health');
    assert.equal(backendSession.claim.events_path, '/api/events');
    assert.match(backendSession.claim.base_url, /^http:\/\/127\.0\.0\.1:\d+$/);
    assert.equal(Object.hasOwn(backendSession.claim, 'bootstrap_token'), false);
    console.log('  backend session metadata OK');

    console.log('Verifying Electron-owned path dialog route...');
    const dialogPayload = await fetchJsonWithTimeout(window, '/api/dialog/path', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind: 'primary', current: '', home: '' }),
      }, { timeoutMs: 1000, retries: 30, retryDelayMs: 200 });
    assert.equal(dialogPayload.path, dialogPath);
    console.log('  Electron-owned path dialog route OK');

    console.log('Verifying Electron-owned external open route...');
    const dashboardPayload = await fetchJsonWithTimeout(window, '/api/practiscore/dashboard/open', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      }, { timeoutMs: 1000, retries: 30, retryDelayMs: 200 });
    assert.equal(dashboardPayload.url, 'https://practiscore.com/dashboard/home');
    const lastExternalUrl = await window.evaluate(() => window.splitshot.testGetLastOpenExternal());
    assert.equal(lastExternalUrl, 'https://practiscore.com/dashboard/home');
    console.log('  Electron-owned external open route OK');

    console.log('Waiting for startup project...');
    await waitForProjectPath(window, startupProject);
    console.log('  startup project loaded');

    console.log('Checking PractiScore host feature state...');
    const practiScoreFeature = await window.evaluate(async () => window.splitshot.getPractiScoreHostFeature());
    assert.equal(practiScoreFeature.enabled, true);
    console.log('  PractiScore host feature enabled');

    console.log('Starting PractiScore desktop host session...');
    const practiScoreSession = await fetchJsonWithTimeout(window, '/api/practiscore/session/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      }, { timeoutMs: 1000, retries: 30, retryDelayMs: 200 });
    assert.equal(practiScoreSession.state, 'authenticated_ready');
    console.log('  PractiScore desktop host session ready');

    console.log('Listing PractiScore remote matches through desktop host...');
    const matchesPayload = await fetchJsonWithTimeout(window, '/api/practiscore/matches', {}, {
      timeoutMs: 1000,
      retries: 30,
      retryDelayMs: 200,
    });
    assert.equal(matchesPayload.practiscore_session.state, 'authenticated_ready');
    assert.equal(matchesPayload.practiscore_sync.state, 'match_list_ready');
    assert.equal(matchesPayload.matches.length, 1);
    assert.equal(matchesPayload.matches[0].remote_id, 'match-electron-200');
    console.log('  PractiScore remote match list ready');

    console.log('Importing selected PractiScore remote match through desktop host...');
    const syncPayload = await fetchJsonWithTimeout(window, '/api/practiscore/sync/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ remote_id: 'match-electron-200' }),
      }, { timeoutMs: 1000, retries: 30, retryDelayMs: 200 });
    assert.equal(syncPayload.practiscore_sync.state, 'success');
    assert.equal(syncPayload.practiscore_sync.selected_remote_id, 'match-electron-200');
    assert.equal(syncPayload.practiscore_options.has_source, true);
    assert.equal(syncPayload.practiscore_options.source_name, 'IDPA.csv');
    console.log('  PractiScore remote import succeeded');

    console.log('Clearing PractiScore desktop host session...');
    const clearedSession = await fetchJsonWithTimeout(window, '/api/practiscore/session/clear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      }, { timeoutMs: 1000, retries: 30, retryDelayMs: 200 });
    assert.equal(clearedSession.state, 'not_authenticated');
    const stateAfterClear = await fetchJsonWithTimeout(window, '/api/state', {}, {
      timeoutMs: 1000,
      retries: 30,
      retryDelayMs: 200,
    });
    assert.equal(stateAfterClear.practiscore_session.state, 'not_authenticated');
    assert.equal(stateAfterClear.practiscore_sync.state, 'idle');
    console.log('  PractiScore desktop host session cleared');

    console.log('Simulating second instance...');
    const queued = await window.evaluate(({ executablePath, targetPath }) => (
      window.splitshot.testSimulateSecondInstance([executablePath, targetPath])
    ), {
      executablePath: simulatedExecutablePath(),
      targetPath: secondProject,
    });
    assert.equal(queued, true);
    await waitForProjectPath(window, secondProject);
    console.log('  second instance handled');

    console.log('Simulating protocol URL...');
    const injected = await window.evaluate((targetUrl) => window.splitshot.testOpenUrl(targetUrl), `splitshot://open?path=${encodeURIComponent(protocolProject)}`);
    assert.equal(injected, true);
    await waitForProjectPath(window, protocolProject);
    console.log('  protocol URL handled');
  } finally {
    console.log('Closing Electron...');
    await closeApp(electronApp);
    console.log('  Electron closed');
  }
}

const timer = setTimeout(() => {
  console.error('FATAL: test timed out');
  process.exit(1);
}, TEST_TIMEOUT);

main()
  .then(() => {
    clearTimeout(timer);
    console.log('electron smoke ok');
    process.exit(0);
  })
  .catch((error) => {
    clearTimeout(timer);
    console.error(error);
    process.exit(1);
  });
