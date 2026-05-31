const fs = require('fs');
const path = require('path');

const PRACTISCORE_DASHBOARD_URL = 'https://practiscore.com/dashboard/home';
const PRACTISCORE_MATCHES_URL = 'https://practiscore.com/dashboard/matches';
const PRACTISCORE_PARTITION = 'persist:splitshot-practiscore-host-v1';
const EXPIRED_AUTHENTICATION_ERROR = 'expired_authentication';
const MALFORMED_REMOTE_RESPONSE_ERROR = 'malformed_remote_response';
const MISSING_REQUIRED_REMOTE_ARTIFACT_ERROR = 'missing_required_remote_artifact';
const TRANSIENT_NETWORK_FAILURE_ERROR = 'transient_network_failure';
const DEFAULT_STUB_MATCH = {
  remote_id: 'match-electron-200',
  label: 'Electron IDPA Match',
  match_type: 'idpa',
  event_name: 'Electron IDPA Match',
  event_date: '2026-05-29',
  details_url: `${PRACTISCORE_MATCHES_URL}/match-electron-200`,
};
const AUTH_STATE_SCRIPT = `(() => {
  const currentUrl = String(location.href || '');
  const bodyText = (document.body?.innerText || '').toLowerCase();
  const title = document.title || '';
  const heading = document.querySelector('h1, h2')?.textContent?.trim() || '';
  const challengeRequired = /challenge|captcha|verify/i.test(currentUrl)
    || /security challenge|captcha|verify you are human/.test(bodyText);
  const loginRequired = /login|signin|authenticate/i.test(currentUrl)
    || /sign in|log in|authentication/.test(bodyText);
  return {
    current_url: currentUrl,
    page_title: title,
    page_heading: heading,
    challenge_required: challengeRequired,
    authenticated: !challengeRequired && !loginRequired,
  };
})()`;
const DISCOVER_MATCHES_SCRIPT = `(() => {
  const inferMatchType = (text) => {
    const value = String(text || '').toLowerCase();
    if (value.includes('steel challenge') || value.includes('scsa')) return 'scsa';
    if (value.includes('idpa')) return 'idpa';
    if (value.includes('uspsa')) return 'uspsa';
    return '';
  };
  const anchors = [...document.querySelectorAll('a[href*="/dashboard/matches/"]')];
  const seen = new Set();
  return anchors.map((anchor) => {
    try {
      const detailsUrl = new URL(anchor.href, location.href).toString();
      const pathnameParts = new URL(detailsUrl).pathname.split('/').filter(Boolean);
      const remoteId = pathnameParts[pathnameParts.length - 1] || '';
      if (!remoteId || seen.has(remoteId)) return null;
      seen.add(remoteId);
      const card = anchor.closest('article, li, tr, .card, .match, [data-match-id]') || anchor;
      const label = (
        card.querySelector('h1, h2, h3, h4, strong, .title, .card-title')?.textContent
        || anchor.textContent
        || remoteId
      ).trim();
      const eventDate = (
        card.querySelector('time')?.getAttribute('datetime')
        || card.querySelector('time')?.textContent
        || ''
      ).trim();
      return {
        remote_id: remoteId,
        label,
        match_type: inferMatchType(label),
        event_name: label,
        event_date: eventDate,
        details_url: detailsUrl,
      };
    } catch {
      return null;
    }
  }).filter(Boolean);
})()`;
const SELECTED_MATCH_SNAPSHOT_SCRIPT = `(() => ({
  page_url: String(location.href || ''),
  page_title: document.title || '',
  page_heading: document.querySelector('h1, h2')?.textContent?.trim() || '',
}))()`;
const FETCH_ARTIFACT_SCRIPT = `(() => {
  const anchors = [...document.querySelectorAll('a[href]')];
  const candidate = anchors.find((anchor) => {
    const href = String(anchor.href || '').toLowerCase();
    const text = String(anchor.textContent || '').toLowerCase();
    return href.endsWith('.csv')
      || href.endsWith('.txt')
      || (text.includes('csv') && href.includes('download'))
      || (text.includes('txt') && href.includes('download'))
      || text.includes('export match results');
  });
  if (!candidate) {
    return { error: 'missing_artifact' };
  }
  const sourceName = candidate.getAttribute('download')
    || candidate.href.split('/').filter(Boolean).pop()
    || 'remote-practiscore.csv';
  return fetch(candidate.href, { credentials: 'include' })
    .then(async (response) => ({
      ok: response.ok,
      status: response.status,
      final_url: response.url,
      source_name: sourceName,
      content_type: response.headers.get('content-type') || '',
      artifact_text: await response.text(),
    }))
    .catch((error) => ({ error: String(error?.message || error || 'download_failed') }));
})()`;

