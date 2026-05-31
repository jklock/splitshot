function installDesktopRouteBridgeInMainWorld(dashboardUrl) {
  if (globalThis.__splitshotDesktopRouteBridgeInstalled) {
    return true;
  }
  if (globalThis.__splitshotDesktopRouteBridgeInstalling) {
    return false;
  }
  globalThis.__splitshotDesktopRouteBridgeInstalling = true;

  const installBridge = () => {
    if (globalThis.__splitshotDesktopRouteBridgeInstalled) {
      globalThis.__splitshotDesktopRouteBridgeInstalling = false;
      return true;
    }
    if (
      !globalThis.splitshot
      || typeof globalThis.splitshot.openPathDialog !== 'function'
      || typeof globalThis.splitshot.openExternal !== 'function'
    ) {
      globalThis.setTimeout(installBridge, 50);
      return false;
    }

    const splitshot = globalThis.splitshot;
    const bridgeDashboardUrl = String(dashboardUrl || '');
    const currentLocation = () => String(globalThis.location?.href || 'http://127.0.0.1/');
    const originalFetch = globalThis.fetch.bind(globalThis);
    const jsonHeaders = { 'Content-Type': 'application/json' };
    const jsonResponse = (payload, status = 200) => new Response(JSON.stringify(payload), {
      status,
      headers: jsonHeaders,
    });
    const requestPath = (input) => {
      try {
        if (typeof input === 'string') return new URL(input, currentLocation()).pathname;
        if (input && typeof input.url === 'string') return new URL(input.url, currentLocation()).pathname;
      } catch {}
      return '';
    };
    const requestMethod = (input, init) => String((init && init.method) || (input && input.method) || 'GET').toUpperCase();
    const requestHeaders = (input, init) => new Headers((init && init.headers) || (input && input.headers) || {});
    const requestBody = async (input, init) => {
      if (init && typeof init.body === 'string') {
        try { return JSON.parse(init.body); } catch { return {}; }
      }
      if (input && typeof input.clone === 'function') {
        try {
          const text = await input.clone().text();
          return text ? JSON.parse(text) : {};
        } catch {}
      }
      return {};
    };
    const encodeJsonHeader = (payload) => {
      try {
        const bytes = new TextEncoder().encode(JSON.stringify(payload ?? {}));
        let binary = '';
        for (const byte of bytes) {
          binary += String.fromCharCode(byte);
        }
        return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
      } catch {
        return '';
      }
    };
    const currentState = () => (globalThis.state && typeof globalThis.state === 'object' ? globalThis.state : {});
    const currentPractiScoreOptions = () => {
      const options = currentState().practiscore_options;
      if (options && typeof options === 'object') {
        return { ...options };
      }
      return {
        has_source: false,
        source_name: '',
        detected_match_type: '',
        stage_numbers: [],
        competitors: [],
        comparison_competitors: [],
      };
    };
    const defaultSessionPayload = () => ({
      state: 'not_authenticated',
      message: 'Connect PractiScore to use your browser session for background sync.',
      details: {},
    });
    const defaultSyncPayload = () => ({
      state: 'idle',
      message: 'No remote PractiScore sync activity yet.',
      matches: [],
      selected_remote_id: null,
      error_category: '',
      details: {},
    });
    const responseJson = async (response) => {
      try {
        return await response.clone().json();
      } catch {
        return null;
      }
    };
    const hostFeature = async () => {
      if (typeof splitshot.getPractiScoreHostFeature !== 'function') {
        return { enabled: false };
      }
      try {
        return await splitshot.getPractiScoreHostFeature();
      } catch {
        return { enabled: false };
      }
    };
    const hostOverlay = async () => {
      if (typeof splitshot.getPractiScoreStateOverlay !== 'function') {
        return null;
      }
      try {
        return await splitshot.getPractiScoreStateOverlay();
      } catch {
        return null;
      }
    };
    const updateHostOverlay = async (payload) => {
      if (typeof splitshot.updatePractiScoreHostOverlay !== 'function') {
        return null;
      }
      try {
        return await splitshot.updatePractiScoreHostOverlay(payload || {});
      } catch {
        return null;
      }
    };
    const synthesizePractiScoreErrorPayload = async ({ sessionPayload, matches, remoteId, message, category, details }) => {
      const routePayload = {
        practiscore_session: sessionPayload && typeof sessionPayload === 'object' ? sessionPayload : defaultSessionPayload(),
        practiscore_sync: {
          state: 'error',
          message: String(message || 'PractiScore request failed.'),
          matches: Array.isArray(matches) ? matches : [],
          selected_remote_id: remoteId == null || remoteId === '' ? null : String(remoteId),
          error_category: String(category || ''),
          details: details && typeof details === 'object' ? details : {},
        },
        practiscore_options: currentPractiScoreOptions(),
        matches: Array.isArray(matches) ? matches : [],
      };
      await updateHostOverlay(routePayload);
      return routePayload;
    };

    globalThis.fetch = async (input, init) => {
      const method = requestMethod(input, init);
      const path = requestPath(input);
      if (method === 'POST' && path === '/api/dialog/path') {
        try {
          const payload = await requestBody(input, init);
          const selectedPath = await splitshot.openPathDialog(payload || {});
          return jsonResponse({ path: typeof selectedPath === 'string' ? selectedPath : '' });
        } catch (error) {
          return jsonResponse({ error: error?.message || 'Unable to open the native path chooser.' }, 400);
        }
      }
      if (method === 'POST' && path === '/api/practiscore/dashboard/open') {
        try {
          const opened = await splitshot.openExternal(bridgeDashboardUrl);
          if (!opened) {
            return jsonResponse({ error: 'Unable to open the PractiScore dashboard in your browser.' }, 500);
          }
          return jsonResponse({
            status: 'Opened PractiScore dashboard in your browser.',
            url: bridgeDashboardUrl,
          });
        } catch (error) {
          return jsonResponse({ error: error?.message || 'Unable to open the PractiScore dashboard in your browser.' }, 500);
        }
      }
      const feature = await hostFeature();
      if (method === 'GET' && path === '/api/state' && feature && feature.enabled) {
        const response = await originalFetch(input, init);
        const result = await responseJson(response);
        if (!result) {
          return response;
        }
        const overlay = await hostOverlay();
        if (overlay && overlay.enabled) {
          result.practiscore_session = overlay.practiscore_session || result.practiscore_session;
          result.practiscore_sync = overlay.practiscore_sync || result.practiscore_sync;
        }
        return jsonResponse(result, response.status);
      }
      if (feature && feature.enabled && method === 'POST' && path === '/api/practiscore/session/start') {
        try {
          const result = await splitshot.startPractiScoreSessionHost();
          await updateHostOverlay({ practiscore_session: result, practiscore_sync: defaultSyncPayload() });
          return jsonResponse(result);
        } catch (error) {
          const result = {
            state: 'error',
            message: error?.message || 'Unable to start PractiScore in the desktop host.',
            details: { route: '/api/practiscore/session/start' },
          };
          await updateHostOverlay({ practiscore_session: result, practiscore_sync: defaultSyncPayload() });
          return jsonResponse(result);
        }
      }
      if (feature && feature.enabled && method === 'GET' && path === '/api/practiscore/session/status') {
        try {
          const result = await splitshot.getPractiScoreSessionStatusHost();
          await updateHostOverlay({ practiscore_session: result });
          return jsonResponse(result);
        } catch (error) {
          const result = {
            state: 'error',
            message: error?.message || 'Unable to read PractiScore desktop host status.',
            details: { route: '/api/practiscore/session/status' },
          };
          await updateHostOverlay({ practiscore_session: result });
          return jsonResponse(result);
        }
      }
      if (feature && feature.enabled && method === 'POST' && path === '/api/practiscore/session/clear') {
        try {
          const result = await splitshot.clearPractiScoreSessionHost();
          await updateHostOverlay({ practiscore_session: result, practiscore_sync: defaultSyncPayload() });
          return jsonResponse(result);
        } catch {
          const result = defaultSessionPayload();
          await updateHostOverlay({ practiscore_session: result, practiscore_sync: defaultSyncPayload() });
          return jsonResponse(result);
        }
      }
      if (feature && feature.enabled && method === 'GET' && path === '/api/practiscore/matches') {
        const hostResult = await splitshot.listPractiScoreMatchesHost();
        if (hostResult && hostResult.error) {
          return jsonResponse(await synthesizePractiScoreErrorPayload({
            sessionPayload: hostResult.sessionPayload,
            matches: hostResult.matches,
            remoteId: null,
            message: hostResult.error.message,
            category: hostResult.error.category,
            details: hostResult.error.details,
          }));
        }
        const headers = requestHeaders(input, init);
        headers.set('X-SplitShot-PractiScore-Electron-Host', '1');
        headers.set('X-SplitShot-PractiScore-Session-Payload', encodeJsonHeader(hostResult?.sessionPayload || defaultSessionPayload()));
        headers.set('X-SplitShot-PractiScore-Matches', encodeJsonHeader(hostResult?.matches || []));
        const response = await originalFetch(input, {
          ...(init || {}),
          method: 'GET',
          headers,
        });
        const result = await responseJson(response);
        if (!result) {
          return response;
        }
        await updateHostOverlay(result);
        return jsonResponse(result, response.status);
      }
      if (feature && feature.enabled && method === 'POST' && path === '/api/practiscore/sync/start') {
        const payload = await requestBody(input, init);
        const hostResult = await splitshot.downloadPractiScoreSelectedMatchHost(payload?.remote_id || '');
        if (hostResult && hostResult.error) {
          return jsonResponse(await synthesizePractiScoreErrorPayload({
            sessionPayload: hostResult.sessionPayload,
            matches: currentState().practiscore_sync?.matches,
            remoteId: payload?.remote_id || null,
            message: hostResult.error.message,
            category: hostResult.error.category,
            details: hostResult.error.details,
          }));
        }
        const headers = requestHeaders(input, init);
        if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
        headers.set('X-SplitShot-PractiScore-Electron-Host', '1');
        headers.set('X-SplitShot-PractiScore-Session-Payload', encodeJsonHeader(hostResult?.sessionPayload || defaultSessionPayload()));
        const response = await originalFetch(input, {
          ...(init || {}),
          method: 'POST',
          headers,
          body: JSON.stringify({
            ...(payload || {}),
            __electron_host_download: hostResult?.download || null,
          }),
        });
        const result = await responseJson(response);
        if (!result) {
          return response;
        }
        await updateHostOverlay(result);
        return jsonResponse(result, response.status);
      }
      if (method === 'POST' && path === '/api/practiscore/session/start') {
        const payload = await requestBody(input, init);
        const headers = requestHeaders(input, init);
        if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
        const response = await originalFetch(input, {
          ...(init || {}),
          method: 'POST',
          headers,
          body: JSON.stringify({ ...(payload || {}), defer_external_open: true }),
        });
        let result = null;
        try {
          result = await response.clone().json();
        } catch {
          return response;
        }
        if (!response.ok || (result && result.error)) {
          return response;
        }
        const sessionState = String(result?.state || '');
        if (sessionState === 'authenticating' || sessionState === 'challenge_required') {
          const opened = await splitshot.openExternal(bridgeDashboardUrl);
          if (!opened) {
            return jsonResponse({
              state: 'error',
              message: 'Unable to open PractiScore in your browser.',
              details: {
                ...(result?.details || {}),
                open_url: bridgeDashboardUrl,
              },
            });
          }
        }
        return jsonResponse(result, response.status);
      }
      return originalFetch(input, init);
    };

    globalThis.__splitshotDesktopRouteBridgeInstalled = true;
    globalThis.__splitshotDesktopRouteBridgeInstalling = false;
    return true;
  };

  return installBridge();
}

function createDesktopRouteBridgeSource({ dashboardUrl }) {
  return `(${installDesktopRouteBridgeInMainWorld.toString()})(${JSON.stringify(String(dashboardUrl || ''))});`;
}

module.exports = {
  createDesktopRouteBridgeSource,
  installDesktopRouteBridgeInMainWorld,
};
