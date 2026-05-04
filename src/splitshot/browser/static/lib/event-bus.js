export function createEventBus() {
  const listenersByEvent = new Map();

  function ensureListeners(eventName) {
    if (!listenersByEvent.has(eventName)) listenersByEvent.set(eventName, new Set());
    return listenersByEvent.get(eventName);
  }

  function on(eventName, listener) {
    if (typeof listener !== "function") return () => {};
    const listeners = ensureListeners(eventName);
    listeners.add(listener);
    return () => off(eventName, listener);
  }

  function once(eventName, listener) {
    if (typeof listener !== "function") return () => {};
    const unsubscribe = on(eventName, (detail) => {
      unsubscribe();
      listener(detail);
    });
    return unsubscribe;
  }

  function off(eventName, listener) {
    const listeners = listenersByEvent.get(eventName);
    if (!listeners) return false;
    const removed = listeners.delete(listener);
    if (listeners.size === 0) listenersByEvent.delete(eventName);
    return removed;
  }

  function emit(eventName, detail = undefined) {
    const listeners = listenersByEvent.get(eventName);
    if (!listeners || listeners.size === 0) return detail;
    [...listeners].forEach((listener) => listener(detail));
    return detail;
  }

  function clear(eventName = null) {
    if (eventName === null || eventName === undefined) {
      listenersByEvent.clear();
      return;
    }
    listenersByEvent.delete(eventName);
  }

  return Object.freeze({
    on,
    once,
    off,
    emit,
    clear,
  });
}
