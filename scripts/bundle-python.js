const { execFileSync, execSync } = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const BUNDLE_DIR = path.join(ROOT, 'electron', 'bundle');
const VENV_DIR = path.join(BUNDLE_DIR, '.venv');
const WINDOWS_PYTHON_DIR = path.join(BUNDLE_DIR, 'python');
const SRC_DIR = path.join(ROOT, 'src');
const BUNDLE_SRC_DIR = path.join(BUNDLE_DIR, 'src');
const BUNDLE_MANIFEST_PATH = path.join(BUNDLE_DIR, 'runtime-manifest.json');
const ELECTRON_PACKAGE_PATH = path.join(ROOT, 'electron', 'package.json');
const ELECTRON_PACKAGE_LOCK_PATH = path.join(ROOT, 'electron', 'package-lock.json');
const UV_LOCK_PATH = path.join(ROOT, 'uv.lock');
const PYPROJECT_PATH = path.join(ROOT, 'pyproject.toml');

function run(cmd, opts = {}) {
  console.log(`[bundle] ${cmd}`);
  execSync(cmd, { stdio: 'inherit', cwd: ROOT, ...opts });
}

function runFile(bin, args, opts = {}) {
  console.log(`[bundle] ${bin} ${args.join(' ')}`);
  execFileSync(bin, args, { stdio: 'inherit', cwd: ROOT, ...opts });
}

function repoPythonCommand(args, opts = {}) {
  runFile('uv', ['run', 'python', ...args], opts);
}

function sleepSync(milliseconds) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, milliseconds);
}

function rmrf(target) {
  if (!fs.existsSync(target)) {
    return;
  }

  let lastError = null;
  for (let attempt = 1; attempt <= 5; attempt += 1) {
    try {
      fs.rmSync(target, {
        recursive: true,
        force: true,
        maxRetries: 20,
        retryDelay: 100,
      });
      return;
    } catch (error) {
      lastError = error;
      if (!['EBUSY', 'ENOTEMPTY', 'EPERM'].includes(error?.code || '')) {
        throw error;
      }
      if (fs.existsSync(target)) {
        try {
          const stats = fs.lstatSync(target);
          if (stats.isDirectory()) {
            for (const entry of fs.readdirSync(target)) {
              rmrf(path.join(target, entry));
            }
          }
        } catch {
          // Best-effort cleanup; allow the next retry to re-check the path.
        }
      }
      if (attempt < 5) {
        sleepSync(attempt * 200);
      }
    }
  }

  if (lastError) {
    throw lastError;
  }
}

function getPythonVersion() {
  const result = execSync('uv run python --version', { encoding: 'utf8', cwd: ROOT });
  const match = result.trim().match(/^Python (\d+\.\d+)/);
  if (!match) throw new Error(`Could not detect Python version from: ${result}`);
  return match[1];
}

function getPythonBasePrefix() {
  return execSync('uv run python -c "import sys; print(sys.base_prefix)"', {
    encoding: 'utf8',
    cwd: ROOT,
  }).trim();
}

function getPythonBinDir(venvDir, pythonVersion) {
  const isWin = process.platform === 'win32';
  const binDir = isWin ? 'Scripts' : 'bin';
  const pythonBin = path.join(venvDir, binDir, `python${isWin ? '.exe' : ''}`);
  if (!fs.existsSync(pythonBin)) return null;
  return path.dirname(pythonBin);
}

function pythonExecutableForVenv(venvDir) {
  const binDir = getPythonBinDir(venvDir);
  if (!binDir) throw new Error(`Python binary not found in venv at ${venvDir}`);
  return path.join(binDir, `python${process.platform === 'win32' ? '.exe' : ''}`);
}

function bundledPythonExecutable(pythonVersion) {
  if (process.platform === 'win32') {
    return path.join(WINDOWS_PYTHON_DIR, 'python.exe');
  }
  return pythonExecutableForVenv(VENV_DIR);
}

function bundledSitePackagesDir(pythonVersion) {
  if (process.platform === 'win32') {
    return path.join(WINDOWS_PYTHON_DIR, 'Lib', 'site-packages');
  }
  return path.join(VENV_DIR, 'lib', `python${pythonVersion}`, 'site-packages');
}

function bundledPosixPythonHome() {
  return VENV_DIR;
}

