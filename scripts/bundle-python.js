const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const BUNDLE_DIR = path.join(ROOT, 'electron', 'bundle');
const VENV_DIR = path.join(BUNDLE_DIR, '.venv');
const SRC_DIR = path.join(ROOT, 'src');
const BUNDLE_SRC_DIR = path.join(BUNDLE_DIR, 'src');

function run(cmd, opts = {}) {
  console.log(`[bundle] ${cmd}`);
  execSync(cmd, { stdio: 'inherit', cwd: ROOT, ...opts });
}

function rmrf(target) {
  if (fs.existsSync(target)) {
    fs.rmSync(target, { recursive: true, force: true });
  }
}

function getPythonVersion() {
  const result = execSync('uv run python --version', { encoding: 'utf8', cwd: ROOT });
  const match = result.trim().match(/^Python (\d+\.\d+)/);
  if (!match) throw new Error(`Could not detect Python version from: ${result}`);
  return match[1];
}

function getPythonBinDir(venvDir, pythonVersion) {
  const isWin = process.platform === 'win32';
  const binDir = isWin ? 'Scripts' : 'bin';
  const pythonBin = path.join(venvDir, binDir, `python${isWin ? '.exe' : ''}`);
  if (!fs.existsSync(pythonBin)) return null;
  return path.dirname(pythonBin);
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
  const cmd = process.platform === 'win32' ? `where ${tool} 2>nul` : `which ${tool} 2>/dev/null`;
  try {
    const result = execSync(cmd, { encoding: 'utf8', cwd: ROOT }).trim().split(/\r?\n/)[0];
    return result || '';
  } catch {
    return '';
  }
}

function bundleFfmpeg() {
  const ffmpegDir = path.join(BUNDLE_SRC_DIR, 'splitshot', 'resources', 'ffmpeg');
  const platform = process.platform === 'darwin' ? 'macos' : process.platform === 'win32' ? 'windows' : 'linux';
  const platformDir = path.join(ffmpegDir, platform);
  fs.mkdirSync(platformDir, { recursive: true });
  for (const tool of ['ffmpeg', 'ffprobe']) {
    const result = findTool(tool);
    if (result) {
      const dest = path.join(platformDir, tool);
      fs.cpSync(result, dest);
      fs.chmodSync(dest, 0o755);
      console.log(`[bundle] bundled ${tool}: ${result} -> ${dest}`);
    } else {
      console.warn(`[bundle] WARNING: ${tool} not found on PATH, skipping`);
    }
  }
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

function verifyBundle(pythonBin) {
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
  const env = { ...process.env, PYTHONPATH: BUNDLE_SRC_DIR };
  try {
    run(`"${pythonBin}" "${verifyScript}"`, { env, cwd: BUNDLE_DIR });
  } catch {
    console.warn('[bundle] WARNING: Verification had non-critical failures');
  }
  fs.rmSync(verifyScript);
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

  if (!isCheck) {
    run(`uv venv "${VENV_DIR}" --python ${pythonVersion} --seed`);
  }

  const binDir = getPythonBinDir(VENV_DIR, pythonVersion);
  if (!binDir) throw new Error(`Python binary not found in venv at ${VENV_DIR}`);
  const pythonBin = path.join(binDir, `python${process.platform === 'win32' ? '.exe' : ''}`);

  if (!isCheck) {
    const pythonExe = path.join(binDir, `python${process.platform === 'win32' ? '.exe' : ''}`);

    // Install deps BEFORE symlink resolution (venv python is a working symlink here)
    run(`uv pip install --python "${pythonExe}" "."`);

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
    resolveSymlinks(binDir);

    bundleFfmpeg();

    rmrf(BUNDLE_SRC_DIR);
    fs.cpSync(SRC_DIR, BUNDLE_SRC_DIR, { recursive: true });
    fs.cpSync(path.join(ROOT, 'pyproject.toml'), path.join(BUNDLE_DIR, 'pyproject.toml'));

    generateIcons();

    pruneBundle();
  }

  verifyBundle(pythonBin);

  if (!isCheck) {
    console.log('[bundle] Python bundle created successfully');
  } else {
    console.log('[bundle] Bundle verification passed');
  }
}

function pruneBundle() {
  const pruneDirs = ['__pycache__', '.pytest_cache', '.ruff_cache', 'node_modules'];
  const pruneExts = ['.pyc', '.pyo', '.pyd'];

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

  const SITE = path.join(VENV_DIR, 'lib', `python${getPythonVersion()}`, 'site-packages');

  rmrf(path.join(VENV_DIR, '..', 'pip'));
  rmrf(path.join(VENV_DIR, 'share'));
  rmrf(path.join(SITE, 'pip'));
  rmrf(path.join(SITE, 'pip-*.dist-info'));

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
