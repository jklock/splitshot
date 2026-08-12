const notarizeEnabled = process.platform !== 'darwin' || process.env.SPLITSHOT_MAC_NOTARIZE !== '0';

module.exports = {
  appId: 'studio.splitshot.app',
  productName: 'SplitShot',
  directories: {
    output: 'build',
  },
  compression: 'maximum',
  files: [
    'main.js',
    'preload.js',
    'launch-intent.js',
  ],
  extraResources: [
    {
      from: 'bundle',
      to: 'bundle',
      filter: ['**/*'],
    },
  ],
  mac: {
    category: 'public.app-category.sports',
    target: ['dmg'],
    icon: 'assets/icon.icns',
    hardenedRuntime: true,
    notarize: notarizeEnabled,
    timestamp: notarizeEnabled ? undefined : 'none',
    gatekeeperAssess: false,
    forceCodeSigning: true,
    entitlements: 'assets/entitlements.mac.plist',
    entitlementsInherit: 'assets/entitlements.mac.plist',
    extendInfo: {
      CFBundleDocumentTypes: [
        {
          CFBundleTypeName: 'SplitShot Project',
          CFBundleTypeRole: 'Editor',
          LSHandlerRank: 'Owner',
          LSItemContentTypes: ['studio.splitshot.ssproj'],
        },
      ],
    },
  },
  win: {
    target: ['nsis', 'dir'],
    icon: 'assets/icon.ico',
  },
  linux: {
    target: ['AppImage', 'dir'],
    icon: 'assets/icon.png',
    category: 'Sports',
    mimeTypes: ['application/x-splitshot-project'],
  },
  fileAssociations: [
    {
      ext: 'ssproj',
      name: 'SplitShot Project',
      description: 'SplitShot project bundle',
      mimeType: 'application/x-splitshot-project',
      role: 'Editor',
    },
  ],
  protocols: {
    name: 'SplitShot',
    schemes: ['splitshot'],
  },
};