function resolveSymlinks(binDir) {
  if (process.platform === 'win32') return;
  for (const name of fs.readdirSync(binDir)) {
    const p = path.join(binDir, name);
    let stat;
    try { stat = fs.lstatSync(p); } catch { continue; }
    if (stat.isSymbolicLink()) {
      const real = fs.realpathSync(p);
      rmrf(p);
      fs.copyFileSync(real, p);
      fs.chmodSync(p, 0o755);
      console.log(`[bundle] resolved symlink: ${name}`);
    }
  }
}

function findTool(tool) {
  const executable = process.platform === 'win32' ? `${tool}.exe` : tool;
  const cmd = process.platform === 'win32' ? `where ${executable} 2>nul` : `which ${executable} 2>/dev/null`;
  try {
    const result = execSync(cmd, { encoding: 'utf8', cwd: ROOT }).trim().split(/\r?\n/)[0];
    return result || '';
  } catch {
    return '';
  }
}

function downloadFile(url, target) {
  fs.mkdirSync(path.dirname(target), { recursive: true });
  const curl = process.platform === 'win32' ? 'curl.exe' : 'curl';
  runFile(curl, ['-LfsS', '-o', target, url]);
}

function extractZip(archive, destination) {
  fs.mkdirSync(destination, { recursive: true });
  repoPythonCommand([
    '-c',
    'import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])',
    archive,
    destination,
  ]);
}

function extractTarXz(archive, destination) {
  fs.mkdirSync(destination, { recursive: true });
  runFile('tar', ['-xf', archive, '-C', destination]);
}

function walkFiles(rootDir) {
  const files = [];
  const stack = [rootDir];
  while (stack.length > 0) {
    const current = stack.pop();
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) {
        stack.push(full);
      } else if (entry.isFile()) {
        files.push(full);
      }
    }
  }
  return files;
}

