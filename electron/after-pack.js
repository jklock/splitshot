// electron-builder afterPack hook: deep-signs all binaries before notarization
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

exports.default = async function(context) {
  const appDir = context.packager.appDir;
  const identity = 'Developer ID Application: John Klockenkemper (7DJ75AWV5R)';

  console.log('[afterPack] deep-signing:', appDir);

  // Import cert into the temp keychain that electron-builder provides
  const kc = process.env.CSC_KEYCHAIN || (execSync('security list-keychains -d user | head -1', { encoding: 'utf8' }).trim().replace(/"/g, ''));
  if (process.env.CSC_LINK && process.env.CSC_KEY_PASSWORD) {
    const p12 = path.join(os.tmpdir(), `devid-${Date.now()}.p12`);
    fs.writeFileSync(p12, Buffer.from(process.env.CSC_LINK, 'base64'));
    try {
      execSync(`security import "${p12}" -k "${kc}" -P "${process.env.CSC_KEY_PASSWORD}" -T /usr/bin/codesign -A`, { stdio: 'inherit' });
    } catch (e) {
      console.error('[afterPack] import cert failed:', e.message);
    }
    fs.unlinkSync(p12);
  }

  // Set default keychain to ensure codesign finds the cert
  try {
    execSync(`security default-keychain -s "${kc}"`, { stdio: 'ignore' });
    execSync(`security unlock-keychain -p "" "${kc}"`, { stdio: 'ignore' });
  } catch {}

  // Deep-sign the entire .app bundle
  const cmd = `codesign --deep --force --options runtime --timestamp -s "${identity}" --keychain "${kc}" "${appDir}" 2>&1`;
  console.log('[afterPack] signing...');
  const result = execSync(cmd, { encoding: 'utf8', timeout: 300000 });
  if (result.trim()) console.log('[afterPack]', result.trim().substring(0, 300));
  console.log('[afterPack] done');
};
