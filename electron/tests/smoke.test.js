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

const ELECTRON_LAUNCH_TIMEOUT = 120_000;

async function main() {
  const startupProject = createProjectBundle('startup');
  const secondProject = createProjectBundle('second-instance');
  const protocolProject = createProjectBundle('protocol');
  const env = {
    ...process.env,
    CI: '1',
    SPLITSHOT_ELECTRON_TEST: '1',
  };

  const electronApp = await playwrightElectron.launch({
    executablePath: electronBinary,
    args: ['--no-sandbox', '--disable-gpu', ELECTRON_APP_DIR, startupProject],
    cwd: ELECTRON_APP_DIR,
    env,
    timeout: ELECTRON_LAUNCH_TIMEOUT,
  });

  const window = await electronApp.firstWindow({ timeout: ELECTRON_LAUNCH_TIMEOUT });
  try {
    await window.waitForLoadState('domcontentloaded');
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

    await waitForProjectPath(window, startupProject);

    const queued = await window.evaluate((targetPath) => (
      window.splitshot.testSimulateSecondInstance([
        '/Applications/SplitShot.app/Contents/MacOS/SplitShot',
        targetPath,
      ])
    ), secondProject);
    assert.equal(queued, true);
    await waitForProjectPath(window, secondProject);

    const injected = await window.evaluate((targetUrl) => window.splitshot.testOpenUrl(targetUrl), `splitshot://open?path=${encodeURIComponent(protocolProject)}`);
    assert.equal(injected, true);
    await waitForProjectPath(window, protocolProject);
  } finally {
    await electronApp.close();
  }
}

main()
  .then(() => {
    console.log('electron smoke ok');
    process.exit(0);
  })
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
