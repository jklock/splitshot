const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const { setTimeout: delay } = require('node:timers/promises');
const { _electron: playwrightElectron } = require('playwright');
const electronBinary = require('electron');

const REPO = path.resolve(__dirname, '..', '..');
const ELECTRON_APP_DIR = path.resolve(REPO, 'electron');
const DEFAULT_PROJECT = path.resolve(REPO, '05072026');
const TMP_ROOT = path.resolve(REPO, 'tmp', 'codex');
const DEFAULT_TIMEOUT_MS = 180_000;

function proofId(prefix) {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(16).slice(2, 8)}`;
}

function parseArgs(argv) {
  const args = {
    scenarios: [],
    artifacts: path.resolve(REPO, 'artifacts', 'electron-iterate'),
    projectPath: DEFAULT_PROJECT,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--scenario') {
      args.scenarios.push(String(argv[index + 1] || '').trim());
      index += 1;
      continue;
    }
    if (arg === '--artifacts') {
      args.artifacts = path.resolve(String(argv[index + 1] || args.artifacts));
      index += 1;
      continue;
    }
    if (arg === '--project-path') {
      args.projectPath = path.resolve(String(argv[index + 1] || args.projectPath));
      index += 1;
    }
  }
  if (!args.scenarios.length) {
    args.scenarios = ['startup'];
  }
  return args;
}

function comparablePath(targetPath) {
  try {
    return fs.realpathSync(targetPath).replaceAll('\\', '/').toLowerCase();
  } catch {
    return path.resolve(targetPath).replaceAll('\\', '/').toLowerCase();
  }
}

function comparableBasename(targetPath) {
  return path.basename(targetPath || '').replaceAll('\\', '/').toLowerCase();
}

async function findFreePort() {
  const server = require('node:net').createServer();
  return new Promise((resolve, reject) => {
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      const port = typeof address === 'object' && address ? address.port : 0;
      server.close((error) => {
        if (error) {
          reject(error);
          return;
        }
        resolve(port);
      });
    });
    server.on('error', reject);
  });
}

async function closeApp(app) {
  const gracefulQuit = (async () => {
    try {
      await app.evaluate(async ({ app: electronApp }) => {
        electronApp.quit();
      });
    } catch (_error) {
    }
    await app.close();
  })();
  await Promise.race([
    gracefulQuit,
    delay(15_000).then(() => {
      app.process().kill();
    }),
  ]);
}

async function waitForStateProject(page, expectedProjectPath, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const expectedCanonicalPath = comparablePath(expectedProjectPath);
  const expectedBasename = comparableBasename(expectedProjectPath);
  const deadline = Date.now() + timeoutMs;
  let lastProjectPath = '';
  while (Date.now() < deadline) {
    try {
      const projectPath = await page.evaluate(async () => {
        const response = await fetch('/api/state');
        const state = await response.json();
        return state.project?.path || '';
      });
      lastProjectPath = projectPath || '';
      if (!projectPath) {
        await delay(250);
        continue;
      }
      const actualCanonicalPath = comparablePath(projectPath);
      const actualBasename = comparableBasename(projectPath);
      if (actualCanonicalPath === expectedCanonicalPath || actualBasename === expectedBasename) {
        return;
      }
    } catch {}
    await delay(250);
  }
  throw new Error(`Timed out waiting for project ${expectedProjectPath}; last seen=${lastProjectPath || '<empty>'}`);
}

async function waitForState(page, predicate, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const deadline = Date.now() + timeoutMs;
  let lastState = null;
  while (Date.now() < deadline) {
    lastState = await page.evaluate(async () => {
      const response = await fetch('/api/state');
      return await response.json();
    });
    if (predicate(lastState)) {
      return lastState;
    }
    await delay(250);
  }
  throw new Error(`State predicate timed out: ${JSON.stringify(lastState || {}, null, 2)}`);
}

async function callApi(page, route, payload) {
  const result = await page.evaluate(
    async ({ route, payload }) => {
      if (typeof callApi !== 'function') {
        throw new Error('callApi is not available.');
      }
      return await callApi(route, payload);
    },
    { route, payload },
  );
  if (!result || typeof result !== 'object') {
    throw new Error(`Unexpected API response for ${route}`);
  }
  return result;
}

async function currentState(page) {
  return page.evaluate(async () => {
    const response = await fetch('/api/state');
    return await response.json();
  });
}

async function setTool(page, tool) {
  await page.locator(`button[data-tool="${tool}"]`).click({ force: true });
  await page.waitForFunction(
    (targetTool) => {
      const inspector = document.querySelector('.inspector');
      const pane = document.querySelector(`[data-tool-pane="${targetTool}"]`);
      return inspector?.dataset?.activeTool === targetTool && pane?.classList?.contains('active') === true;
    },
    tool,
    { timeout: 15_000 },
  );
}

async function warmVisibleMedia(page) {
  await page.evaluate(async () => {
    const isVisible = (element) =>
      element instanceof HTMLElement &&
      !element.hidden &&
      element.offsetParent !== null &&
      window.getComputedStyle(element).display !== 'none' &&
      window.getComputedStyle(element).visibility !== 'hidden';
    const media = [
      document.getElementById('primary-video'),
      document.getElementById('secondary-video'),
      ...Array.from(document.querySelectorAll('#merge-preview-layer video')),
    ].filter((element) => element instanceof HTMLVideoElement && isVisible(element));
    for (const video of media) {
      if (!video.currentSrc) continue;
      try {
        video.muted = true;
        const playAttempt = video.play();
        if (playAttempt && typeof playAttempt.then === 'function') {
          await Promise.race([playAttempt.catch(() => {}), new Promise((resolve) => window.setTimeout(resolve, 500))]);
        }
      } catch (_error) {
      } finally {
        try {
          video.pause();
        } catch (_error) {}
      }
    }
  });
}

async function scenarioStartup(page, metrics) {
  const started = Date.now();
  await page.waitForLoadState('domcontentloaded', { timeout: DEFAULT_TIMEOUT_MS });
  await page.waitForSelector('#current-file', { timeout: DEFAULT_TIMEOUT_MS });
  await waitForStateProject(page, metrics.projectPath);
  metrics.firstPaneReadyMs = metrics.firstPaneReadyMs || (Date.now() - metrics.launchStartMs);
  return { projectLoaded: true, durationMs: Date.now() - started };
}

async function scenarioProject(page) {
  await setTool(page, 'project');
  const nextName = proofId('proof-project');
  const nextDescription = `Description ${nextName}`;
  await callApi(page, '/api/project/details', {
    name: nextName,
    description: nextDescription,
  });
  await page.waitForFunction(
    ({ expectedName, expectedDescription }) => {
      const nameInput = document.getElementById('project-name');
      const descriptionInput = document.getElementById('project-description');
      return nameInput?.value === expectedName && descriptionInput?.value === expectedDescription;
    },
    { expectedName: nextName, expectedDescription: nextDescription },
    { timeout: 30_000 },
  );
  const summary = await page.evaluate(() => ({
    name: document.getElementById('project-name')?.value || '',
    description: document.getElementById('project-description')?.value || '',
    projectPath: document.getElementById('project-path')?.value || '',
  }));
  assert.equal(summary.name, nextName);
  assert.equal(summary.description, nextDescription);
  assert.ok(summary.projectPath.length > 0);
  return summary;
}

async function scenarioMedia(page) {
  await setTool(page, 'media');
  const originalState = await currentState(page);
  const originalStageId = String(originalState.project?.active_stage_id || '');
  const originalPrimaryPath = String(originalState.project?.primary_video?.path || '');
  assert.ok(originalStageId, 'Expected an active stage for Media proof');
  assert.ok(originalPrimaryPath, 'Expected active-stage primary media for Media proof');

  await callApi(page, '/api/project/stage/create', { label: 'Stage 3 Empty Proof' });
  const emptyState = await waitForState(
    page,
    (currentState) => (
      String(currentState.project?.active_stage_id || '') !== originalStageId
      && !String(currentState.project?.primary_video?.path || '')
    ),
    30_000,
  );
  const emptyStageId = String(emptyState.project?.active_stage_id || '');
  assert.ok(emptyStageId, 'Expected the new empty stage to become active');

  await page.locator('#media-active-stage-select').selectOption(originalStageId);
  await waitForState(
    page,
    (currentState) => (
      String(currentState.project?.active_stage_id || '') === originalStageId
      && String(currentState.project?.primary_video?.path || '') === originalPrimaryPath
    ),
    30_000,
  );
  await page.locator('#media-active-stage-select').selectOption(emptyStageId);
  await waitForState(
    page,
    (currentState) => (
      String(currentState.project?.active_stage_id || '') === emptyStageId
      && !String(currentState.project?.primary_video?.path || '')
    ),
    30_000,
  );
  await page.waitForFunction(
    (stageId) => (
      document.getElementById('media-active-stage-select')?.value === stageId
      && !document.querySelector('.media-asset-row[data-source-id="primary"]')
      && document.querySelector('.media-add-primary-btn')?.textContent?.trim() === 'Add Primary'
    ),
    emptyStageId,
    { timeout: 30_000 },
  );

  const summary = await page.evaluate(() => {
    const pane = document.querySelector('[data-tool-pane="media"]');
    const sections = Array.from(pane?.querySelectorAll('.media-pane-section') || []);
    const activeStageSection = sections[0] || null;
    const primarySection = sections[1] || null;
    const addStage = pane?.querySelector('.media-add-stage-btn');
    const actionRow = pane?.querySelector('.media-active-stage-actions');
    const primaryRow = pane?.querySelector('.media-asset-row[data-source-id="primary"]');
    const saveButton = pane?.querySelector('.media-save-stage-btn');
    const deleteButton = pane?.querySelector('.media-delete-stage-btn');
    const addMediaButton = pane?.querySelector('.media-add-more-btn');
    const addPrimaryButton = pane?.querySelector('.media-add-primary-btn');
    const primaryToggle = primarySection?.querySelector('.media-section-toggle');
    const addPrimaryRect = addPrimaryButton?.getBoundingClientRect() || null;
    const primaryToggleRect = primaryToggle?.getBoundingClientRect() || null;
    return {
      addStageInsideActiveStage: Boolean(activeStageSection && addStage && activeStageSection.contains(addStage)),
      addStageAfterActionRow: Boolean(actionRow && addStage && actionRow.nextElementSibling === addStage),
      saveDeleteGrouped: Boolean(actionRow && saveButton && deleteButton && actionRow.contains(saveButton) && actionRow.contains(deleteButton)),
      hasPrimaryRow: Boolean(primaryRow),
      primaryText: primaryRow?.textContent?.replace(/\s+/g, ' ').trim() || '',
      addPrimaryText: addPrimaryButton?.textContent?.trim() || '',
      addPrimaryInHeader: Boolean(primarySection && addPrimaryButton && primarySection.querySelector('.section-header-actions')?.contains(addPrimaryButton)),
      addPrimaryInBody: Boolean(primarySection?.querySelector('.media-pane-section-body .media-add-primary-btn')),
      emptyPrimaryText: primarySection?.querySelector('.media-pane-section-body')?.textContent?.replace(/\s+/g, ' ').trim() || '',
      addMediaEnabled: addMediaButton instanceof HTMLButtonElement && !addMediaButton.disabled,
      actionClearance: addPrimaryRect && primaryToggleRect
        ? primaryToggleRect.left - addPrimaryRect.right
        : null,
      intakeButtonsMatch: !addPrimaryButton || !addMediaButton || (
        Math.abs(addPrimaryButton.getBoundingClientRect().width - addMediaButton.getBoundingClientRect().width) <= 1
        && Math.abs(addPrimaryButton.getBoundingClientRect().height - addMediaButton.getBoundingClientRect().height) <= 1
      ),
    };
  });
  assert.equal(summary.addStageInsideActiveStage, true);
  assert.equal(summary.addStageAfterActionRow, true);
  assert.equal(summary.saveDeleteGrouped, true);
  assert.equal(summary.hasPrimaryRow, false);
  assert.equal(summary.addPrimaryText, 'Add Primary');
  assert.equal(summary.addPrimaryInHeader, true);
  assert.equal(summary.addPrimaryInBody, false);
  assert.equal(summary.emptyPrimaryText, 'No primary media.');
  assert.equal(summary.addMediaEnabled, false);
  assert.ok(summary.actionClearance >= 7, `Expected >=7px between Add Primary and disclosure, got ${summary.actionClearance}`);
  assert.equal(summary.intakeButtonsMatch, true);

  await page.locator('#media-active-stage-select').selectOption(originalStageId);
  await waitForState(
    page,
    (currentState) => (
      String(currentState.project?.active_stage_id || '') === originalStageId
      && String(currentState.project?.primary_video?.path || '') === originalPrimaryPath
    ),
    30_000,
  );
  await page.waitForFunction(
    (stageId) => (
      document.getElementById('media-active-stage-select')?.value === stageId
      && Boolean(document.querySelector('.media-asset-row[data-source-id="primary"]'))
    ),
    originalStageId,
    { timeout: 30_000 },
  );
  const populatedSummary = await page.evaluate(() => ({
    hasPrimaryRow: Boolean(document.querySelector('.media-asset-row[data-source-id="primary"]')),
    replaceInAssetActions: Boolean(document.querySelector('.media-asset-row[data-source-id="primary"] .media-asset-actions .media-replace-primary-btn')),
    addMediaEnabled: document.querySelector('.media-add-more-btn') instanceof HTMLButtonElement
      && !document.querySelector('.media-add-more-btn').disabled,
  }));
  assert.equal(populatedSummary.hasPrimaryRow, true);
  assert.equal(populatedSummary.replaceInAssetActions, true);
  assert.equal(populatedSummary.addMediaEnabled, true);
  await callApi(page, '/api/project/stage/delete', { stage_id: emptyStageId });
  return { ...summary, populated: populatedSummary };
}

async function scenarioCompose(page) {
  await setTool(page, 'merge');
  await page.evaluate(() => {
    document.documentElement.style.setProperty('--inspector-width', '520px');
    window.dispatchEvent(new Event('resize'));
  });
  await warmVisibleMedia(page);
  const before = await page.evaluate(() => {
    const source = (state?.project?.merge_sources || [])[0] || null;
    return String(source?.placement_mode || source?.placement?.mode || '');
  });
  const nextLayout = before === 'pip' ? 'side_by_side' : 'pip';
  await callApi(page, '/api/merge/source', { source_id: String((await page.evaluate(() => (state?.project?.merge_sources || [])[0]?.id || ''))), placement_mode: nextLayout, enabled: true });
  const stateAfter = await waitForState(page, (currentState) => {
    const source = (currentState.project?.merge_sources || [])[0] || null;
    return String(source?.placement_mode || source?.placement?.mode || '') === nextLayout;
  });
  await page.evaluate(() => {
    document.documentElement.style.setProperty('--inspector-width', '520px');
    window.dispatchEvent(new Event('resize'));
  });
  await page.waitForTimeout(100);
  const gridColumns = await page.evaluate(() => {
    const control = document.querySelector('.merge-source-controls');
    if (!(control instanceof HTMLElement)) return 0;
    return String(window.getComputedStyle(control).gridTemplateColumns || '').split(' ').filter(Boolean).length;
  });
  assert.equal(String((stateAfter.project?.merge_sources || [])[0]?.placement_mode || (stateAfter.project?.merge_sources || [])[0]?.placement?.mode || ''), nextLayout);
  assert.ok(gridColumns >= 2, `Expected normal-width compose controls to render in >=2 columns, got ${gridColumns}`);
  let pipControlClearance = null;
  if (nextLayout === 'pip') {
    await page.evaluate(() => {
      const showPip = document.getElementById('show-pip');
      if (showPip instanceof HTMLInputElement) showPip.checked = true;
      if (state?.project?.merge) state.project.merge.enabled = true;
      const source = (state?.project?.merge_sources || [])[0];
      if (source) source.enabled = true;
      const video = document.getElementById('primary-video');
      const stage = document.getElementById('video-stage');
      renderMergePreviewLayer(video, stage, state.project.merge_sources, state.project.merge.pip_size_percent);
    });
    await page.locator('#merge-preview-layer .merge-preview-item').first().waitFor({ state: 'visible', timeout: 30_000 });
    pipControlClearance = await page.evaluate(() => {
      const video = document.getElementById('primary-video')?.getBoundingClientRect();
      const pip = document.querySelector('#merge-preview-layer .merge-preview-item')?.getBoundingClientRect();
      return video && pip ? video.bottom - pip.bottom : null;
    });
    assert.ok(pipControlClearance >= 40, `Expected PiP to clear video controls by >=40px, got ${pipControlClearance}`);
  }
  return { layout: nextLayout, gridColumns, pipControlClearance };
}

async function scenarioTrim(page) {
  await setTool(page, 'trim-sync');
  await callApi(page, '/api/merge/source/trim-all', {
    keep_before_beep_s: 2,
    keep_after_last_shot_s: 2,
    clear: false,
  });
  const applied = await waitForState(
    page,
    (currentState) => {
      const primaryTrimActive = Boolean(currentState.project?.primary_video?.trim_active);
      const sources = Array.isArray(currentState.project?.merge_sources) ? currentState.project.merge_sources : [];
      return primaryTrimActive && sources.length > 0 && sources.every((source) => Boolean(source?.trim_active));
    },
    DEFAULT_TIMEOUT_MS,
  );
  const summary = {
    primaryTrimActive: Boolean(applied?.project?.primary_video?.trim_active),
    mergeTrimActiveCount: Number((applied?.project?.merge_sources || []).filter((source) => source?.trim_active).length || 0),
  };
  assert.equal(summary.primaryTrimActive, true);
  assert.ok(summary.mergeTrimActiveCount > 0);
  return summary;
}

async function scenarioScore(page) {
  await setTool(page, 'scoring');
  const stateBefore = await currentState(page);
  const presets = Array.isArray(stateBefore.scoring_presets) ? stateBefore.scoring_presets : [];
  const currentRuleset = String(stateBefore.project?.scoring?.ruleset || '');
  const nextPreset = presets.find((preset) => preset.id !== currentRuleset) || presets[0];
  assert.ok(nextPreset, 'Expected at least one scoring preset');
  await callApi(page, '/api/scoring/profile', { ruleset: nextPreset.id });
  await page.waitForFunction(
    ({ expectedValue }) => {
      const select = document.getElementById('scoring-preset');
      return select?.value === expectedValue;
    },
    { expectedValue: nextPreset.id },
    { timeout: 30_000 },
  );
  const summary = await page.evaluate(() => ({
    preset: document.getElementById('scoring-preset')?.value || '',
    description: document.getElementById('scoring-description')?.textContent?.trim() || '',
    result: document.getElementById('scoring-result')?.textContent?.trim() || '',
  }));
  assert.equal(summary.preset, nextPreset.id);
  assert.ok(summary.description.length > 0);
  assert.ok(summary.result.length > 0);
  return summary;
}

async function scenarioSplits(page) {
  await setTool(page, 'timing');
  await page.locator('#expand-timing').click({ force: true });
  const stateBefore = await currentState(page);
  const firstShotId = String((stateBefore.split_rows || []).find((row) => row?.shot_id)?.shot_id || '');
  assert.ok(firstShotId, 'Expected a first shot id for timing event proof');
  const label = proofId('event');
  await callApi(page, '/api/events/add', {
    kind: 'custom_label',
    label,
    after_shot_id: firstShotId,
    before_shot_id: '',
  });
  await page.waitForFunction(
    (expectedLabel) => (document.getElementById('timing-event-list')?.innerText || '').includes(expectedLabel),
    label,
    { timeout: 30_000 },
  );
  const summary = await page.evaluate(() => ({
    eventsText: document.getElementById('timing-event-list')?.innerText || '',
    eventCount: document.querySelectorAll('#timing-event-list .timing-event-chip, #timing-event-list .timing-event-row').length,
  }));
  assert.ok(summary.eventsText.includes(label));
  return { ...summary, label };
}

async function scenarioMarkers(page) {
  await setTool(page, 'markers');
  const beforeCount = await page.evaluate(() => document.querySelectorAll('#popup-marker-list .popup-marker-row').length);
  await page.locator('#popup-add-bubble').click({ force: true });
  await page.waitForFunction(
    (expectedCount) => document.querySelectorAll('#popup-marker-list .popup-marker-row').length === expectedCount,
    beforeCount + 1,
    { timeout: 30_000 },
  );
  await page.locator('#popup-edit-selected').click({ force: true });
  await page.waitForFunction(
    () => document.getElementById('popup-selected-editor-panel')?.hidden === false,
    { timeout: 30_000 },
  );
  const summary = await page.evaluate(() => ({
    listCount: document.querySelectorAll('#popup-marker-list .popup-marker-row').length,
    editorVisible: document.getElementById('popup-selected-editor-panel')?.hidden === false,
    editorCardCount: document.querySelectorAll('#markers-workbench-editor .popup-bubble-card').length,
  }));
  assert.equal(summary.listCount, beforeCount + 1);
  assert.equal(summary.editorVisible, true);
  assert.ok(summary.editorCardCount >= 1);
  return summary;
}

async function scenarioOverlay(page) {
  await setTool(page, 'overlay');
  const currentSize = await page.locator('#badge-size').inputValue();
  const nextSize = ['XS', 'S', 'M', 'L', 'XL'].find((value) => value !== currentSize) || 'L';
  await page.locator('#badge-size').selectOption(nextSize);
  await waitForState(
    page,
    (state) => String(state.project?.overlay?.badge_size || '') === nextSize,
    30_000,
  );
  await page.waitForFunction(
    (expectedClass) => {
      const badge = document.querySelector('.overlay-badge');
      return badge?.className?.includes(expectedClass) === true;
    },
    `badge-${nextSize}`,
    { timeout: 30_000 },
  );
  const summary = await page.evaluate(() => ({
    badgeSize: document.getElementById('badge-size')?.value || '',
    badgeClass: document.querySelector('.overlay-badge')?.className || '',
  }));
  assert.equal(summary.badgeSize, nextSize);
  assert.ok(summary.badgeClass.includes(`badge-${nextSize}`));
  const scoreToggle = page.locator('#show-shot-scores');
  const previousShotScores = await scoreToggle.isChecked();
  await scoreToggle.setChecked(!previousShotScores);
  await waitForState(page, (state) => Boolean(state.project?.overlay?.show_shot_scores) === !previousShotScores, 30_000);
  assert.equal(await scoreToggle.isChecked(), !previousShotScores);
  return { ...summary, showShotScores: !previousShotScores };
}

async function scenarioReview(page) {
  await setTool(page, 'review');
  const beforeCount = await page.evaluate(() => document.querySelectorAll('#review-text-box-list .text-box-card').length);
  await page.locator('#review-add-text-box').click({ force: true });
  await page.waitForFunction(
    (expectedCount) => document.querySelectorAll('#review-text-box-list .text-box-card').length === expectedCount,
    beforeCount + 1,
    { timeout: 30_000 },
  );
  const summary = await page.evaluate(() => ({
    cardCount: document.querySelectorAll('#review-text-box-list .text-box-card').length,
    firstCardText: document.querySelector('#review-text-box-list .text-box-card')?.textContent?.replace(/\s+/g, ' ').trim() || '',
  }));
  assert.equal(summary.cardCount, beforeCount + 1);
  assert.ok(summary.firstCardText.includes('Custom Box'));
  return summary;
}

async function scenarioQueue(page) {
  const stageIds = await page.evaluate(() => (state?.project?.stages || []).map((stage) => String(stage.id || '')));
  for (const stageId of stageIds) {
    await callApi(page, '/api/project/queue/add', { stage_id: stageId });
  }
  await setTool(page, 'queue');
  const summary = await waitForState(
    page,
    (currentState) => Array.isArray(currentState.project?.queue) && currentState.project.queue.length === stageIds.length,
    30_000,
  );
  return {
    queued: (summary.project?.queue || []).length,
    statuses: (summary.project?.queue || []).map((entry) => entry.status),
  };
}

async function scenarioExport(page) {
  await setTool(page, 'export');
  const currentQuality = await page.locator('#quality').inputValue();
  const nextQuality = ['high', 'medium', 'low'].find((value) => value !== currentQuality) || 'low';
  await page.locator('#quality').selectOption(nextQuality);
  await waitForState(
    page,
    (state) => String(state.project?.export?.quality || '') === nextQuality,
    30_000,
  );
  const summary = await page.evaluate(() => ({
    quality: document.getElementById('quality')?.value || '',
    aspectRatio: document.getElementById('aspect-ratio')?.value || '',
  }));
  assert.equal(summary.quality, nextQuality);
  return summary;
}

async function scenarioMetrics(page) {
  await setTool(page, 'metrics');
  const stateBefore = await currentState(page);
  const firstShotRow = (stateBefore.split_rows || []).find((row) => row?.shot_id) || null;
  const firstShotLabel = String(firstShotRow?.shot_number ? `Shot ${firstShotRow.shot_number}` : '');
  const firstShotId = String(firstShotRow?.shot_id || '');
  const currentRuleset = String(stateBefore.project?.scoring?.ruleset || '');
  const preset = (stateBefore.scoring_presets || []).find((candidate) => candidate?.id === currentRuleset) || null;
  const scoreOptions = Array.isArray(preset?.score_options) ? preset.score_options.map((value) => String(value || '')).filter(Boolean) : [];
  const currentLetter = String(((stateBefore.timing_segments || []).find((segment) => segment?.shot_id === firstShotId)?.score_letter) || '');
  const nextLetter = scoreOptions.find((value) => value !== currentLetter) || '';
  assert.ok(firstShotLabel, 'Expected a first shot label for metrics proof');
  assert.ok(firstShotId, 'Expected a first shot id for metrics proof');
  assert.ok(nextLetter, 'Expected an alternate valid score token for metrics proof');
  await callApi(page, '/api/scoring/score', {
    shot_id: firstShotId,
    letter: nextLetter,
    penalty_counts: {},
  });
  await page.waitForFunction(
    ({ expectedLabel, expectedLetter }) => {
      const cells = Array.from(document.querySelectorAll('#metrics-trend-list > div')).map((cell) => cell.textContent?.trim() || '');
      for (let index = 6; index < cells.length; index += 6) {
        if (cells[index].includes(expectedLabel)) {
          return cells[index + 3] === expectedLetter;
        }
      }
      return false;
    },
    { expectedLabel: firstShotLabel, expectedLetter: nextLetter },
    { timeout: 30_000 },
  );
  const summary = await page.evaluate((expectedLabel) => {
    const cells = Array.from(document.querySelectorAll('#metrics-trend-list > div')).map((cell) => cell.textContent?.trim() || '');
    let matchingRow = [];
    for (let index = 6; index < cells.length; index += 6) {
      if (cells[index].includes(expectedLabel)) {
        matchingRow = cells.slice(index, index + 6);
        break;
      }
    }
    return {
      matchingTrendRow: matchingRow,
      summaryCards: document.querySelectorAll('#metrics-summary-grid > *').length,
      competitionCards: Array.from(document.querySelectorAll('#metrics-competition-summary > *')).map((card) => card.textContent?.replace(/\s+/g, ' ').trim() || ''),
    };
  }, firstShotLabel);
  assert.ok(summary.summaryCards > 0);
  assert.equal(summary.competitionCards.length, 3);
  assert.ok(summary.matchingTrendRow.length === 6, 'Expected the metrics trend table to render a visible row for the first shot');
  assert.equal(summary.matchingTrendRow[3], nextLetter);
  return { ...summary, shotLabel: firstShotLabel, scoreLetter: nextLetter };
}

async function scenarioShotML(page) {
  await setTool(page, 'shotml');
  const stateBefore = await currentState(page);
  const currentThreshold = Number(stateBefore.project?.analysis?.shotml_settings?.detection_threshold || 0.35);
  const nextThreshold = Number((currentThreshold >= 0.4 ? 0.35 : 0.4).toFixed(2));
  await callApi(page, '/api/analysis/shotml-settings', {
    settings: {
      ...(stateBefore.project?.analysis?.shotml_settings || {}),
      detection_threshold: nextThreshold,
    },
    rerun: false,
  });
  await page.waitForFunction(
    (expectedValue) => {
      const input = document.getElementById('threshold');
      return Number(input?.value || 0) === expectedValue;
    },
    nextThreshold,
    { timeout: 30_000 },
  );
  const summary = await page.evaluate(() => ({
    threshold: Number(document.getElementById('threshold')?.value || 0),
    proposalSummary: document.getElementById('shotml-proposal-summary')?.textContent?.trim() || '',
  }));
  assert.equal(summary.threshold, nextThreshold);
  return summary;
}

async function scenarioSettings(page) {
  await setTool(page, 'settings');
  const section = page.locator('[data-settings-section="global-template"]');
  const scopeSelect = page.locator('#settings-scope');
  if (!(await scopeSelect.isVisible())) {
    await section.locator('[data-section-toggle]').click({ force: true });
    await scopeSelect.waitFor({ state: 'visible', timeout: 30_000 });
  }
  await page.locator('#settings-scope').selectOption('folder');
  await page.locator('#settings-default-tool').selectOption('metrics');
  await page.locator('#settings-import-current').click({ force: true });
  await waitForState(
    page,
    (state) => String(state.settings_layers?.folder?.default_tool || '') === 'metrics',
    30_000,
  );
  const summary = await page.evaluate(() => ({
    scope: document.getElementById('settings-scope')?.value || '',
    defaultTool: document.getElementById('settings-default-tool')?.value || '',
    status: document.getElementById('settings-scope-status')?.textContent?.trim() || '',
  }));
  assert.equal(summary.scope, 'folder');
  assert.equal(summary.defaultTool, 'metrics');
  return summary;
}

const SCENARIOS = {
  startup: scenarioStartup,
  project: scenarioProject,
  media: scenarioMedia,
  compose: scenarioCompose,
  trim: scenarioTrim,
  score: scenarioScore,
  splits: scenarioSplits,
  markers: scenarioMarkers,
  overlay: scenarioOverlay,
  review: scenarioReview,
  export: scenarioExport,
  queue: scenarioQueue,
  metrics: scenarioMetrics,
  shotml: scenarioShotML,
  settings: scenarioSettings,
};

async function main() {
  const args = parseArgs(process.argv.slice(2));
  fs.mkdirSync(args.artifacts, { recursive: true });
  fs.mkdirSync(TMP_ROOT, { recursive: true });
  const readyFile = path.join(fs.mkdtempSync(path.join(TMP_ROOT, 'splitshot-electron-iterate-ready-')), 'events.jsonl');
  const port = await findFreePort();
  const env = {
    ...process.env,
    CI: '1',
    SPLITSHOT_ELECTRON_TEST: '1',
    SPLITSHOT_ELECTRON_READY_FILE: readyFile,
    SPLITSHOT_TEST_PORT: String(port),
  };

  const electronApp = await playwrightElectron.launch({
    executablePath: electronBinary,
    args: [ELECTRON_APP_DIR, args.projectPath],
    cwd: ELECTRON_APP_DIR,
    env,
    timeout: DEFAULT_TIMEOUT_MS,
  });

  const metrics = {
    launchStartMs: Date.now(),
    port,
    projectPath: args.projectPath,
    scenarios: {},
  };

  try {
    const page = await electronApp.firstWindow({ timeout: DEFAULT_TIMEOUT_MS });
    await page.waitForLoadState('domcontentloaded', { timeout: DEFAULT_TIMEOUT_MS });
    await waitForStateProject(page, args.projectPath);
    metrics.backendReadyMs = Date.now() - metrics.launchStartMs;
    metrics.windowReadyMs = metrics.backendReadyMs;
    metrics.firstPaneReadyMs = metrics.backendReadyMs;

    for (const scenario of args.scenarios) {
      const handler = SCENARIOS[scenario];
      if (!handler) {
        throw new Error(`Unknown scenario: ${scenario}`);
      }
      const started = Date.now();
      const result = await handler(page, metrics);
      metrics.scenarios[scenario] = {
        durationMs: Date.now() - started,
        result,
      };
    }

    const output = {
      tier: 'source',
      projectPath: args.projectPath,
      metrics,
    };
    fs.writeFileSync(path.join(args.artifacts, 'source-electron-iterate.json'), JSON.stringify(output, null, 2));
    console.log(JSON.stringify(output, null, 2));
  } finally {
    await closeApp(electronApp);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