function readJsonFile(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function sha256File(filePath) {
  const digest = crypto.createHash('sha256');
  const data = fs.readFileSync(filePath);
  digest.update(data);
  return digest.digest('hex');
}

function normalizeRelativePath(value) {
  return String(value || '').replace(/\\/g, '/');
}

function relativeRepoPath(filePath) {
  return normalizeRelativePath(path.relative(ROOT, filePath));
}

function relativeBundlePath(filePath) {
  return normalizeRelativePath(path.relative(BUNDLE_DIR, filePath));
}

function fileDigestRecord(filePath, relativePath) {
  const stats = fs.statSync(filePath);
  return {
    path: normalizeRelativePath(relativePath),
    size: stats.size,
    sha256: sha256File(filePath),
  };
}

function hashStrings(values) {
  const digest = crypto.createHash('sha256');
  for (const value of values) {
    digest.update(String(value));
    digest.update('\n');
  }
  return digest.digest('hex');
}

function directoryFingerprint(rootDir) {
  const files = walkFiles(rootDir).sort((left, right) => left.localeCompare(right));
  const entries = files.map((filePath) => fileDigestRecord(filePath, path.relative(rootDir, filePath)));
  return {
    path: relativeBundlePath(rootDir),
    file_count: entries.length,
    total_bytes: entries.reduce((sum, entry) => sum + entry.size, 0),
    sha256: hashStrings(entries.map((entry) => `${entry.path}\t${entry.size}\t${entry.sha256}`)),
  };
}

function findExtractedTool(rootDir, toolName) {
  const matches = walkFiles(rootDir).filter((file) => path.basename(file) === toolName);
  if (matches.length === 0) {
    throw new Error(`Could not find ${toolName} under extracted archive ${rootDir}`);
  }
  return matches[0];
}

function portableMediaManifest() {
  if (process.platform === 'win32') {
    return {
      archiveType: 'zip',
      archiveUrl: 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip',
      tools: {
        ffmpeg: 'ffmpeg.exe',
        ffprobe: 'ffprobe.exe',
      },
    };
  }
  const arch = process.arch === 'arm64' ? 'arm64' : 'amd64';
  const osName = process.platform === 'darwin' ? 'macos' : 'linux';
  return {
    archiveType: 'zip',
    tools: {
      ffmpeg: `${osName}/${arch}/release/ffmpeg.zip`,
      ffprobe: `${osName}/${arch}/release/ffprobe.zip`,
    },
  };
}

function verifyBundledMediaTool(toolPath) {
  runFile(toolPath, ['-version']);
  if (process.platform === 'darwin') {
    const linked = execFileSync('otool', ['-L', toolPath], { encoding: 'utf8', cwd: ROOT });
    for (const forbidden of ['/opt/homebrew/', '/usr/local/Cellar/', '/usr/local/opt/']) {
      if (linked.includes(forbidden)) {
        throw new Error(`Bundled media tool depends on host-managed library path: ${forbidden} in ${toolPath}`);
      }
    }
    return;
  }
  if (process.platform === 'linux') {
    const linked = execFileSync('ldd', [toolPath], { encoding: 'utf8', cwd: ROOT });
    if (linked.includes('not found')) {
      throw new Error(`Bundled media tool has unresolved shared libraries: ${toolPath}\n${linked}`);
    }
  }
}

function copyTool(sourcePath, destinationPath) {
  const real = fs.realpathSync(sourcePath);
  fs.copyFileSync(real, destinationPath);
  fs.chmodSync(destinationPath, 0o755);
  verifyBundledMediaTool(destinationPath);
}

function copyDirectory(sourcePath, destinationPath) {
  rmrf(destinationPath);
  if (process.platform === 'darwin') {
    runFile('ditto', [sourcePath, destinationPath]);
    return;
  }
  fs.cpSync(sourcePath, destinationPath, { recursive: true, force: true });
}

function fetchPortableMediaTools(platformDir) {
  const cacheDir = path.join(os.tmpdir(), 'splitshot-vendored-ffmpeg', `${process.platform}-${process.arch}`);
  rmrf(cacheDir);
  fs.mkdirSync(cacheDir, { recursive: true });
  const manifest = portableMediaManifest();
  if (process.platform === 'win32') {
    const archive = path.join(cacheDir, 'ffmpeg-release-essentials.zip');
    const extracted = path.join(cacheDir, 'extracted');
    downloadFile(manifest.archiveUrl, archive);
    extractZip(archive, extracted);
    for (const [tool, executable] of Object.entries(manifest.tools)) {
      const source = findExtractedTool(extracted, executable);
      const dest = path.join(platformDir, executable);
      copyTool(source, dest);
      console.log(`[bundle] bundled ${tool}: ${source} -> ${dest}`);
    }
    return;
  }

  for (const [tool, relativeUrl] of Object.entries(manifest.tools)) {
    const archive = path.join(cacheDir, `${tool}.zip`);
    const extracted = path.join(cacheDir, tool);
    const url = `https://ffmpeg.martin-riedl.de/redirect/latest/${relativeUrl}`;
    downloadFile(url, archive);
    extractZip(archive, extracted);
    const source = findExtractedTool(extracted, tool);
    const dest = path.join(platformDir, tool);
    copyTool(source, dest);
    console.log(`[bundle] bundled ${tool}: ${source} -> ${dest}`);
  }
}

function bundledFfmpegDir() {
  const ffmpegDir = path.join(BUNDLE_SRC_DIR, 'splitshot', 'resources', 'ffmpeg');
  const platform = process.platform === 'darwin' ? 'macos' : process.platform === 'win32' ? 'windows' : 'linux';
  return path.join(ffmpegDir, platform);
}

function prependPathEntries(env, entries) {
  const separator = process.platform === 'win32' ? ';' : ':';
  const existing = (env.PATH || '').split(separator).filter(Boolean);
  env.PATH = [...entries.filter(Boolean), ...existing].join(separator);
}

function buildBundledPythonEnv(pythonVersion) {
  const env = {
    ...process.env,
    PYTHONPATH: BUNDLE_SRC_DIR,
    PYTHONNOUSERSITE: '1',
    PYTHONDONTWRITEBYTECODE: '1',
  };
  prependPathEntries(env, [bundledFfmpegDir()]);
  if (process.platform === 'win32') {
    env.PYTHONHOME = WINDOWS_PYTHON_DIR;
    env.PYTHONPATH += ';' + bundledSitePackagesDir(pythonVersion);
    prependPathEntries(env, [WINDOWS_PYTHON_DIR, path.join(WINDOWS_PYTHON_DIR, 'Scripts')]);
  } else {
    const venvHome = bundledPosixPythonHome();
    env.PYTHONHOME = venvHome;
    env.PYTHONPATH += ':' + bundledSitePackagesDir(pythonVersion);
  }
  return env;
}

function createBundledPosixVenv(venvDir, pythonVersion) {
  // Keep the bundle venv unseeded. The bundle flow installs project deps via
  // `uv pip --python ...` immediately afterward, and `--seed` has been
  // failing on shared-volume worktrees while resolving the bundled pip entry
  // points.
  run(`uv venv "${venvDir}" --python ${pythonVersion}`);
  return pythonExecutableForVenv(venvDir);
}

function stageBundledPosixVenv(pythonVersion) {
  const stageRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'splitshot-bundle-venv-'));
  const stageVenvDir = path.join(stageRoot, '.venv');
  console.log(`[bundle] staging POSIX venv in local temp dir: ${stageVenvDir}`);
  try {
    const pythonExe = createBundledPosixVenv(stageVenvDir, pythonVersion);
    run(`uv pip install --python "${pythonExe}" --link-mode copy "."`);
    console.log(`[bundle] copying staged POSIX venv into bundle: ${stageVenvDir} -> ${VENV_DIR}`);
    copyDirectory(stageVenvDir, VENV_DIR);
    console.log(`[bundle] copied staged POSIX venv into bundle: ${VENV_DIR}`);
  } finally {
    rmrf(stageRoot);
  }
  return bundledPythonExecutable(pythonVersion);
}

