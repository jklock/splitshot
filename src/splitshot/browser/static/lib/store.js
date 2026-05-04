export function createStore(initialState = {}) {
  let currentState = initialState;
  const listeners = new Set();

  function notify(previousState, nextState, patch) {
    if (previousState === nextState) return;
    [...listeners].forEach((listener) => {
      listener({ previousState, nextState, patch });
    });
  }

  function snapshot() {
    return currentState;
  }

  function get(key, fallback = undefined) {
    if (key === undefined) return currentState;
    if (
      currentState
      && typeof currentState === "object"
      && !Array.isArray(currentState)
      && Object.prototype.hasOwnProperty.call(currentState, key)
    ) {
      return currentState[key];
    }
    return fallback;
  }

  function set(keyOrState, value) {
    if (arguments.length === 1) {
      const previousState = currentState;
      currentState = keyOrState;
      notify(previousState, currentState, null);
      return currentState;
    }
    return patch({ [keyOrState]: value });
  }

  function patch(nextPatch = {}) {
    if (!nextPatch || typeof nextPatch !== "object" || Array.isArray(nextPatch)) return currentState;
    const baseState = currentState && typeof currentState === "object" && !Array.isArray(currentState)
      ? currentState
      : {};
    let changed = false;
    Object.entries(nextPatch).forEach(([key, value]) => {
      if (!changed && baseState[key] !== value) changed = true;
    });
    if (!changed) return currentState;
    const previousState = currentState;
    currentState = {
      ...baseState,
      ...nextPatch,
    };
    notify(previousState, currentState, nextPatch);
    return currentState;
  }

  function subscribe(listener) {
    if (typeof listener !== "function") return () => {};
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  }

  return Object.freeze({
    snapshot,
    get,
    set,
    patch,
    subscribe,
  });
}
