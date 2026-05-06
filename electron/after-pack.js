// electron-builder afterPack hook: deep-signs all binaries before notarization
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

exports.default = async function(context) {
  const appName = context.packager.appInfo.productFilename;
  const appOutDir = context.appOutDir || context.outDir;
  const appPath = path.join(appOutDir, `${appName}.app`);
  console.log('[afterPack] signing:', appPath);

  if (!fs.existsSync(appPath)) {
    console.error('[afterPack] ERROR: .app not found');
    return;
  }

  if (process.env.CSC_LINK && process.env.CSC_KEY_PASSWORD) {
    const p12 = path.join(os.tmpdir(), `devid-${Date.now()}.p12`);
    fs.writeFileSync(p12, Buffer.from(process.env.CSC_LINK, 'base64'));
    try {
      execSync(`security import "${p12}" -k ~/Library/Keychains/login.keychain-db -P "${process.env.CSC_KEY_PASSWORD}" -T /usr/bin/codesign -A`, { stdio: 'pipe' });
    } catch (e) {
      console.error('[afterPack] import failed:', e.stderr ? e.stderr.toString().trim().substring(0,200) : e.message);
    }
    try { fs.unlinkSync(p12); } catch {}
  }

  try {
    execSync('security unlock-keychain -p "" ~/Library/Keychains/login.keychain-db', { stdio: 'pipe' });
  } catch {}

  const identity = 'Developer ID Application: John Klockenkemper (7DJ75AWV5R)';
  const cmd = `codesign --deep --force --options runtime --timestamp -s "${identity}" "${appPath}"`;
  console.log('[afterPack] running:', cmd);
  try {
    const result = execSync(cmd, { timeout: 300000, stdio: 'pipe' });
    console.log('[afterPack] signed successfully');
  } catch (e) {
    const stderr = e.stderr ? e.stderr.toString().trim() : '';
    const stdout = e.stdout ? e.stdout.toString().trim() : '';
    console.error('[afterPack] codesign failed:', stderr || stdout || e.message);
    // Don't throw — let the build continue without deep-signing
  }
};
