// Custom sign that adds --deep. electron-builder v25 calls this with the full config.
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

exports.default = async function(config) {
  const identity = config.identity;
  const keychain = config.keychain;

  console.log('sign-deep: identity=' + identity);
  console.log('sign-deep: keychain=' + keychain);
  console.log('sign-deep: CSC_LINK=' + (process.env.CSC_LINK ? 'set' : 'not set'));

  // Check if cert is findable
  try {
    const id = execSync(`security find-identity -v -p basic 2>&1 | grep "${identity}"`, { encoding: 'utf8', timeout: 5000 });
    console.log('sign-deep: cert found:', id.trim().substring(0, 60));
  } catch {
    console.log('sign-deep: cert NOT found in default keychain, importing...');
    if (process.env.CSC_LINK && process.env.CSC_KEY_PASSWORD) {
      const p12 = path.join(os.tmpdir(), `devid-${Date.now()}.p12`);
      fs.writeFileSync(p12, Buffer.from(process.env.CSC_LINK, 'base64'));
      try {
        execSync(`security import "${p12}" -k "${keychain}" -P "${process.env.CSC_KEY_PASSWORD}" -T /usr/bin/codesign -A`, { stdio: 'inherit' });
        console.log('sign-deep: cert imported successfully');
      } catch(e) {
        console.error('sign-deep: import failed:', e.message);
      }
      fs.unlinkSync(p12);
    }
  }

  // Sign files with --deep
  const signFile = (filePath) => {
    const cmd = `codesign --deep --force --options runtime --timestamp -s ${identity} --keychain "${keychain}" "${filePath}" 2>&1`;
    const result = execSync(cmd, { encoding: 'utf8', timeout: 60000 });
    console.log('sign-deep: signed', filePath);
  };

  // Sign listed binaries
  if (config.binaries && config.binaries.length > 0) {
    console.log('sign-deep: signing ' + config.binaries.length + ' binaries');
    for (const binary of config.binaries) {
      try { signFile(binary); } catch (e) { console.error('sign-deep: FAILED', binary, e.message); }
    }
  }

  // Sign main .app
  const appDir = config.app ? config.app.appDir || config.app.outDir : null;
  if (appDir) {
    console.log('sign-deep: deep-signing app: ' + appDir);
    try {
      signFile(appDir);
      console.log('sign-deep: DONE - app deep-signed');
    } catch (e) {
      console.error('sign-deep: app deep-sign failed:', e.message);
    }
  } else {
    console.log('sign-deep: no appDir found in config.app');
    console.log('sign-deep: app keys:', JSON.stringify(Object.keys(config.app || {})));
  }
};