function installBundledPosixProject(pythonVersion) {
  const maxAttempts = 2;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    rmrf(VENV_DIR);
    try {
      return stageBundledPosixVenv(pythonVersion);
    } catch (error) {
      if (attempt >= maxAttempts) {
        throw error;
      }
      console.warn(
        `[bundle] uv pip install failed on attempt ${attempt}/${maxAttempts}; recreating ${VENV_DIR} and retrying once`,
      );
    }
  }
  throw new Error('Bundled POSIX dependency installation did not complete.');
}

function resolvedNodeToolVersions() {
  const packageJson = readJsonFile(ELECTRON_PACKAGE_PATH);
  const packageLock = readJsonFile(ELECTRON_PACKAGE_LOCK_PATH);
  const toolNames = ['electron', 'electron-builder', 'playwright'];
  return Object.fromEntries(toolNames.map((toolName) => {
    const lockEntry = packageLock.packages?.[`node_modules/${toolName}`] || {};
    return [toolName, {
      requested_version: packageJson.devDependencies?.[toolName] || '',
      resolved_version: lockEntry.version || '',
      integrity: lockEntry.integrity || '',
    }];
  }));
}

function collectBundledPythonDistributions(pythonBin, pythonVersion) {
  const code = `
import hashlib
import importlib.metadata as md
import json
import sys

distributions = []
for dist in md.distributions():
    name = dist.metadata.get('Name') or dist.name or ''
    distributions.append({'name': str(name), 'version': str(dist.version)})
distributions.sort(key=lambda item: (item['name'].lower(), item['version']))
fingerprint = hashlib.sha256(
    '\\n'.join(f"{item['name']}=={item['version']}" for item in distributions).encode('utf-8')
).hexdigest()
print(json.dumps({
    'python_version': sys.version.split()[0],
    'implementation': sys.implementation.name,
    'distribution_count': len(distributions),
    'distribution_fingerprint': fingerprint,
    'distributions': distributions,
}, sort_keys=True))
`.trim();
  const output = execFileSync(pythonBin, ['-c', code], {
    cwd: BUNDLE_DIR,
    encoding: 'utf8',
    env: buildBundledPythonEnv(pythonVersion),
  });
  return JSON.parse(output);
}

function mediaToolMetadata(toolPath) {
  const versionLine = execFileSync(toolPath, ['-version'], {
    cwd: ROOT,
    encoding: 'utf8',
  }).split(/\r?\n/).find((line) => line.trim()) || '';
  return {
    path: relativeBundlePath(toolPath),
    version_line: versionLine.trim(),
    size: fs.statSync(toolPath).size,
    sha256: sha256File(toolPath),
  };
}

