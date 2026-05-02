# Cloudflare Pages Setup

Deploying SplitShot as a browser-only PWA on Cloudflare Pages.

## Overview

Cloudflare Pages serves static files from a Git repository. No server-side runtime needed — SplitShot would be a folder of `.html`, `.js`, `.css`, `.wasm`, and model files.

## Setup Steps

### 1. Create a Pages project

- Go to **Workers & Pages** in the Cloudflare dashboard.
- Click **Create application** > **Pages** > **Connect to Git**.
- Select the repo and set the build configuration:

| Setting | Value |
|---|---|
| **Build command** | `exit 0` (no build step needed if files are already static) |
| **Build output directory** | `./` or the folder containing `index.html` |
| **Root directory** | `--` (leave blank unless monorepo) |

If using a build step (e.g., bundling JS modules, optimizing WASM), set `npm run build` and point to `dist/`.

### 2. Custom domain (`splitshot.studio`)

- In the Pages project, go to **Custom domains** > **Set up a domain**.
- If using an apex domain, add the domain as a Cloudflare zone and configure nameservers.
- For a subdomain (e.g., `app.splitshot.studio`), add a CNAME record pointing to `<project>.pages.dev` from your DNS provider, then associate it in the dashboard.

### 3. Static assets (`_headers`)

Create a `_headers` file in the output directory:

```
# Serve WASM with correct MIME type
*.wasm
  Content-Type: application/wasm

# Cache fingerprinted assets aggressively
*.wasm
  Cache-Control: public, max-age=31536000, immutable
*.js
  Cache-Control: public, max-age=31536000, immutable
*.css
  Cache-Control: public, max-age=31536000, immutable

# Cross-origin for FFmpeg.wasm SharedArrayBuffer
/*
  Cross-Origin-Opener-Policy: same-origin
  Cross-Origin-Embedder-Policy: require-corp
```

### 4. Static redirects (`_redirects`)

Optional. Create `_redirects` to forward root to the app:

```
/  /index.html  200
```

### 5. Environment variables

Not needed — there is no backend. All state is local to the browser.

## Important Limits (Free Plan)

| Limit | Value | Concern for SplitShot |
|---|---|---|
| **File size** | 25 MiB per file | FFmpeg.wasm core (`ffmpeg.wasm` ~30MB) exceeds this. Must split into chunks or serve from R2. ONNX model (~20MB) fits. |
| **Files per site** | 20,000 | Fine — SplitShot is a handful of static files. |
| **Bandwidth** | unlimited (within reason) | Fine on free tier for a local-first app (load once, cache locally). |
| **Builds per month** | 500 | Fine. |
| **Custom domains** | 100 per project | Fine. |

## Working Around the 25 MiB File Limit

FFmpeg.wasm's core (~30MB) exceeds Cloudflare Pages' per-file cap. Options:

**Option A — Use R2 for large WASM binaries**
- Upload `ffmpeg.wasm` and the ONNX model to Cloudflare R2.
- Make the R2 bucket public and serve from a custom domain (e.g., `static.splitshot.studio`).
- Update your JS to load WASM from the R2 URL.

**Option B — Split FFmpeg.wasm into chunks**
- FFmpeg.wasm supports loading from separate `.wasm` + `.data` files.
- If the `.wasm` portion is under 25 MiB, it works directly.
- The `.data` file can be fetched as a blob via R2.

**Option C — Use Cloudflare Workers as a proxy**
- A Pages Function can serve the large WASM file from R2 with the correct headers.
- This avoids exposing R2 directly while staying on the Cloudflare ecosystem.

## COOP/COEP Headers

FFmpeg.wasm requires `SharedArrayBuffer`, which needs:

```
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

These are set via `_headers` (see above). All resources loaded by the page must either be same-origin or explicitly opted in with `crossorigin="anonymous"` and CORS headers. External CDN resources (fonts, analytics, etc.) will be blocked unless they send `Access-Control-Allow-Origin: *`.

## Deployment

- Push to the connected Git branch → auto-deploys.
- Or use Direct Upload via `npx wrangler pages deploy <output-dir>`.

## Cost

**$0** on the Free Plan. Only pay if you exceed bandwidth limits (unlikely for a local-first app), or need R2 for large WASM files (R2 free tier: 10GB storage, 10M reads/month).
