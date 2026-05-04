export function createMutableBindings(bindings = {}) {
  const descriptors = {};
  Object.entries(bindings || {}).forEach(([name, [getter, setter]]) => {
    const descriptor = {
      configurable: true,
      enumerable: false,
      get: typeof getter === "function" ? getter : () => getter,
    };
    if (typeof setter === "function") descriptor.set = setter;
    descriptors[name] = descriptor;
  });
  return Object.defineProperties({}, descriptors);
}

export function installMutableGlobals(target, source) {
  Object.entries(Object.getOwnPropertyDescriptors(source || {})).forEach(([name, descriptor]) => {
    const existingDescriptor = Object.getOwnPropertyDescriptor(target, name);
    if (existingDescriptor && existingDescriptor.configurable === false) return;
    Object.defineProperty(target, name, {
      configurable: true,
      enumerable: false,
      ...descriptor,
    });
  });
  return target;
}

export function installValueGlobals(target, values = {}) {
  Object.entries(values || {}).forEach(([name, value]) => {
    const existingDescriptor = Object.getOwnPropertyDescriptor(target, name);
    if (existingDescriptor && existingDescriptor.configurable === false) return;
    Object.defineProperty(target, name, {
      configurable: true,
      enumerable: false,
      writable: true,
      value,
    });
  });
  return target;
}

export function installLegacyGlobalCompat({
  target,
  valueSources = [],
  values = {},
  mutableSources = [],
  mutableBindings = {},
  backbone = null,
  bootstrapMode = "module",
} = {}) {
  if (!target) return target;

  const mergedValues = Object.assign(
    {},
    ...((Array.isArray(valueSources) ? valueSources : []).filter(Boolean)),
    values || {},
  );

  installValueGlobals(target, mergedValues);

  (Array.isArray(mutableSources) ? mutableSources : []).forEach((source) => {
    if (!source) return;
    installMutableGlobals(target, source);
  });

  if (mutableBindings && Object.keys(mutableBindings).length > 0) {
    installMutableGlobals(target, createMutableBindings(mutableBindings));
  }

  if (backbone?.bus || backbone?.store) {
    target.__splitshotBackbone = Object.freeze({ bus: backbone.bus, store: backbone.store });
  }
  target.__splitshotBootstrapMode = bootstrapMode;
  return target;
}
