// Custom sign function that adds --deep flag
const { execSync } = require('child_process');

exports.default = async function(config) {
  const id = config.identity;
  const kc = config.keychain ? `--keychain "${config.keychain}"` : '';
  const appPath = config.app ? config.app.appDir || config.app.outDir : null;

  // Sign all binaries listed in config
  if (config.binaries && config.binaries.length > 0) {
    for (const binary of config.binaries) {
      const cmd = `codesign --deep --force --options runtime --timestamp -s ${id} ${kc} "${binary}"`;
      execSync(cmd, { stdio: 'inherit' });
    }
  }

  // Sign the main .app if we have the path
  if (appPath) {
    const cmd = `codesign --deep --force --options runtime --timestamp -s ${id} ${kc} "${appPath}"`;
    execSync(cmd, { stdio: 'inherit' });
  }
};
