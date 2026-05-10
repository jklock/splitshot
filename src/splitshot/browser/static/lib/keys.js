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
  getState = () => null,
} = {}) {
  function selectedBeep() {
    return getState()?.project?.analysis?.beep_time_ms_primary ?? null;
  }

  function moveSelectedShot(deltaMs) {
    const shot = selectedShot();
    if (shot) {
      emitBackbone(backbone, "keys.shot.nudge", { shot_id: shot.id, delta_ms: deltaMs });
      activity("shot.keyboard_nudge", { shot_id: shot.id, delta_ms: deltaMs });
      callApi("/api/shots/move", { shot_id: shot.id, time_ms: shot.time_ms + deltaMs, preserve_following_splits: true });
      return;
    }
    const beep = selectedBeep();
    if (beep !== null && beep !== undefined) {
      activity("beep.keyboard_nudge", { time_ms: beep + deltaMs });
      callApi("/api/beep", { time_ms: beep + deltaMs });
    }
  }

  function deleteSelectedShot() {
    if (runtime.selectedShotId) {
      return deleteShotById(runtime.selectedShotId, "selected");
    }
    const beep = selectedBeep();
    if (beep !== null && beep !== undefined) {
      activity("beep.keyboard_delete", {});
      callApi("/api/beep", { time_ms: null });
    }
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
