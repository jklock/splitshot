const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');

const {
  createLaunchIntentRouter,
  launchIntentFromArgv,
  launchIntentFromUrl,
  normalizeProjectPath,
} = require('../launch-intent');

function makeProjectBundle(name) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'splitshot-launch-intent-'));
  const projectPath = path.join(root, `${name}.ssproj`);
  fs.mkdirSync(projectPath, { recursive: true });
  fs.writeFileSync(path.join(projectPath, 'project.json'), '{}', 'utf8');
  return projectPath;
}

test('normalizeProjectPath accepts .ssproj bundles and project.json paths', () => {
  const projectPath = makeProjectBundle('alpha');
  assert.equal(normalizeProjectPath(projectPath), projectPath);
  assert.equal(normalizeProjectPath(path.join(projectPath, 'project.json')), projectPath);
});

test('launchIntentFromArgv ignores noise and extracts project argv', () => {
  const projectPath = makeProjectBundle('beta');
  const intent = launchIntentFromArgv([
    '/Applications/SplitShot.app/Contents/MacOS/SplitShot',
    '--inspect=9229',
    projectPath,
  ]);
  assert.deepEqual(intent, {
    kind: 'open-project',
    projectPath,
    source: 'argv',
  });
});

test('launchIntentFromUrl accepts valid splitshot deep links', () => {
  const projectPath = makeProjectBundle('gamma');
  const intent = launchIntentFromUrl(`splitshot://open?path=${encodeURIComponent(projectPath)}`);
  assert.deepEqual(intent, {
    kind: 'open-project',
    projectPath,
    source: 'protocol',
  });
});

test('launchIntentFromUrl rejects malformed or unsupported deep links', () => {
  assert.equal(launchIntentFromUrl('splitshot://noop?path=/tmp/project.ssproj'), null);
  assert.equal(launchIntentFromUrl('not-a-url'), null);
  assert.equal(launchIntentFromUrl('splitshot://open?path=/tmp/missing.ssproj'), null);
});

test('launch intent router drains only after backend and window are ready', () => {
  const projectPath = makeProjectBundle('delta');
  const received = [];
  const router = createLaunchIntentRouter((intent) => {
    received.push(intent.projectPath);
    return true;
  });

  const queued = router.queueIntent({
    kind: 'open-project',
    projectPath,
    source: 'test',
  });
  assert.equal(queued, true);
  assert.deepEqual(received, []);
  assert.equal(router.pendingCount(), 1);

  router.setBackendReady(true);
  assert.deepEqual(received, []);
  assert.equal(router.pendingCount(), 1);

  router.setWindowReady(true);
  assert.deepEqual(received, [projectPath]);
  assert.equal(router.pendingCount(), 0);
});
