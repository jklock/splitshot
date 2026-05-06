const fs = require('fs');
const os = require('os');
const path = require('path');

const DEEP_LINK_SCHEME = 'splitshot:';
const PROJECT_FILENAME = 'project.json';
const PROJECT_SUFFIX = '.ssproj';

function expandUserPath(value) {
  if (typeof value !== 'string') return '';
  if (value === '~') return os.homedir();
  if (value.startsWith(`~${path.sep}`)) {
    return path.join(os.homedir(), value.slice(2));
  }
  if (path.sep === '\\' && value.startsWith('~/')) {
    return path.join(os.homedir(), value.slice(2).replace(/\//g, '\\'));
  }
  return value;
}

function normalizeProjectPath(candidatePath) {
  if (typeof candidatePath !== 'string') return null;
  const trimmed = candidatePath.trim();
  if (!trimmed) return null;
  const expanded = expandUserPath(trimmed);
  const resolved = path.resolve(expanded);
  const basename = path.basename(resolved).toLowerCase();
  const projectPath = basename === PROJECT_FILENAME ? path.dirname(resolved) : resolved;
  if (path.extname(projectPath).toLowerCase() !== PROJECT_SUFFIX) {
    return null;
  }
  if (!fs.existsSync(projectPath)) {
    return null;
  }
  return projectPath;
}

function createProjectIntent(projectPath, source) {
  const normalizedProjectPath = normalizeProjectPath(projectPath);
  if (!normalizedProjectPath) return null;
  return {
    kind: 'open-project',
    projectPath: normalizedProjectPath,
    source,
  };
}

function launchIntentFromUrl(targetUrl) {
  if (typeof targetUrl !== 'string' || !targetUrl.trim()) return null;
  let parsed;
  try {
    parsed = new URL(targetUrl);
  } catch {
    return null;
  }
  if (parsed.protocol !== DEEP_LINK_SCHEME) return null;
  const host = parsed.hostname.toLowerCase();
  const pathname = parsed.pathname.replace(/^\/+/, '').toLowerCase();
  if (!(host === 'open' || pathname === 'open')) {
    return null;
  }
  return createProjectIntent(parsed.searchParams.get('path'), 'protocol');
}

function launchIntentFromArgv(argv) {
  if (!Array.isArray(argv)) return null;
  for (const candidate of argv) {
    if (typeof candidate !== 'string') continue;
    if (candidate.startsWith(DEEP_LINK_SCHEME)) {
      const intent = launchIntentFromUrl(candidate);
      if (intent) return intent;
      continue;
    }
    const intent = createProjectIntent(candidate, 'argv');
    if (intent) return intent;
  }
  return null;
}

function createLaunchIntentRouter(dispatchIntent) {
  if (typeof dispatchIntent !== 'function') {
    throw new TypeError('dispatchIntent must be a function');
  }
  let backendReady = false;
  let windowReady = false;
  const queue = [];

  function drain() {
    if (!(backendReady && windowReady)) return;
    while (queue.length) {
      const intent = queue[0];
      if (!dispatchIntent(intent)) return;
      queue.shift();
    }
  }

  return {
    queueIntent(intent) {
      if (!intent) return false;
      queue.push(intent);
      drain();
      return true;
    },
    setBackendReady(ready) {
      backendReady = Boolean(ready);
      drain();
    },
    setWindowReady(ready) {
      windowReady = Boolean(ready);
      drain();
    },
    isBackendReady() {
      return backendReady;
    },
    pendingCount() {
      return queue.length;
    },
  };
}

module.exports = {
  createLaunchIntentRouter,
  createProjectIntent,
  launchIntentFromArgv,
  launchIntentFromUrl,
  normalizeProjectPath,
};
