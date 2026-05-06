// Custom sign that adds --deep, using the Developer ID cert name
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

exports.default = async function(config) {
  const keychain = config.keychain;
  const identity = 'Developer ID Application: John Klockenkemper (7DJ75AWV5R)';

  // Import the cert if not already available
  if (process.env.CSC_LINK && process.env.CSC_KEY_PASSWORD) {
    const p12 = path.join(os.tmpdir(), `devid-${Date.now()}.p12`);
    fs.writeFileSync(p12, Buffer.from(process.env.CSC_LINK, 'base64'));
    try {
      execSync(`security import "${p12}" -k "${keychain}" -P "${process.env.CSC_KEY_PASSWORD}" -T /usr/bin/codesign -A`, { stdio: 'ignore' });
    } catch (e) {
      console.error('sign-deep: import failed:', e.message);
    }
    try { fs.unlinkSync(p12); } catch {}
  }

  const sign = (filePath) => {
    const cmd = `codesign --deep --force --options runtime --timestamp -s "${identity}" --keychain "${keychain}" "${filePath}" 2>&1`;
    const result = execSync(cmd, { encoding: 'utf8', timeout: 120000 });
    if (result.trim()) console.log('sign-deep:', result.trim().substring(0, 200));
  };

  // Sign all binaries
  if (config.binaries) {
    for (const b of config.binaries) {
      try { sign(b); } catch (e) { console.error('sign-deep: binary fail:', path.basename(b), e.message.substring(0,100)); }
    }
  }

  // Deep-sign the main .app
  const appDir = config.appDir || (config.app && (config.app.appDir || config.app.outDir));
  if (appDir) {
    console.log('sign-deep: deep-signing', path.basename(appDir));
    sign(appDir);
  } else if (Array.isArray(config.app)) {
    for (const item of config.app) {
      if (typeof item === 'string' && (item.endsWith('.app') || item.endsWith('.framework'))) {
        try { sign(item); } catch (e) { console.error('sign-deep: item fail:', path.basename(item)); }
      }
    }
  }
};
