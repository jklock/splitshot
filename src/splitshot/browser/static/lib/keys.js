function emitBackbone(backbone, eventName, detail = undefined) {
  backbone?.bus?.emit?.(eventName, detail);
  return detail;
}

export function createKeyRuntime({
  backbone = null,
  runtime,
  selectedShot = () => null,
  activity = () => {},
  callApi = () => null,
  deleteShotById = () => null,
} = {}) {
  function moveSelectedShot(deltaMs) {
    const shot = selectedShot();
    if (!shot) return;
    emitBackbone(backbone, "keys.shot.nudge", { shot_id: shot.id, delta_ms: deltaMs });
    activity("shot.keyboard_nudge", { shot_id: shot.id, delta_ms: deltaMs });
    callApi("/api/shots/move", { shot_id: shot.id, time_ms: shot.time_ms + deltaMs, preserve_following_splits: true });
  }

  function deleteSelectedShot() {
    return deleteShotById(runtime.selectedShotId, "selected");
  }

  function keyboardEditTargetIsEditable(event) {
    const path = typeof event.composedPath === "function" ? event.composedPath() : [];
    const targets = [event.target, document.activeElement, ...path];
    return targets.some((target) => target instanceof Element && (
      target.isContentEditable
      || target.closest(".inspector, .modal, [role='dialog']")
      || ["INPUT", "SELECT", "TEXTAREA"].includes(target.tagName)
    ));
  }

  function handleKeyboardEdit(event) {
    if (!runtime.selectedShotId) return;
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      moveSelectedShot(event.shiftKey ? -10 : -1);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      moveSelectedShot(event.shiftKey ? 10 : 1);
    } else if (event.key === "Delete" || event.key === "Backspace") {
      event.preventDefault();
      deleteSelectedShot();
    }
  }

  return Object.freeze({
    moveSelectedShot,
    deleteSelectedShot,
    keyboardEditTargetIsEditable,
    handleKeyboardEdit,
  });
}
