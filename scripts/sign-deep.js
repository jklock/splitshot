// Custom sign function that adds --deep flag.
// Imports the cert ourselves so we can use it with --deep.
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

exports.default = async function(config) {
  const id = config.identity || process.env.CSC_LINK_IDENTITY;
  const kc = config.keychain;

  // Import cert if CSC_LINK is available (for --deep signing)
  if (process.env.CSC_LINK && process.env.CSC_KEY_PASSWORD) {
    const tmpP12 = path.join(require('os').tmpdir(), `devid-${Date.now()}.p12`);
    fs.writeFileSync(tmpP12, Buffer.from(process.env.CSC_LINK, 'base64'));
    try {
      execSync(`security import "${tmpP12}" -k "${kc || 'login.keychain'}" -P "${process.env.CSC_KEY_PASSWORD}" -T /usr/bin/codesign -A 2>/dev/null`, { stdio: 'ignore' });
    } catch {}
    fs.unlinkSync(tmpP12);
  }

  const kcFlag = kc ? `--keychain "${kc}"` : '';

  // Sign all binaries with --deep
  if (config.binaries && config.binaries.length > 0) {
    for (const binary of config.binaries) {
      try {
        execSync(`codesign --deep --force --options runtime --timestamp -s ${id} ${kcFlag} "${binary}" 2>/dev/null`);
      } catch {}
    }
  }

  // Sign the main app
  const appPath = config.app ? config.app.appDir || config.app.outDir : null;
  if (appPath) {
    try {
      execSync(`codesign --deep --force --options runtime --timestamp -s ${id} ${kcFlag} "${appPath}"`, { stdio: 'inherit' });
    } catch (e) {
      console.error('[sign-deep] WARNING: --deep sign failed, app may not be notarizable:', e.message);
    }
  }
};
