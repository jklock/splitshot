// electron-builder afterSign hook: signs all nested binaries before notarization
const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

exports.default = async function(context) {
  const { appOutDir, packager } = context;
  const appName = packager.appInfo.productFilename;
  const appPath = path.join(appOutDir, `${appName}.app`);
  const identity = process.env.CSC_LINK_IDENTITY || '49C2A7CDD2C1C84BDE7F719CB4B359E61AF7227C';

  console.log(`[afterSign] Signing nested binaries in ${appPath}`);

  // Sign all Mach-O files inside the app bundle
  function walk(dir) {
    let count = 0;
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (entry.name.endsWith('.app') || entry.name.endsWith('.framework') || entry.name === 'MacOS' || entry.name === 'Resources' || entry.name === 'Helpers' || entry.name === 'Versions') {
          count += walk(full);
        }
      } else if (entry.isFile()) {
        try {
          execSync(
            `codesign --force --options runtime --timestamp -s ${identity} "${full}"`,
            { stdio: 'ignore', timeout: 10000 }
          );
          count++;
        } catch {
          // not a Mach-O binary, skip silently
        }
      }
    }
    return count;
  }

  const signed = walk(appPath);
  console.log(`[afterSign] Signed ${signed} nested files`);

  // Re-sign the outer .app wrapper
  execSync(`codesign --force --options runtime --timestamp -s ${identity} "${appPath}"`, { stdio: 'inherit' });
  console.log('[afterSign] Done');
};
