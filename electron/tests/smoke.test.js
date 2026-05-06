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

function canonicalPath(targetPath) {
  try {
    return fs.realpathSync(targetPath);
  } catch {
    return path.resolve(targetPath);
  }
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
  const result = spawnSync('uv', ['run', 'python', '-c', script, projectPath, name], {
    cwd: REPO,
    encoding: 'utf8',
  });
  if (result.status !== 0) {
    throw new Error(result.stderr || result.stdout || 'Failed to create project bundle');
  }
  return projectPath;
}

async function waitForProjectPath(page, expectedProjectPath, timeoutMs = 20000) {
  const expectedCanonicalPath = canonicalPath(expectedProjectPath);
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const projectPath = await page.evaluate(async () => {
        const response = await fetch('/api/state');
        const state = await response.json();
        return state.project?.path || '';
      });
      if (projectPath && canonicalPath(projectPath) === expectedCanonicalPath) {
        return;
      }
    } catch {}
    await delay(250);
  }
  throw new Error(`Timed out waiting for project path ${expectedProjectPath}`);
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
  const env = {
    ...process.env,
    CI: '1',
    SPLITSHOT_ELECTRON_TEST: '1',
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
      onOpenProject: typeof window.splitshot?.onOpenProject === 'function',
      testSimulateSecondInstance: typeof window.splitshot?.testSimulateSecondInstance === 'function',
      testOpenUrl: typeof window.splitshot?.testOpenUrl === 'function',
    }));
    assert.deepEqual(bridge, {
      getVersion: true,
      getPlatform: true,
      openProjectDialog: true,
      onOpenProject: true,
      testSimulateSecondInstance: true,
      testOpenUrl: true,
    });
    console.log('  bridge API OK');

    console.log('Waiting for startup project...');
    await waitForProjectPath(window, startupProject);
    console.log('  startup project loaded');

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
