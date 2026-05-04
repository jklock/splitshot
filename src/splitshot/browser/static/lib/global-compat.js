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
