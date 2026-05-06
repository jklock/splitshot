// Custom sign that adds --deep. electron-builder v25 calls this with the full config.
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

exports.default = async function(config) {
  const identity = config.identity;
  const keychain = config.keychain;

  // Import cert if not findable
  try {
    execSync(`security find-identity -v -p basic 2>&1 | grep -q "${identity}"`, { timeout: 5000 });
  } catch {
    if (process.env.CSC_LINK && process.env.CSC_KEY_PASSWORD) {
      const p12 = path.join(os.tmpdir(), `devid-${Date.now()}.p12`);
      fs.writeFileSync(p12, Buffer.from(process.env.CSC_LINK, 'base64'));
      execSync(`security import "${p12}" -k "${keychain}" -P "${process.env.CSC_KEY_PASSWORD}" -T /usr/bin/codesign -A`, { stdio: 'inherit' });
      fs.unlinkSync(p12);
    }
  }

  const sign = (filePath) => {
    execSync(`codesign --deep --force --options runtime --timestamp -s ${identity} --keychain "${keychain}" "${filePath}"`, { stdio: 'inherit' });
  };

  // Sign all binaries (these are the individual .app, .framework, .dylib files)
  if (config.binaries) {
    for (const b of config.binaries) {
      try { sign(b); } catch {}
    }
  }

  // config.app is an ARRAY of paths including the main .app, helpers, and frameworks
  // Find and sign the main .app from it
  if (Array.isArray(config.app)) {
    for (const item of config.app) {
      if (typeof item === 'string' && item.endsWith('.app') && !item.includes('Helper')) {
        try { sign(item); } catch {}
        break;
      }
    }
  }
};