function defaultSessionPayload() {
  return {
    state: 'not_authenticated',
    message: 'Connect PractiScore to use your browser session for background sync.',
    details: {},
  };
}

function defaultSyncPayload() {
  return {
    state: 'idle',
    message: 'No remote PractiScore sync activity yet.',
    matches: [],
    selected_remote_id: null,
    error_category: '',
    details: {},
  };
}

function normalizeSessionPayload(payload) {
  const fallback = defaultSessionPayload();
  const source = payload && typeof payload === 'object' ? payload : {};
  const details = source.details && typeof source.details === 'object' ? source.details : {};
  return {
    state: String(source.state || fallback.state),
    message: String(source.message || fallback.message),
    details: { ...details },
  };
}

function normalizeSyncPayload(payload, existingPayload = defaultSyncPayload()) {
  const fallback = defaultSyncPayload();
  const source = payload && typeof payload === 'object' ? payload : {};
  const matches = Array.isArray(source.matches) ? source.matches : existingPayload.matches || fallback.matches;
  return {
    state: String(source.state || fallback.state),
    message: String(source.message || fallback.message),
    matches: matches.map((item) => ({ ...item })),
    selected_remote_id: source.selected_remote_id == null || source.selected_remote_id === ''
      ? null
      : String(source.selected_remote_id),
    error_category: String(source.error_category || ''),
    details: source.details && typeof source.details === 'object' ? { ...source.details } : {},
  };
}

function inferMatchType(text) {
  const value = String(text || '').toLowerCase();
  if (value.includes('steel challenge') || value.includes('scsa')) return 'scsa';
  if (value.includes('idpa')) return 'idpa';
  if (value.includes('uspsa')) return 'uspsa';
  return '';
}

function normalizeMatch(rawMatch) {
  if (!rawMatch || typeof rawMatch !== 'object') return null;
  const remoteId = String(rawMatch.remote_id || '').trim();
  if (!remoteId) return null;
  const label = String(rawMatch.label || rawMatch.event_name || remoteId).trim() || remoteId;
  return {
    remote_id: remoteId,
    label,
    match_type: String(rawMatch.match_type || inferMatchType(label)).trim(),
    event_name: String(rawMatch.event_name || label).trim() || label,
    event_date: String(rawMatch.event_date || '').trim(),
    details_url: typeof rawMatch.details_url === 'string' ? rawMatch.details_url : '',
  };
}

function normalizeMatches(items) {
  if (!Array.isArray(items)) return [];
  const seen = new Set();
  const matches = [];
  for (const item of items) {
    const match = normalizeMatch(item);
    if (!match || seen.has(match.remote_id)) continue;
    seen.add(match.remote_id);
    matches.push(match);
  }
  return matches;
}

function errorCategoryFromMessage(message) {
  const value = String(message || '').toLowerCase();
  if (value.includes('timeout') || value.includes('timed out') || value.includes('network')) {
    return TRANSIENT_NETWORK_FAILURE_ERROR;
  }
  return MALFORMED_REMOTE_RESPONSE_ERROR;
}

function pageLooksUnauthenticated(pageState, currentUrl) {
  const url = String(currentUrl || pageState?.current_url || '').toLowerCase();
  if (pageState?.challenge_required) return 'challenge_required';
  if (/login|signin|authenticate/.test(url)) return 'authenticating';
  if (pageState && pageState.authenticated === false) return 'authenticating';
  return '';
}

