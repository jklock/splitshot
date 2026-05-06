// electron-builder afterPack hook: deep-signs all binaries before notarization
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

exports.default = async function(context) {
  // Find the .app directory
  const appDir = context.appOutDir || (context.packager && context.packager.appDir);
  if (!appDir) {
    console.error('[afterPack] ERROR: appDir not found');
    return;
  }
  console.log('[afterPack] deep-signing:', appDir);

  // Import cert into login keychain
  if (process.env.CSC_LINK && process.env.CSC_KEY_PASSWORD) {
    const p12 = path.join(os.tmpdir(), `devid-${Date.now()}.p12`);
    fs.writeFileSync(p12, Buffer.from(process.env.CSC_LINK, 'base64'));
    try {
      execSync(`security import "${p12}" -k ~/Library/Keychains/login.keychain-db -P "${process.env.CSC_KEY_PASSWORD}" -T /usr/bin/codesign -A`, { stdio: 'inherit' });
      console.log('[afterPack] cert imported');
    } catch (e) {
      console.error('[afterPack] import failed:', e.message);
    }
    fs.unlinkSync(p12);
  }

  // Unlock login keychain
  try {
    execSync('security unlock-keychain -p "" ~/Library/Keychains/login.keychain-db 2>/dev/null', { stdio: 'ignore' });
    execSync('security default-keychain -s ~/Library/Keychains/login.keychain-db 2>/dev/null', { stdio: 'ignore' });
  } catch {}

  // Deep-sign the entire .app
  const identity = 'Developer ID Application: John Klockenkemper (7DJ75AWV5R)';
  const cmd = `codesign --deep --force --options runtime --timestamp -s "${identity}" "${appDir}" 2>&1`;
  console.log('[afterPack] signing...');
  const result = execSync(cmd, { encoding: 'utf8', timeout: 300000 });
  if (result.trim()) console.log('[afterPack]', result.trim().substring(0, 300));
  console.log('[afterPack] done');
};
