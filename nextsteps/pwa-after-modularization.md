# PWA Setup After Modularization

Once `app.js` is split into clean JS modules, converting SplitShot into an installable PWA (still Python-free, all-in-browser) requires these additions.

## Required Files

### 1. Web App Manifest (`manifest.json`)

Placed in the static root. Tells the browser the app is installable.

```json
{
  "name": "SplitShot",
  "short_name": "SplitShot",
  "description": "Competition shooting video analysis, scoring, and export",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "display_override": ["window-controls-overlay", "standalone"],
  "background_color": "#1a1a2e",
  "theme_color": "#e94560",
  "orientation": "any",
  "categories": ["sports", "utilities"],
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/icons/icon-512-maskable.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ],
  "file_handlers": [
    {
      "action": "/",
      "accept": { "application/x-splitshot-project": [".ssproj"] }
    }
  ]
}
```

### 2. Service Worker (`sw.js`)

A service worker enables offline operation and caches the app shell + WASM/model binaries on first visit. It runs in its own thread and intercepts all fetch requests.

**Cache strategies:**

| Resource | Strategy | Rationale |
|---|---|---|
| `index.html`, `app.js`, `styles.css` | Cache-first (install-time) | App shell — needed offline |
| `*.wasm` (FFmpeg, ONNX runtime) | Cache-first (install-time) | Large binaries — download once |
| ONNX model file | Cache-first (install-time) | ~20MB — download once |
| `icons/*` | Cache-first (install-time) | Small, static |
| Video files (user-loaded) | Network-only (no cache) | User files, handled via File API / blob URLs |
| Audio clips | Network-only (no cache) | Same as video |

**Key `install` handler (pseudocode):**

```javascript
const CACHE_NAME = 'splitshot-v1';
const PRECACHE_URLS = [
  '/',
  '/index.html',
  '/app.js',
  '/styles.css',
  '/manifest.json',
  '/ffmpeg/ffmpeg-core.js',
  '/ffmpeg/ffmpeg-core.wasm',
  '/model/shotml.onnx',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();
});
```

**Key `fetch` handler:**

```javascript
self.addEventListener('fetch', (event) => {
  // Only cache same-origin GET requests
  if (event.request.method !== 'GET' || !event.request.url.startsWith(self.location.origin)) {
    return;
  }
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
```

**Key `activate` handler (cache cleanup):**

```javascript
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
});
```

### 3. Service Worker Registration

In `index.html` (or the JS module), register the service worker. This should happen after the app is functional (not on first paint) to avoid delaying the initial load.

```javascript
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js');
  });
}
```

### 4. App Icons

Required icon sizes: 192x192, 512x512. A maskable variant (with safe-zone padding) for Android. Generate these from the SplitShot logo using a tool like `pwa-asset-generator` or Figma.

### 5. Install Prompt

Optionally, trigger the browser's install prompt with custom UI:

```javascript
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (event) => {
  event.preventDefault();
  deferredPrompt = event;
  // Show an "Install App" button in the UI
});

// On button click:
async function installApp() {
  if (!deferredPrompt) return;
  deferredPrompt.prompt();
  const result = await deferredPrompt.userChoice;
  deferredPrompt = null;
}
```

## What Changes in the Modularized JS

After splitting `app.js` into modules, these PWA-specific additions are needed:

- **`modules/pwa.js`** — handles SW registration, install prompt, app update notification
- **`modules/storage.js`** — wraps IndexedDB for project persistence (replacing filesystem `.ssproj`)
- **`modules/file-loader.js`** — wraps File System Access API and drag-and-drop for video loading
- **`modules/export.js`** — wraps FFmpeg.wasm calls and triggers browser download via `URL.createObjectURL`

## Storage Architecture (IndexedDB)

The current Python backend reads/writes `.ssproj` folders on disk. In the browser, IndexedDB replaces this:

| Python filesystem | Browser equivalent |
|---|---|
| `project.json` | IndexedDB document store |
| Auto-save periodic write | `requestAnimationFrame` throttle + periodic IndexedDB writes |
| Recent projects list | IndexedDB or `localStorage` |
| Settings (`~/.splitshot/settings.json`) | `localStorage` or IndexedDB |
| Exported video files | Browser download (blob → `<a download>`) |

## Offline Behavior

On first visit, the service worker caches:
- App shell (HTML, JS, CSS, manifest)
- FFmpeg.wasm core (~30MB)
- ONNX model (~20MB)

After that, the app loads entirely from cache. Video files the user imports are held as in-memory blob URLs (from `<input type="file">` or drag-and-drop). Closing the tab loses them — the user re-imports next session (same as current behavior where videos aren't embedded in `.ssproj`).

## Testing PWA Readiness

Use Chrome DevTools > **Lighthouse** > **PWA** audit. Checks:
- Registers service worker
- Responds with 200 on offline
- Has `manifest.json` with required fields
- Icons of correct sizes
- Uses HTTPS (Cloudflare Pages provides this automatically)
- Redirects HTTP to HTTPS
- Proper `start_url`

## Deployment Checklist (after modularization)

- [ ] Split `app.js` into modules (`modules/` directory)
- [ ] Create `manifest.json`
- [ ] Create `sw.js` with precache + cache-first strategy
- [ ] Add SW registration to `index.html`
- [ ] Generate icon set (192, 512, maskable)
- [ ] Add `_headers` for COOP/COEP and WASM MIME types
- [ ] Test offline with DevTools > Network > Offline
- [ ] Run Lighthouse PWA audit
- [ ] Deploy to Cloudflare Pages
