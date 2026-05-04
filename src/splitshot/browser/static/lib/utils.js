export const $ = (id) => document.getElementById(id);

export function debounce(fn, delayMs = 250) {
  let timer = null;
  let lastArgs = null;

  const debounced = (...args) => {
    lastArgs = args;
    window.clearTimeout(timer);
    timer = window.setTimeout(() => {
      timer = null;
      const pendingArgs = lastArgs;
      lastArgs = null;
      fn(...(pendingArgs || []));
    }, delayMs);
  };

  debounced.cancel = () => {
    window.clearTimeout(timer);
    timer = null;
    lastArgs = null;
  };

  debounced.flush = () => {
    if (timer === null) return false;
    window.clearTimeout(timer);
    timer = null;
    const pendingArgs = lastArgs;
    lastArgs = null;
    fn(...(pendingArgs || []));
    return true;
  };

  debounced.pending = () => timer !== null;

  return debounced;
}

export function savedNumber(key, fallback) {
  const value = Number(window.localStorage.getItem(key));
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

export function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

export function clampNumber(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

export function seconds(ms) {
  if (ms === null || ms === undefined || ms === "") return "--.--";
  return (ms / 1000).toFixed(2);
}

export function precise(ms) {
  if (ms === null || ms === undefined || ms === "") return "";
  return (ms / 1000).toFixed(3);
}

export function splitSeconds(ms) {
  if (ms === null || ms === undefined || ms === "") return "--.--s";
  return `${seconds(ms)}s`;
}

export function numericMs(value) {
  if (value === null || value === undefined || value === "") return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

export function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || value === "") return "";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return String(value);
  if (Number.isInteger(numeric)) return String(numeric);
  return numeric.toFixed(digits);
}

export function fileName(path) {
  if (!path) return "No Video Selected";
  const normalized = path.split("\\").join("/");
  const base = normalized.split("/").filter(Boolean).pop() || path;
  return base.replace(/^[a-f0-9]{32}_/i, "");
}

export function normalizedUiBooleanMap(data) {
  if (!data || typeof data !== "object" || Array.isArray(data)) return {};
  return Object.fromEntries(
    Object.entries(data)
      .map(([key, value]) => [String(key || "").trim(), Boolean(value)])
      .filter(([key]) => Boolean(key)),
  );
}

export function normalizedUiFloatMap(data, minimum = 0) {
  if (!data || typeof data !== "object" || Array.isArray(data)) return {};
  return Object.fromEntries(
    Object.entries(data)
      .map(([key, value]) => [String(key || "").trim(), Number(value)])
      .filter(([key, value]) => Boolean(key) && Number.isFinite(value) && value >= minimum),
  );
}

export function normalizedUiStringList(data) {
  if (!Array.isArray(data)) return [];
  return data
    .map((value) => String(value || "").trim())
    .filter(Boolean);
}