function buildRuntimeManifest(pythonBin, pythonVersion) {
  const electronPackage = readJsonFile(ELECTRON_PACKAGE_PATH);
  const pythonInfo = collectBundledPythonDistributions(pythonBin, pythonVersion);
  const ffmpegExecutable = process.platform === 'win32' ? 'ffmpeg.exe' : 'ffmpeg';
  const ffprobeExecutable = process.platform === 'win32' ? 'ffprobe.exe' : 'ffprobe';
  const ffmpegPath = path.join(bundledFfmpegDir(), ffmpegExecutable);
  const ffprobePath = path.join(bundledFfmpegDir(), ffprobeExecutable);
  const criticalPaths = [
    path.join(BUNDLE_DIR, 'pyproject.toml'),
    pythonBin,
    ffmpegPath,
    ffprobePath,
    path.join(BUNDLE_SRC_DIR, 'splitshot', 'browser', 'server.py'),
    path.join(BUNDLE_SRC_DIR, 'splitshot', 'browser', 'state.py'),
    path.join(BUNDLE_SRC_DIR, 'splitshot', 'browser', 'static', 'index.html'),
    path.join(BUNDLE_SRC_DIR, 'splitshot', 'browser', 'static', 'app.js'),
    path.join(BUNDLE_SRC_DIR, 'splitshot', 'browser', 'static', 'styles.css'),
  ].filter((filePath) => fs.existsSync(filePath)).map((filePath) => fileDigestRecord(filePath, relativeBundlePath(filePath)));
  const sourceInputs = [
    PYPROJECT_PATH,
    UV_LOCK_PATH,
    ELECTRON_PACKAGE_PATH,
    ELECTRON_PACKAGE_LOCK_PATH,
  ].filter((filePath) => fs.existsSync(filePath));
  return {
    manifest_schema_version: 1,
    generated_at: new Date().toISOString(),
    application: {
      name: electronPackage.name,
      version: electronPackage.version,
    },
    bundle: {
      platform: process.platform,
      arch: process.arch,
      python_executable: relativeBundlePath(pythonBin),
      site_packages: relativeBundlePath(bundledSitePackagesDir(pythonVersion)),
      source_root: relativeBundlePath(BUNDLE_SRC_DIR),
      ffmpeg_root: relativeBundlePath(bundledFfmpegDir()),
    },
    source_inputs: Object.fromEntries(sourceInputs.map((filePath) => [
      relativeRepoPath(filePath),
      fileDigestRecord(filePath, relativeRepoPath(filePath)),
    ])),
    tool_versions: {
      node: { version: process.version },
      ...resolvedNodeToolVersions(),
      python: {
        version: pythonInfo.python_version,
        implementation: pythonInfo.implementation,
        distribution_count: pythonInfo.distribution_count,
        distribution_fingerprint: pythonInfo.distribution_fingerprint,
      },
      ffmpeg: mediaToolMetadata(ffmpegPath),
      ffprobe: mediaToolMetadata(ffprobePath),
    },
    python_distributions: pythonInfo.distributions,
    bundle_inventory: {
      critical_paths: criticalPaths,
      source_tree: directoryFingerprint(BUNDLE_SRC_DIR),
    },
  };
}

function normalizeManifestForComparison(manifest) {
  return JSON.stringify({
    ...manifest,
    generated_at: null,
  });
}

