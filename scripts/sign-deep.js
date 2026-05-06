// Custom sign function that adds --deep flag
const { execSync } = require('child_process');

exports.default = async function(config) {
  const { path: filePath, identity, keychain, options } = config;
  const id = identity || '49C2A7CDD2C1C84BDE7F719CB4B359E61AF7227C';
  const entitlements = options && options.entitlements ? `--entitlements "${options.entitlements}"` : '';
  const keychainArg = keychain ? `--keychain "${keychain}"` : '';
  const cmd = `codesign --deep --force --options runtime --timestamp -s ${id} ${entitlements} ${keychainArg} "${filePath}"`.replace(/\s+/g, ' ').trim();
  console.log(`[sign-deep] ${cmd}`);
  execSync(cmd, { stdio: 'inherit' });
};