function createPractiScoreHost({ enabled, BrowserWindow, session, getParentWindow }) {
  const hostSession = session.fromPartition(PRACTISCORE_PARTITION, { cache: true });
  const stubFixturePath = process.env.SPLITSHOT_ELECTRON_TEST_PRACTISCORE_HOST_FIXTURE || '';
  const stubEnabled = Boolean(process.env.SPLITSHOT_ELECTRON_TEST === '1' && stubFixturePath);
  let authWindow = null;
  let workerWindow = null;
  let sessionPayload = defaultSessionPayload();
  let syncPayload = defaultSyncPayload();
  let lastMatches = [];

  function featureState() {
    return {
      enabled: Boolean(enabled),
      mode: !enabled ? 'disabled' : (stubEnabled ? 'test_fixture' : 'electron_practiscore_host_v1'),
    };
  }

  function setSessionPayload(nextPayload) {
    sessionPayload = normalizeSessionPayload(nextPayload);
    return sessionPayload;
  }

  function setSyncPayload(nextPayload) {
    syncPayload = normalizeSyncPayload(nextPayload, syncPayload);
    return syncPayload;
  }

  function closeWindow(name) {
    const targetWindow = name === 'auth' ? authWindow : workerWindow;
    if (targetWindow && !targetWindow.isDestroyed()) {
      targetWindow.close();
    }
    if (name === 'auth') {
      authWindow = null;
    } else {
      workerWindow = null;
    }
  }

  function ensureWindow(name, { show }) {
    let targetWindow = name === 'auth' ? authWindow : workerWindow;
    if (targetWindow && !targetWindow.isDestroyed()) {
      return targetWindow;
    }
    targetWindow = new BrowserWindow({
      width: 1180,
      height: 860,
      minWidth: 1024,
      minHeight: 700,
      title: name === 'auth' ? 'SplitShot PractiScore Sign In' : 'SplitShot PractiScore Worker',
      parent: typeof getParentWindow === 'function' ? getParentWindow() || undefined : undefined,
      autoHideMenuBar: true,
      show,
      webPreferences: {
        partition: PRACTISCORE_PARTITION,
        contextIsolation: true,
        nodeIntegration: false,
      },
    });
    targetWindow.on('closed', () => {
      if (name === 'auth') {
        authWindow = null;
      } else {
        workerWindow = null;
      }
    });
    if (name === 'auth') {
      authWindow = targetWindow;
    } else {
      workerWindow = targetWindow;
    }
    return targetWindow;
  }

  async function loadUrl(browserWindow, targetUrl) {
    if (!browserWindow || browserWindow.isDestroyed()) {
      throw new Error('PractiScore browser window is unavailable.');
    }
    const currentUrl = browserWindow.webContents.getURL();
    if (currentUrl === targetUrl) {
      return browserWindow;
    }
    await browserWindow.loadURL(targetUrl);
    return browserWindow;
  }

  async function executeScript(browserWindow, script) {
    if (!browserWindow || browserWindow.isDestroyed()) {
      throw new Error('PractiScore browser window is unavailable.');
    }
    return browserWindow.webContents.executeJavaScript(script, true);
  }

  async function detectPageState(browserWindow) {
    if (!browserWindow || browserWindow.isDestroyed()) {
      return null;
    }
    try {
      const currentUrl = browserWindow.webContents.getURL();
      if (!/^https?:/i.test(currentUrl || '')) {
        return null;
      }
      return await executeScript(browserWindow, AUTH_STATE_SCRIPT);
    } catch {
      return null;
    }
  }

  async function hasPractiScoreCookies() {
    try {
      const cookies = await hostSession.cookies.get({ url: PRACTISCORE_DASHBOARD_URL });
      return Array.isArray(cookies) && cookies.some((cookie) => String(cookie?.domain || '').includes('practiscore.com'));
    } catch {
      return false;
    }
  }

  async function currentStatus() {
    if (!enabled) {
      return setSessionPayload(defaultSessionPayload());
    }
    if (stubEnabled) {
      return sessionPayload;
    }
    const cookiesPresent = await hasPractiScoreCookies();
    const pageState = await detectPageState(authWindow) || await detectPageState(workerWindow);
    const currentUrl = String(pageState?.current_url || authWindow?.webContents.getURL() || workerWindow?.webContents.getURL() || '');
    const mode = pageLooksUnauthenticated(pageState, currentUrl);
    const details = {
      partition: PRACTISCORE_PARTITION,
      current_url: currentUrl,
    };
    if (mode === 'challenge_required') {
      return setSessionPayload({
        state: 'challenge_required',
        message: 'Finish the PractiScore security challenge in the desktop sign-in window.',
        details,
      });
    }
    if (cookiesPresent && mode !== 'authenticating') {
      return setSessionPayload({
        state: 'authenticated_ready',
        message: 'PractiScore session is authenticated and ready.',
        details,
      });
    }
    if ((authWindow && !authWindow.isDestroyed()) || mode === 'authenticating') {
      return setSessionPayload({
        state: 'authenticating',
        message: 'Continue the PractiScore sign-in flow in the desktop sign-in window.',
        details,
      });
    }
    return setSessionPayload(defaultSessionPayload());
  }

  async function startSession() {
    if (!enabled) {
      return setSessionPayload(defaultSessionPayload());
    }
    if (stubEnabled) {
      setSyncPayload(defaultSyncPayload());
      return setSessionPayload({
        state: 'authenticated_ready',
        message: 'PractiScore session is authenticated and ready.',
        details: { host: 'electron_practiscore_host_v1', mode: 'test_fixture' },
      });
    }
    const browserWindow = ensureWindow('auth', { show: true });
    await loadUrl(browserWindow, PRACTISCORE_DASHBOARD_URL);
    if (browserWindow.isMinimized()) {
      browserWindow.restore();
    }
    browserWindow.show();
    browserWindow.focus();
    setSyncPayload(defaultSyncPayload());
    return currentStatus();
  }

  async function clearSession() {
    if (!enabled) {
      return setSessionPayload(defaultSessionPayload());
    }
    closeWindow('auth');
    closeWindow('worker');
    lastMatches = [];
    setSyncPayload(defaultSyncPayload());
    if (!stubEnabled) {
      try {
        await hostSession.clearStorageData({ origins: ['https://practiscore.com'] });
        await hostSession.clearCache();
      } catch {}
    }
    return setSessionPayload(defaultSessionPayload());
  }

  async function listMatches() {
    if (!enabled) {
      return { sessionPayload: defaultSessionPayload(), matches: [] };
    }
    if (stubEnabled) {
      const nextSession = setSessionPayload({
        state: 'authenticated_ready',
        message: 'PractiScore session is authenticated and ready.',
        details: { host: 'electron_practiscore_host_v1', mode: 'test_fixture' },
      });
      lastMatches = [{ ...DEFAULT_STUB_MATCH }];
      return { sessionPayload: nextSession, matches: lastMatches };
    }
    const nextSession = await currentStatus();
    if (nextSession.state !== 'authenticated_ready') {
      return { sessionPayload: nextSession, matches: [] };
    }
    try {
      const browserWindow = ensureWindow('worker', { show: false });
      await loadUrl(browserWindow, PRACTISCORE_MATCHES_URL);
      lastMatches = normalizeMatches(await executeScript(browserWindow, DISCOVER_MATCHES_SCRIPT));
      return { sessionPayload: await currentStatus(), matches: lastMatches };
    } catch (error) {
      return {
        sessionPayload: await currentStatus(),
        matches: lastMatches,
        error: {
          message: error?.message || 'Unable to list remote PractiScore matches.',
          category: errorCategoryFromMessage(error?.message),
          details: { route: '/api/practiscore/matches' },
        },
      };
    }
  }

  async function downloadSelectedMatch(remoteId) {
    const resolvedRemoteId = String(remoteId || '').trim();
    if (!enabled) {
      return {
        sessionPayload: defaultSessionPayload(),
        error: {
          message: 'PractiScore Electron host is disabled.',
          category: MALFORMED_REMOTE_RESPONSE_ERROR,
          details: { remote_id: resolvedRemoteId },
        },
      };
    }
    if (!resolvedRemoteId) {
      return {
        sessionPayload: await currentStatus(),
        error: {
          message: 'A remote PractiScore match must be selected before import.',
          category: MALFORMED_REMOTE_RESPONSE_ERROR,
          details: { remote_id: resolvedRemoteId },
        },
      };
    }
    if (stubEnabled) {
      const artifactText = fs.readFileSync(stubFixturePath, 'utf8');
      const match = { ...DEFAULT_STUB_MATCH, remote_id: resolvedRemoteId };
      return {
        sessionPayload: setSessionPayload({
          state: 'authenticated_ready',
          message: 'PractiScore session is authenticated and ready.',
          details: { host: 'electron_practiscore_host_v1', mode: 'test_fixture' },
        }),
        download: {
          remote_id: resolvedRemoteId,
          source_name: path.basename(stubFixturePath),
          artifact_text: artifactText,
          html: '<html><body><h1>Electron IDPA Match</h1></body></html>',
          match,
          summary_snapshot: {
            remote_match: match,
          },
        },
      };
    }
    const nextSession = await currentStatus();
    if (nextSession.state !== 'authenticated_ready') {
      return {
        sessionPayload: nextSession,
        error: {
          message: nextSession.message || 'PractiScore session is not ready.',
          category: EXPIRED_AUTHENTICATION_ERROR,
          details: { remote_id: resolvedRemoteId },
        },
      };
    }
    try {
      if (!lastMatches.some((item) => item.remote_id === resolvedRemoteId)) {
        const discovery = await listMatches();
        if (discovery.error) {
          return discovery;
        }
        lastMatches = normalizeMatches(discovery.matches);
      }
      const match = lastMatches.find((item) => item.remote_id === resolvedRemoteId);
      if (!match || !match.details_url) {
        return {
          sessionPayload: await currentStatus(),
          error: {
            message: `Unable to resolve remote PractiScore match ${resolvedRemoteId}.`,
            category: MALFORMED_REMOTE_RESPONSE_ERROR,
            details: { remote_id: resolvedRemoteId },
          },
        };
      }
      const browserWindow = ensureWindow('worker', { show: false });
      await loadUrl(browserWindow, match.details_url);
      const snapshot = await executeScript(browserWindow, SELECTED_MATCH_SNAPSHOT_SCRIPT);
      const download = await executeScript(browserWindow, FETCH_ARTIFACT_SCRIPT);
      if (!download || download.error) {
        return {
          sessionPayload: await currentStatus(),
          error: {
            message: `PractiScore did not expose a CSV or TXT artifact for remote match ${resolvedRemoteId}.`,
            category: MISSING_REQUIRED_REMOTE_ARTIFACT_ERROR,
            details: { remote_id: resolvedRemoteId },
          },
        };
      }
      const artifactText = typeof download.artifact_text === 'string' ? download.artifact_text : '';
      const sourceName = String(download.source_name || `remote-${resolvedRemoteId}.csv`).trim();
      if (!artifactText || !/\.(csv|txt)$/i.test(sourceName)) {
        return {
          sessionPayload: await currentStatus(),
          error: {
            message: `PractiScore did not expose a CSV or TXT artifact for remote match ${resolvedRemoteId}.`,
            category: MISSING_REQUIRED_REMOTE_ARTIFACT_ERROR,
            details: { remote_id: resolvedRemoteId, source_name: sourceName },
          },
        };
      }
      const html = await browserWindow.webContents.executeJavaScript('document.documentElement.outerHTML', true)
        .catch(() => '');
      return {
        sessionPayload: await currentStatus(),
        download: {
          remote_id: resolvedRemoteId,
          source_name: path.basename(sourceName),
          artifact_text: artifactText,
          html,
          match,
          summary_snapshot: {
            remote_match: match,
            page_url: snapshot?.page_url || browserWindow.webContents.getURL(),
            page_title: snapshot?.page_title || '',
            page_heading: snapshot?.page_heading || '',
            artifact: {
              source_name: path.basename(sourceName),
              final_url: String(download.final_url || ''),
              content_type: String(download.content_type || ''),
            },
          },
        },
      };
    } catch (error) {
      return {
        sessionPayload: await currentStatus(),
        error: {
          message: error?.message || 'Unable to import the selected remote PractiScore match.',
          category: errorCategoryFromMessage(error?.message),
          details: { remote_id: resolvedRemoteId },
        },
      };
    }
  }

  async function updateOverlay(routePayload) {
    const source = routePayload && typeof routePayload === 'object' ? routePayload : {};
    if (source.practiscore_session && typeof source.practiscore_session === 'object') {
      setSessionPayload(source.practiscore_session);
    }
    if (source.practiscore_sync && typeof source.practiscore_sync === 'object') {
      setSyncPayload(source.practiscore_sync);
    }
    return {
      practiscore_session: sessionPayload,
      practiscore_sync: syncPayload,
    };
  }

  return {
    getFeatureState: () => featureState(),
    getStateOverlay: () => ({
      ...featureState(),
      practiscore_session: sessionPayload,
      practiscore_sync: syncPayload,
    }),
    startSession,
    currentStatus,
    clearSession,
    listMatches,
    downloadSelectedMatch,
    updateOverlay,
  };
}

module.exports = {
  createPractiScoreHost,
  PRACTISCORE_DASHBOARD_URL,
};