function writeRuntimeManifest(pythonBin, pythonVersion) {
  const manifest = buildRuntimeManifest(pythonBin, pythonVersion);
  fs.writeFileSync(BUNDLE_MANIFEST_PATH, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
  console.log(`[bundle] wrote runtime manifest: ${BUNDLE_MANIFEST_PATH}`);
  return manifest;
}

function verifyRuntimeManifest(pythonBin, pythonVersion) {
  if (!fs.existsSync(BUNDLE_MANIFEST_PATH)) {
    throw new Error(`Bundled runtime manifest not found at ${BUNDLE_MANIFEST_PATH}`);
  }
  const manifest = readJsonFile(BUNDLE_MANIFEST_PATH);
  const expected = buildRuntimeManifest(pythonBin, pythonVersion);
  if (normalizeManifestForComparison(manifest) !== normalizeManifestForComparison(expected)) {
    throw new Error('Bundled runtime manifest no longer matches the current bundle contents and pinned source inputs.');
  }
  console.log('[bundle] runtime manifest: OK');
}

function bundleFfmpeg() {
  const platformDir = bundledFfmpegDir();
  fs.mkdirSync(platformDir, { recursive: true });
  const overrideDir = process.env.SPLITSHOT_BUNDLED_FFMPEG_DIR;
  if (overrideDir) {
    for (const tool of ['ffmpeg', 'ffprobe']) {
      const executable = process.platform === 'win32' ? `${tool}.exe` : tool;
      const source = path.join(overrideDir, executable);
      if (!fs.existsSync(source)) {
        throw new Error(`[bundle] ${executable} not found in SPLITSHOT_BUNDLED_FFMPEG_DIR=${overrideDir}`);
      }
      const dest = path.join(platformDir, executable);
      copyTool(source, dest);
      console.log(`[bundle] bundled ${tool} from override: ${source} -> ${dest}`);
    }
    return;
  }

  if (process.env.SPLITSHOT_USE_HOST_FFMPEG === '1') {
    for (const tool of ['ffmpeg', 'ffprobe']) {
      const result = findTool(tool);
      if (!result) {
        throw new Error(`[bundle] ${tool} not found on PATH; packaged builds require vendored media tools`);
      }
      const executable = process.platform === 'win32' ? `${tool}.exe` : tool;
      const dest = path.join(platformDir, executable);
      copyTool(result, dest);
      console.log(`[bundle] bundled ${tool} from PATH: ${result} -> ${dest}`);
    }
    return;
  }

  fetchPortableMediaTools(platformDir);
}

function generateIcons() {
  const assetsDir = path.join(ROOT, 'electron', 'assets');
  const logo = path.join(ROOT, 'src', 'splitshot', 'browser', 'static', 'logo.png');
  if (!fs.existsSync(logo)) {
    console.warn('[bundle] WARNING: logo.png not found, skipping icon generation');
    return;
  }
  fs.mkdirSync(assetsDir, { recursive: true });
  const iconPng = path.join(assetsDir, 'icon.png');
  fs.copyFileSync(logo, iconPng);
  console.log('[bundle] copied icon.png to assets/');

  if (process.platform === 'darwin') {
    const iconset = path.join(assetsDir, 'icons.iconset');
    fs.mkdirSync(iconset, { recursive: true });
    execSync(`sips -z 1024 1024 "${logo}" --out "${iconPng}" > /dev/null 2>&1`);
    for (const size of [16, 32, 64, 128, 256, 512, 1024]) {
      execSync(`sips -z ${size} ${size} "${iconPng}" --out "${iconset}/icon_${size}x${size}.png" > /dev/null 2>&1`);
      if (size <= 512) {
        execSync(`sips -z ${size*2} ${size*2} "${iconPng}" --out "${iconset}/icon_${size}x${size}@2x.png" > /dev/null 2>&1`);
      }
    }
    execSync(`iconutil -c icns "${iconset}" -o "${path.join(assetsDir, 'icon.icns')}" > /dev/null 2>&1`);
    console.log('[bundle] generated icon.icns');
  }
}

function verifyBundle(pythonBin, pythonVersion) {
  console.log('[bundle] Verifying bundle...');
  const verifyScript = path.join(ROOT, 'electron', 'verify_bundle.py');
  const verifyCode = `import sys, os
sys.path.insert(0, ${JSON.stringify(BUNDLE_SRC_DIR)})
sys.path.insert(0, ${JSON.stringify(BUNDLE_DIR)})
ok = True
try:
    from splitshot.browser.server import BrowserControlServer
    from splitshot.ui.controller import ProjectController
    print("- server imports: OK")
except Exception as e:
    print(f"- server imports: WARNING - {e}")
    ok = False
try:
    from splitshot.media.ffmpeg import resolve_media_binary
    print(f"- ffmpeg: {resolve_media_binary('ffmpeg')}")
    print(f"- ffprobe: {resolve_media_binary('ffprobe')}")
except Exception as e:
    print(f"- ffmpeg: WARNING - {e}")
    ok = False
try:
    from importlib import resources
    static = resources.files("splitshot.browser.static")
    for asset in ("index.html", "styles.css", "app.js"):
        target = static / asset
        status = "present" if target.is_file() else "missing"
        print(f"- browser:{asset}: {status}")
        if status == "missing":
            ok = False
except Exception as e:
    print(f"- browser: WARNING - {e}")
    ok = False
print("- bundle verification: OK" if ok else "- bundle verification: WARN (non-critical failures)")
exit(0 if ok else 1)
	`;
  fs.writeFileSync(verifyScript, verifyCode, 'utf8');
  const env = buildBundledPythonEnv(pythonVersion);
  run(`"${pythonBin}" "${verifyScript}"`, { env, cwd: BUNDLE_DIR });
  fs.rmSync(verifyScript);
  // Verification imports can recreate transient caches under the bundled source
  // tree; re-prune before re-hashing the runtime manifest.
  pruneBundle();
  verifyRuntimeManifest(pythonBin, pythonVersion);
}

function buildWindowsPythonRuntime() {
  const sourcePrefix = getPythonBasePrefix();
  console.log(`[bundle] Copying Windows Python runtime from ${sourcePrefix}`);
  rmrf(WINDOWS_PYTHON_DIR);
  fs.cpSync(sourcePrefix, WINDOWS_PYTHON_DIR, { recursive: true });
  const pythonExe = path.join(WINDOWS_PYTHON_DIR, 'python.exe');
  if (!fs.existsSync(pythonExe)) {
    throw new Error(`Bundled Windows python.exe not found at ${pythonExe}`);
  }
  const pythonAlias = path.join(WINDOWS_PYTHON_DIR, 'python3.exe');
  if (fs.existsSync(pythonAlias)) {
    fs.rmSync(pythonAlias, { force: true });
    console.log('[bundle] removed windows alias python3.exe');
  }
  run(`uv pip install --python "${pythonExe}" --system --break-system-packages --link-mode copy "."`);
  return pythonExe;
}

function bundlePosixStdlib(pythonVersion) {
  if (process.platform === 'win32') return;
  const sourcePrefix = getPythonBasePrefix();
  const sourceStdlib = path.join(sourcePrefix, 'lib', `python${pythonVersion}`);
  const targetStdlib = path.join(VENV_DIR, 'lib', `python${pythonVersion}`);
  if (!fs.existsSync(sourceStdlib)) {
    throw new Error(`Bundled stdlib source not found at ${sourceStdlib}`);
  }
  fs.mkdirSync(targetStdlib, { recursive: true });
  for (const entry of fs.readdirSync(sourceStdlib, { withFileTypes: true })) {
    if (entry.name === 'site-packages') continue;
    const from = path.join(sourceStdlib, entry.name);
    const to = path.join(targetStdlib, entry.name);
    fs.cpSync(from, to, { recursive: true, force: true });
  }
  console.log(`[bundle] copied stdlib contents: ${sourceStdlib} -> ${targetStdlib}`);
}

function main() {
  const isCheck = process.argv.includes('check');
  console.log(`[bundle] Creating Python bundle in electron/bundle/${isCheck ? ' (check only)' : ''}`);

  if (!isCheck) {
    rmrf(BUNDLE_DIR);
    fs.mkdirSync(BUNDLE_DIR, { recursive: true });
  }

  const pythonVersion = getPythonVersion();
  console.log(`[bundle] Python version: ${pythonVersion}`);

  const pythonBin = isCheck ? bundledPythonExecutable(pythonVersion) : null;

  if (!isCheck) {
    const pythonExe = process.platform === 'win32'
      ? buildWindowsPythonRuntime()
      : installBundledPosixProject(pythonVersion);

    if (process.platform !== 'win32') {
      bundlePosixStdlib(pythonVersion);
    }

    // Copy libpython dylib so the resolved binary works on other machines
    if (process.platform === 'darwin') {
      const realPython = fs.realpathSync(pythonExe);
      const uvPythonRoot = path.dirname(path.dirname(realPython));
      const libSrc = path.join(uvPythonRoot, 'lib', 'libpython3.12.dylib');
      const libDir = path.join(VENV_DIR, 'lib');
      fs.mkdirSync(libDir, { recursive: true });
      if (fs.existsSync(libSrc)) {
        fs.copyFileSync(libSrc, path.join(libDir, 'libpython3.12.dylib'));
        console.log(`[bundle] copied libpython: ${libSrc}`);
      }
    }

    // Now resolve symlinks (replace with real copies for distribution)
    if (process.platform !== 'win32') {
      resolveSymlinks(path.dirname(pythonExe));
    }

    rmrf(BUNDLE_SRC_DIR);
    fs.cpSync(SRC_DIR, BUNDLE_SRC_DIR, { recursive: true });
    fs.cpSync(path.join(ROOT, 'pyproject.toml'), path.join(BUNDLE_DIR, 'pyproject.toml'));

    bundleFfmpeg();
    generateIcons();

    pruneBundle();
    writeRuntimeManifest(pythonExe, pythonVersion);
    verifyBundle(pythonExe, pythonVersion);
  } else {
    verifyBundle(pythonBin, pythonVersion);
  }

  if (!isCheck) {
    console.log('[bundle] Python bundle created successfully');
  } else {
    console.log('[bundle] Bundle verification passed');
  }
}

function pruneBundle() {
  const pruneDirs = ['__pycache__', '.pytest_cache', '.ruff_cache', 'node_modules'];
  const pruneExts = ['.pyc', '.pyo'];

  function walkAndPrune(dir) {
    if (!fs.existsSync(dir)) return;
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (pruneDirs.includes(entry.name)) {
          rmrf(full);
          console.log(`[bundle] pruned: ${full}`);
        } else {
          walkAndPrune(full);
        }
      } else if (entry.isFile()) {
        if (pruneExts.includes(path.extname(entry.name))) {
          fs.rmSync(full, { force: true });
        }
      }
    }
  }
  walkAndPrune(BUNDLE_DIR);

  const pythonVersion = getPythonVersion();
  const SITE = bundledSitePackagesDir(pythonVersion);

  if (process.platform === 'win32') {
    rmrf(path.join(WINDOWS_PYTHON_DIR, 'Tools'));
    rmrf(path.join(WINDOWS_PYTHON_DIR, 'Doc'));
    rmrf(path.join(WINDOWS_PYTHON_DIR, 'share'));
  } else {
    rmrf(path.join(VENV_DIR, '..', 'pip'));
    rmrf(path.join(VENV_DIR, 'share'));
  }
  rmrf(path.join(SITE, 'pip'));

  const PYSIDE = path.join(SITE, 'PySide6');
  if (fs.existsSync(PYSIDE)) {
    const keepFrameworks = new Set([
      'QtCore', 'QtGui', 'QtWidgets', 'QtOpenGL', 'QtOpenGLWidgets',
      'QtSvg', 'QtSvgWidgets', 'QtConcurrent', 'QtDBus', 'QtPrintSupport',
    ]);
    const QT_LIB = path.join(PYSIDE, 'Qt', 'lib');
    if (fs.existsSync(QT_LIB)) {
      for (const lib of ['libavcodec', 'libavformat', 'libavutil', 'libswresample', 'libswscale']) {
        for (const f of fs.readdirSync(QT_LIB, { withFileTypes: true })) {
          if (f.isFile() && f.name.startsWith(lib)) {
            fs.rmSync(path.join(QT_LIB, f.name));
          }
        }
      }
      for (const entry of fs.readdirSync(QT_LIB, { withFileTypes: true })) {
        const match = entry.name.match(/^(Qt\w+)\.framework$/);
        if (match && !keepFrameworks.has(match[1])) {
          rmrf(path.join(QT_LIB, entry.name));
        }
      }
    }
    for (const f of fs.readdirSync(PYSIDE, { withFileTypes: true })) {
      if (f.isFile() && f.name.endsWith('.abi3.so')) {
        const match = f.name.match(/^(Qt\w+)\.abi3\.so$/);
        if (match && !keepFrameworks.has(match[1])) {
          fs.rmSync(path.join(PYSIDE, f.name));
        }
      }
    }
    rmrf(path.join(PYSIDE, 'Qt', 'qml'));
    rmrf(path.join(PYSIDE, 'Qt', 'translations'));
    for (const f of fs.readdirSync(PYSIDE, { withFileTypes: true })) {
      if (f.isFile() && f.name.endsWith('.pyi')) {
        fs.rmSync(path.join(PYSIDE, f.name));
      }
    }
    const PLUGINS = path.join(PYSIDE, 'Qt', 'plugins');
    if (fs.existsSync(PLUGINS)) {
      const keepPlugins = ['platforms', 'styles', 'imageformats', 'iconengines'];
      for (const entry of fs.readdirSync(PLUGINS, { withFileTypes: true })) {
        if (entry.isDirectory() && !keepPlugins.includes(entry.name)) {
          rmrf(path.join(PLUGINS, entry.name));
        }
      }
    }
    for (const app of ['Assistant.app', 'Designer.app', 'Linguist.app']) {
      rmrf(path.join(PYSIDE, app));
    }
    for (const subdir of ['include', 'typesystems', 'scripts', 'glue', 'doc', 'support']) {
      rmrf(path.join(PYSIDE, subdir));
    }
  }

  const NPY = path.join(SITE, 'numpy');
  for (const d of ['tests', '_core/tests', 'f2py/tests', 'fft/tests', 'lib/tests',
    'linalg/tests', 'ma/tests', 'matrixlib/tests', 'polynomial/tests',
    'random/tests', 'testing/tests', 'typing/tests']) {
    rmrf(path.join(NPY, d));
  }

  rmrf(path.join(SITE, 'Cryptodome', 'SelfTest'));
}

main();
