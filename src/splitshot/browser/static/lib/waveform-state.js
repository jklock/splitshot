export function createWaveformState({
  $ = (id) => document.getElementById(id),
  clamp = (value, minimum, maximum) => Math.min(maximum, Math.max(minimum, value)),
  getState = () => null,
  getWaveformZoomX = () => 1,
  setWaveformZoomX = () => {},
  getWaveformOffsetMs = () => 0,
  setWaveformOffsetMs = () => {},
  syncLocalProjectUiState = () => {},
  scheduleProjectUiStateApply = () => {},
  storage = window.localStorage,
  waveformWindowHandleMinPx = 18,
} = {}) {
  function currentState() {
    return getState() || {};
  }

  function durationMs() {
    return Math.max(
      1,
      currentState()?.project?.primary_video?.active_duration_ms
        || currentState()?.project?.primary_video?.duration_ms
        || 1,
    );
  }

  function waveformWindow() {
    const duration = durationMs();
    const currentZoomX = clamp(getWaveformZoomX(), 1, 200);
    if (currentZoomX !== getWaveformZoomX()) setWaveformZoomX(currentZoomX);
    const visibleDuration = Math.max(10, duration / currentZoomX);
    const clampedOffset = clamp(getWaveformOffsetMs(), 0, Math.max(0, duration - visibleDuration));
    if (clampedOffset !== getWaveformOffsetMs()) setWaveformOffsetMs(clampedOffset);
    return {
      start: clampedOffset,
      end: clampedOffset + visibleDuration,
      duration: visibleDuration,
    };
  }

  function persistWaveformViewport() {
    storage?.setItem?.("splitshot.waveform.zoomX", String(getWaveformZoomX()));
    storage?.setItem?.("splitshot.waveform.offsetMs", String(Math.round(getWaveformOffsetMs())));
    syncLocalProjectUiState();
    scheduleProjectUiStateApply();
  }

  function setWaveformOffset(nextOffsetMs, { persist = true } = {}) {
    const visible = waveformWindow();
    const maxOffset = Math.max(0, durationMs() - visible.duration);
    const clampedOffset = clamp(nextOffsetMs, 0, maxOffset);
    if (Math.abs(clampedOffset - getWaveformOffsetMs()) < 0.5) return false;
    setWaveformOffsetMs(clampedOffset);
    if (persist) persistWaveformViewport();
    return true;
  }

  function centerWaveformOnTime(timeMs, { persist = true } = {}) {
    const visible = waveformWindow();
    const maxOffset = Math.max(0, durationMs() - visible.duration);
    if (maxOffset <= 0) return false;
    return setWaveformOffset(timeMs - (visible.duration / 2), { persist });
  }

  function ensureWaveformTimeVisible(timeMs, { center = false, paddingRatio = 0.12, persist = true } = {}) {
    const visible = waveformWindow();
    const maxOffset = Math.max(0, durationMs() - visible.duration);
    if (!Number.isFinite(timeMs) || maxOffset <= 0) return false;
    if (center || timeMs < visible.start || timeMs > visible.end) {
      return centerWaveformOnTime(timeMs, { persist });
    }
    const padding = Math.min(visible.duration / 2, Math.max(20, visible.duration * paddingRatio));
    if (timeMs < visible.start + padding) return setWaveformOffset(timeMs - padding, { persist });
    if (timeMs > visible.end - padding) return setWaveformOffset(timeMs - visible.duration + padding, { persist });
    return false;
  }

  function waveformNavigatorMetrics(track = $("waveform-window-track")) {
    if (!track) return null;
    const visible = waveformWindow();
    const totalDuration = Math.max(1, durationMs());
    const rect = track.getBoundingClientRect();
    const trackWidth = Math.max(1, rect.width || track.clientWidth || 1);
    const maxOffset = Math.max(0, totalDuration - visible.duration);
    const idealHandleWidth = trackWidth * (visible.duration / totalDuration);
    const handleWidth = maxOffset <= 0
      ? trackWidth
      : clamp(
        Math.max(waveformWindowHandleMinPx, idealHandleWidth),
        waveformWindowHandleMinPx,
        trackWidth,
      );
    const maxLeft = Math.max(0, trackWidth - handleWidth);
    const left = maxLeft <= 0 ? 0 : (getWaveformOffsetMs() / maxOffset) * maxLeft;
    return { track, rect, trackWidth, totalDuration, visible, maxOffset, handleWidth, maxLeft, left };
  }

  function updateWaveformNavigator(clientX) {
    const metrics = waveformNavigatorMetrics();
    if (!metrics || metrics.maxOffset <= 0) return false;
    const ratio = clamp((clientX - metrics.rect.left) / metrics.trackWidth, 0, 1);
    return centerWaveformOnTime(ratio * metrics.totalDuration);
  }

  function waveformX(timeMs, width) {
    const visible = waveformWindow();
    return ((timeMs - visible.start) / visible.duration) * width;
  }

  function isWaveformVisible(timeMs) {
    const visible = waveformWindow();
    return timeMs >= visible.start && timeMs <= visible.end;
  }

  function waveformTime(event) {
    const rect = $("waveform").getBoundingClientRect();
    const x = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
    const visible = waveformWindow();
    return Math.round(visible.start + (x * visible.duration));
  }

  function shotPixelDistance(event, shot) {
    const rect = $("waveform").getBoundingClientRect();
    if (!isWaveformVisible(shot.time_ms)) return Number.POSITIVE_INFINITY;
    const shotX = waveformX(shot.time_ms, rect.width);
    return Math.abs((event.clientX - rect.left) - shotX);
  }

  function nearestShot(event) {
    const shots = currentState()?.project?.analysis?.shots || [];
    let nearest = null;
    let nearestDistance = Number.POSITIVE_INFINITY;
    shots.forEach((shot) => {
      const distance = shotPixelDistance(event, shot);
      if (distance < nearestDistance) {
        nearest = shot;
        nearestDistance = distance;
      }
    });
    return nearestDistance <= 28 ? nearest : null;
  }

  function nearestBeep(event) {
    const beep = currentState()?.project?.analysis?.beep_time_ms_primary;
    if (beep === null || beep === undefined) return null;
    const distance = shotPixelDistance(event, { time_ms: beep });
    return distance <= 28 ? { is_beep: true, time_ms: beep } : null;
  }

  return Object.freeze({
    durationMs,
    waveformWindow,
    persistWaveformViewport,
    setWaveformOffset,
    centerWaveformOnTime,
    ensureWaveformTimeVisible,
    waveformNavigatorMetrics,
    updateWaveformNavigator,
    waveformX,
    isWaveformVisible,
    waveformTime,
    shotPixelDistance,
    nearestShot,
    nearestBeep,
  });
}
