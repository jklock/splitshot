// Custom sign function that adds --deep flag
const { execSync } = require('child_process');

exports.default = async function(config) {
  console.log('[sign-deep] config keys:', Object.keys(config).join(', '));
  console.log('[sign-deep] config values:', JSON.stringify(config, null, 2));

  const filePath = config.path || config.appPath || config.file;
  const id = config.identity || process.env.CSC_LINK_IDENTITY || '49C2A7CDD2C1C84BDE7F719CB4B359E61AF7227C';
  if (!filePath) {
    throw new Error(`[sign-deep] No path found in config. Keys: ${Object.keys(config).join(', ')}`);
  }
  const keychainArg = config.keychain ? `--keychain "${config.keychain}"` : '';
  const entitlementsOption = config.entitlements ? `--entitlements "${config.entitlements}"` : '';
  const cmd = [
    'codesign', '--deep', '--force', '--options', 'runtime', '--timestamp',
    '-s', id,
    keychainArg,
    entitlementsOption,
    `"${filePath}"`
  ].filter(Boolean).join(' ');
  console.log(`[sign-deep] signing ${filePath}`);
  execSync(cmd, { stdio: 'inherit' });
};
