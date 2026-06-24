# Content App — Architecture & Notes for AI Agents

## Overview
Single-page PWA for content creation. Records audio/video, edits into clips/shorts,
auto-detects silence, generates graphics via Venice AI, and exports social-media-ready
posts. Runs entirely in the browser (client-side). Local Python server for Tailscale access.

## Repository
- GitHub: `https://github.com/ollieadam/content-app`
- Local path: `/home/ollie/content app/`
- Desktop shortcut: `~/Desktop/Content App.desktop` → runs `launcher.py` → persistent launcher window → opens Firefox `--new-window`

## Files

### Core App
| File | Purpose |
|------|---------|
| `index.html` | Main SPA — CSS, HTML, and JS in one file (~1780 lines) |
| `manifest.json` | PWA manifest for "Add to Home Screen" |
| `sw.js` | Service worker for offline caching |
| `icon.svg` | App icon |

### Server
| File | Purpose |
|------|---------|
| `server.py` | Python HTTP server on 0.0.0.0:8080. Has /api/shutdown + /api/status endpoints |
| `launcher.py` | Python tkinter launcher window — persistent taskbar icon. Starts server, opens Chrome `--app` on click |

### Launch Flow
`launcher.py` (via .desktop file) → starts `server.py` subprocess → waits for server ready → user clicks "Open Content App" → Firefox `--new-window` at Tailscale IP (or localhost fallback)

### Originals (kept, not part of new app)
| File | Purpose |
|------|---------|
| `decentralized-strength-teleprompter.html` | Original standalone teleprompter |
| `video editor/clipper.html` | Original standalone clip editor |
| `video editor/to Edit/` | Raw video files (gitignored) |

### Other
| File | Purpose |
|------|---------|
| `AI_NOTES.md` | This file — architecture notes for AI agents |
| `content-app-launcher.sh` | Thin shell wrapper (exec `launcher.py`), kept for backwards compat |
| `.gitignore` | Ignores video files, Python cache, OS junk |
| `originals.md` | List of original standalone HTML files |

## Brands & Platforms

4 brands managed in-app via IndexedDB settings:

| Brand | Emoji | Platforms |
|-------|-------|-----------|
| Personal | 👤 | (none yet) |
| ChasStrengthClub | 🏋️ | YouTube, Instagram, Facebook |
| Decentralized Strength | 🎙️ | Facebook, Buzzsprout |
| Barbie the Pug | 🐾 | Instagram, Facebook |

Brand toggles in Settings modal. Active brand shown as chips on Home tab.

## 5-Tab Layout

### 🏠 Home (tabPanel 0)
- Big Record button → switches to Record tab
- Brand selector chips
- Platform stats cards (YouTube, Buzzsprout, local count)
- Recent recordings list from IndexedDB
- ON/OFF server status bar (green dot = server running, shows Tailscale IP)
- API key status cards (configured/not configured)
- "Stop Server" button (POSTs to /api/shutdown)

### 📝 Scripts (tabPanel 1)
Teleprompter ported from the original HTML:
- Multiple script tabs (+ add/delete)
- Scrolling text with play/pause
- Speed slider (1-10)
- Mirror mode (for teleprompter glass)
- Fullscreen mode
- Font size controls
- Word count + read time estimate
- AI Script Generator button → calls Venice chat API
- Text editor linked to stage

### 🎙️ Record (tabPanel 2)
Three recording modes via tabs: Audio / Video / Screen
- Audio: Webcam off, records mic only
- Video: Webcam on + mic
- Screen: getDisplayMedia for screen share
- Mic selector with refresh + test button
- Level meter (AnalyserNode via Web Audio API)
- Title input + Brand selector + Script selector (for teleprompter sync)
- Record/Stop button with timer
- Save to IndexedDB or Discard

### ✂️ Edit (tabPanel 3)
Manual + auto clipping:
- File drop/browse zone
- Timeline with progress, selection range, playhead
- In/Out buttons + Preview
- Clip queue with export (captureStream + MediaRecorder)
- Auto silence detection: configurable threshold + min gap
  - Analyzes PCM data via AudioContext.decodeAudioData
  - Finds non-silent segments
  - Batch exports all segments as individual .webm files
- Load saved recordings from IndexedDB

### 📱 Post (tabPanel 4)
Social post composer:
- Aspect ratio presets: 9:16 (Reels/Story), 1:1 (Feed), 4:5 (Portrait), 16:9 (YouTube/FB)
- Canvas compositor with text overlay
  - Font size slider + position (top/bottom/center)
  - Video frame capture from source file
  - Cover/fill mode for aspect ratio fitting
- Export: captureStream video (.webm) or frame (.png)
- Venice AI image generation:
  - Prompt input + style selector (fetched from Venice API)
  - Aspect ratio selector for generation
  - 2 variants per generation
  - Grid display of results
  - Click to use in post

## APIs

### Venice AI (image + text)
- **Base URL:** `https://api.venice.ai/api/v1`
- **Auth:** Bearer token stored in IndexedDB settings
- **Endpoints used:**
  - `POST /image/generate` — image gen (model: qwen-image-2)
  - `POST /chat/completions` — script gen (model: qwen3-4b)
  - `GET /image/styles` — list style presets
- **Config fields:** API Key

### YouTube Stats (read-only)
- **API:** Google YouTube Data API v3
- **Endpoint:** `GET /youtube/v3/channels?part=statistics`
- **Config fields:** Channel ID, API Key
- **Displays:** Video count from channel stats

### Buzzsprout Stats (read-only)
- **API:** Buzzsprout API
- **Endpoint:** `GET /api/{podcast_id}/episodes.json`
- **Auth:** Token in Authorization header
- **Config fields:** API Key, Podcast ID
- **Displays:** Episode count

## Data Storage (IndexedDB)

### Database: ContentApp

#### Store: settings
- Key: 'config'
- Value: { veniceKey, ytChannel, ytKey, bsKey, bsPodcast, brands[], activeBrand, _ytStats, _bsEpisodes }

#### Store: recordings
- Key: auto-generated 'rec_'+timestamp
- Value: { id, title, brand, type ('audio'|'video'|'screen'), date, dur, blob (Blob) }

#### Store: scripts
- Key: script id
- Value: { id, name, text }

#### Store: clips
- (reserved for future clip-specific storage)

## PWA
- `manifest.json` sets display: standalone, black/red theme
- `sw.js` caches app files, bypasses API calls (Venice/Google/Buzzsprout)
- Service worker registered in init(), works on localhost (not file://)

## Desktop Launch

### server.py features
- Python 3 http.server
- Binds to 0.0.0.0:8080 (accessible via Tailscale IP on 100.x.x.x)
- GET /api/status → JSON with server state + detected IPs
- POST /api/shutdown → graceful shutdown
- No browser auto-open (launcher.py handles that)
- Quiet logging (log_message override)
- CORS headers for local development
- Runs as subprocess of launcher.py

### launcher.py features
- Python tkinter window (~340x220px, black #0a0a0a / red #dc2626 theme)
- Starts server.py as subprocess on launch; waits up to 15s for server ready
- Resolves Tailscale IP from `/api/status` and opens the app at `http://{tailscale_ip}:8080`
- "🎬 Open Content App" button → Firefox `--new-window` at the resolved URL
- "⏹ Stop Server" button — POSTs /api/shutdown, terminates server process
- Close window = stop server + exit
- WM_CLASS = `"content-app-launcher", "Content-app-launcher"` for Cinnamon taskbar matching
- Centred on screen, not resizable
- Status indicator: ○ Starting server… → ● Running
- Polls `/api/badge` every 5s to show project-saved notifications from phone

### .desktop file (two copies)
- `~/Desktop/Content App.desktop` — desktop shortcut
- `~/.local/share/applications/Content App.desktop` — start menu entry
- `Exec=python3 "/home/ollie/decentralized strength pod/launcher.py"`
- `StartupWMClass=content-app-launcher` (matches launcher window's WM_CLASS)
- `Icon=/home/ollie/decentralized strength pod/icon.svg`
- `Terminal=false`, `Categories=AudioVideo;`

### Workflow
1. User clicks pinned taskbar icon (or desktop shortcut)
2. `launcher.py` opens (small dark window with "Content App" header)
3. Server starts in background (status: "Starting server…" → "● Running")
4. User clicks "🎬 Open Content App"
5. Chrome launches in `--app` mode (no tabs/address bar, looks like native app)
6. User closes Chrome window; launcher stays open
7. User clicks "Open Content App" again to reopen Chrome
8. User clicks "Stop Server" or closes launcher → everything shuts down

### History
- Previously used `content-app-launcher.sh` + Firefox `--new-window`
- Briefly switched to Chrome `--app` mode to fix Firefox double-tab issue
- Switched back to Firefox (user preference) — works fine now

## Key Technical Details

### Media Recording
- getUserMedia for audio/video, getDisplayMedia for screen
- MediaRecorder for capture (prefers vp9/webm)
- Blob stored directly in IndexedDB

### Audio Analysis (Silence Detection)
- FileReader → ArrayBuffer → AudioContext.decodeAudioData
- Get channel data, analyze 50ms frames for RMS amplitude
- Configurable silence threshold (0.02/0.05/0.10)
- Configurable min gap length (0.3s/0.5s/1.0s)
- Merges non-silent regions into exportable segments

### Video Export
- captureStream() from a scratch video element
- MediaRecorder with preferred codec
- Downloads as .webm

### Post Composition
- Canvas sized to aspect ratio (e.g., 360x640 for 9:16)
- Video frame drawn as cover/fill
- Text overlay with shadow for readability
- exportVideo: captureStream + MediaRecorder
- exportFrame: canvas.toBlob → PNG

## Key JavaScript Variables
- _settings — loaded from IndexedDB on init
- _scripts — array of {id, name, text}
- _currentScript — index into _scripts
- _recMode — 'audio' | 'video' | 'screen'
- _editClips — array of {id, name, start, end}
- _editSegments — array of {start, end} from silence detection
- _postAspect — {w, h} from selected aspect ratio

## Common Patterns
- Toast messages for user feedback (2-4 second auto-dismiss)
- IndexedDB methods: dbGet, dbPut, dbGetAll, dbDel
- Time formatting: fmtTime(seconds) → "M:SS"
- All DOM references via getElementById

## UI Theme
- Black background (#0a0a0a), red accent (#dc2626)
- Dark surfaces (#151515, #1a1a1a), subtle borders (#282828)
- Mobile-first, max-width 480px container
- Bottom nav bar, 60px height + safe area padding

## Responsive Layout
- 700px breakpoint: home-grid 2-col, 4-col stat/post/gen grids, settings modal centered
- 1024px breakpoint: larger padding, bigger buttons, taller teleprompter (500px)
- `.app` is `width: 100%` (no max-width constraint)
- Bottom nav unchanged on desktop (no sidebar)
- Optimised for 1920×1200 screen (ASUS Zenbook)
- `'use strict'` is active in the script block — all variables must be declared

---

## Session Update (2026-06-20)

### Architecture Changes

#### Settings — now server-side
- Settings stored in `settings.json` in the app directory (NOT IndexedDB)
- `GET /api/settings` → returns parsed JSON (empty object if file missing)
- `POST /api/settings` → writes JSON body to settings.json
- `loadSettings()` and `saveSettings()` in index.html fetch from `/api/settings`
- Shared across all devices on Tailscale automatically
- `dbPut(store, val, key)` now accepts optional 3rd key arg for out-of-line key stores

#### Server — new endpoints (server.py)
- `GET /api/settings` — load settings from settings.json
- `POST /api/settings` — save settings to settings.json
- `POST /api/proxy` — proxy external API calls (FB, IG, GitHub) to avoid browser CORS
  - Supports `json_body` (JSON POST) and `multipart` (form-data with `_image_b64` for image uploads)
  - `SETTINGS_FILE = os.path.join(DIR, 'settings.json')`
- `do_OPTIONS` handler added for CORS preflight
- Shutdown fix: `self.server.shutdown()` called in daemon thread to avoid deadlock

#### Launcher (launcher.py) — opens Tailscale URL
- On startup reads `/api/status`, extracts `100.x.x.x` Tailscale IP
- Opens Firefox at `http://{tailscale_ip}:8080` (falls back to localhost)
- `self.app_url` stores the resolved URL

### New Features (index.html)

#### Settings modal — tabbed
- Tabs: Creative (Venice AI), Social (YouTube x2, Meta/FB/IG), Publish (Buzzsprout, GitHub/Blog), Brands
- CSS: `.stab-bar` / `.stab` / `.stab-panel`
- `showSettingsTab(btn, tab)` switches panels by matching `id="sp-{tab}"`

#### Brands system
- `BRANDS` constant: personal (no platforms), chs (yt/ig/fb), dsp (fb/buzzsprout), barbie (ig/fb)
- `setupBrandSettings()` renders checkboxes in `#brandsSettings`
- `loadBrandSettings()` populates `#brandBar`, `#recBrand`, `#postBrand`
- `toggleBrandSetting(el)` / `setActiveBrand(id)` update `_settings.brands` / `_settings.activeBrand`

#### Social Publishing (Post tab)
- Live posting toggle: `_livePosting` flag, `toggleLivePosting()`, `#liveBar` / `#liveToggle`
- `updatePublishTargets()` — shows ALL configured accounts regardless of brand (FB x3, IG x3, Blog)
- `publishToAll()` — iterates checked targets, calls per-platform function, shows toast results
- `postToFBPage(pageId, caption, imageBlob)` — text via `/feed`, image via `/photos` multipart
- `postToIG(igId, caption, imageUrl)` — creates media container then publishes
- `uploadImageToGitHub(blob)` — uploads PNG to `assets/posts/{timestamp}.png`, returns public URL for IG
- `postToGitHubBlog(content)` — creates HTML post in `blog/` directory of GitHub repo
- `buildBlogPostHTML(title, body)` — full HTML page (NOTE: `<\/script>` escaped inside template literal)
- All external calls via `_proxy(payload)` → `POST /api/proxy`

#### Settings fields added
- YouTube: `yt1Label`, `ytChannel`, `yt2Label`, `yt2Channel`
- Meta: `metaToken`, `fbPage1Label/Id`, `fbPage2Label/Id`, `fbPage3Label/Id`
- Instagram: `igAcct1Label/Id`, `igAcct2Label/Id`, `igAcct3Label/Id`
- GitHub/Blog: `githubToken`, `githubRepo` (format: `owner/reponame`), `blogUrl`
- Brands: `brands` (array of active brand IDs), `activeBrand`

### Key Proxy Patterns
- JSON call: `_proxy({url, method, json_body: {...}})`
- Image upload: `_proxy({url, method, multipart: {caption, access_token, _image_b64: base64string}})`
- Settings debounce 300ms → `updateApiStatus()` + `loadBrandSettings()` + `updatePublishTargets()`

### Meta/Facebook API Status (as of 2026-06-20)
- Business account verified ✅
- App ID: 4493585697545534, Business ID: 1521837516113590
- Need: Page Access Token from Graph API Explorer → paste into Settings → Meta User Token
- To get IG Account ID: `GET /v21.0/PAGE_ID?fields=instagram_business_account&access_token=TOKEN`
- IG posting requires public image URL — app uploads to GitHub first, passes URL to IG API
- Long-lived Page Access Token = permanent; user token = 60 days

### Desktop Files Fixed
- `~/Desktop/Content App.desktop` and `~/.local/share/applications/Content App.desktop`
- Corrected path from `/home/ollie/decentralized strength pod/` → `/home/ollie/content app/`

### Key Variables Updated
- `_settings` — loaded from server (`/api/settings`), not IndexedDB
- `_livePosting` — bool controlling Publish Now button
- `app_url` (launcher.py) — Tailscale URL resolved at startup

---

## Session Update (2026-06-20 — Content Library)

### Feature: 📚 Library Tab (tab index 6)

New 7th tab added to the nav. Stores all content types in IndexedDB `library` store.

#### Library Item Schema
```js
{
  id:      'lib_' + Date.now(),
  title:   string,
  type:    'audio'|'video'|'image'|'doc'|'link',
  subtype: 'recording'|'upload'|'youtube'|'facebook'|'website',
  date:    number (ms),
  size:    number (bytes, 0 for links),
  url:     string|null,
  blob:    Blob|null,
  notes:   string,
}
```

#### IndexedDB
- DB version bumped `1` → `2` in `dbOpen()` to add `library` store with `{ keyPath: 'id' }`

#### Key JS Functions
- `libraryRender()` — fetches all from `library` store, applies `_libFilter` + `_libSort`, renders rows
- `libraryAdd(file)` — file upload → dbPut → render
- `libraryAddLink(url)` — URL paste, auto-detects youtube/facebook/website → dbPut → render
- `libraryDelete(id)` — dbDel → render
- `librarySuggestModel(item)` → `{provider, model, label, reason}` — maps content type to best AI model
- `librarySendToChat(id)` — shows inline confirmation banner at top of Library tab
- `libraryChatConfirm(item)` — switches to Chat tab, pre-selects model, injects content

#### AI Model Routing
| type | model | reason |
|------|-------|--------|
| image | OpenRouter · Gemini 2.0 Flash | vision |
| youtube link | OpenRouter · Gemini 2.0 Flash | YouTube URL analysis |
| audio/video file | Venice · Llama 3.3 70B | long transcript analysis |
| doc/text | OpenRouter · Qwen3 235B | long-document analysis |
| facebook/website | OpenRouter · Qwen3 235B | web content analysis |

#### Send to Chat Flow
1. User clicks 💬 on library item
2. Inline banner shows suggested model + reason + [Confirm] [Change ▾] [Cancel]
3. On confirm: `switchTab(5)`, pre-select provider/model, inject content as first user message
   - Image → base64 data URL embedded in message bubble + sent as vision content
   - URL → "Analyse this: {url}" as user message
   - Text/doc → file text content as user message
   - Audio/video file → note "No direct audio — paste transcript"

#### Home Tab
- Each recording row in `refreshHome()` gets a "📚" button → `libraryAddFromRecording(id)`

#### sw.js
- Cache version bumped `v3` → `v4`

#### CSS classes added
- `.lib-filters`, `.lib-chip`, `.lib-chip.active`
- `.lib-toolbar`, `.lib-list`, `.lib-row`
- `.lib-row-main`, `.lib-row-meta`, `.lib-row-actions`
- `.lib-type-badge`, `.lib-ai-chip`
- `.lib-add-overlay`, `.lib-add-box`
- `.lib-confirm-bar`

---

## Session Update (2026-06-20 — Security Audit & Next Session Plan)

### Full Codebase Review — Issues Found

#### 🔴 Critical (blocking "record from phone")

**1. No HTTPS → `getUserMedia` blocked on phone**
- Server serves plain HTTP on `0.0.0.0:8080`
- `navigator.mediaDevices.getUserMedia()` requires a secure context (HTTPS or localhost)
- From phone via Tailscale (`http://100.x.x.x:8080`), mic/camera silently denied
- **Fix:** Use Tailscale Serve for auto TLS cert:
  ```
  tailscale serve --bg --https=443 8080
  ```
  Then access at `https://<machine>.<tailnet>.ts.net` from phone.

**2. API keys exposed to every device on the Tailnet**
- `GET /api/settings` returns all secrets (Venice, YouTube, Meta, GitHub, etc.) with no auth
- Anyone on the same network can curl them
- `settings.json` not in `.gitignore` — risk of accidental commit
- **Fix:** Add app password protection + add to `.gitignore`

#### 🟡 Medium

**3. `content-app-launcher.sh` has stale path**
- Points to `/home/ollie/decentralized strength pod/launcher.py`
- Should be `/home/ollie/content app/launcher.py`

**4. Old path references in `.desktop` files still point to old location**

**5. No QR code for phone access**
- Server shows IP but user must type it manually on phone
- QR code on Home tab would let user scan and open instantly

**6. Canvas video export is hardcoded 2-second placeholder**
- `postExportVideo()` line ~2304: `setTimeout(() => rec.stop(), 2000)`
- Always exports only 2 seconds
- Should export proper duration or let user set it

**7. Post overlay text doesn't wrap**
- `postRender()` uses single `ctx.fillText` calls — long text overflows
- Need word-wrap using `ctx.measureText()`

**8. No CSP headers**
- Server sends no Content-Security-Policy
- Should add basic CSP for defense-in-depth

**9. Service worker caches API `GET` responses**
- `sw.js:26` caches all successful GET requests
- Could serve stale `/api/status` or other dynamic data

**10. Settings modal doesn't close on overlay backdrop click**
- Library add overlay does, but settings requires clicking "Done" button
- Inconsistent UX

### Planned Changes for Next Session

#### 1. 🔐 App Password Authentication
**Files:** `server.py` + `index.html`
- Add `appPassword` field to `settings.json`
- Store SHA-256 hash of password
- On page load, if password is set, show login overlay blocking app
- Verify client-side against stored hash
- Store auth state in `sessionStorage` (lasts per browser tab)
- Server-side: protect `GET /api/settings` by checking `X-App-Key` header against stored hash
- Password field in Settings modal (new "Security" tab or under Creative)

**Implementation details:**
- `server.py`: Add `_check_auth()` method that compares `X-App-Key` header value (SHA-256 of password) against stored hash
- Protected endpoints: `GET /api/settings`, `POST /api/settings`, `POST /api/proxy`
- `index.html`: Add login modal overlay (similar to settings modal but simpler)
- CSS: `.login-overlay`, `.login-modal` classes
- JS: `_authenticated` flag, `checkAuth()` on init, `showLogin()`, `loginSubmit()`
- Use `crypto.subtle.digest('SHA-256', ...)` for hashing

#### 2. 🔒 HTTPS via Tailscale Serve
**One-time setup (not code):**
- Run: `tailscale serve --bg --https=443 8080`
- Add to `launcher.py` to auto-run this command on startup
- Detect MagicDNS hostname and show as primary URL on Home tab + QR code

**launcher.py changes:**
- On startup, run `tailscale serve --bg --https=443 8080` (or check if already active)
- Extract `machine.tailnet.ts.net` from `tailscale status --json`
- Set `self.app_url` to `https://{magicdns}:443` (or just `https://{magicdns}`)
- Show the HTTPS URL in launcher status bar

#### 3. 📋 `.gitignore` update
Add lines:
```
settings.json
projects.json
*.pem
*.cert
```

#### 4. 🩹 Fix `content-app-launcher.sh`
Change line 1 from:
```bash
exec python3 "/home/ollie/decentralized strength pod/launcher.py"
```
to:
```bash
exec python3 "/home/ollie/content app/launcher.py"
```

#### 5. 📱 QR Code on Home Tab
**File:** `index.html`
- Add inline QR code generator (small ~50 line JS function using canvas)
- Show QR code below server status bar on Home tab
- Encode the current Tailscale/HTTPS URL
- Regenerate when URL changes

**QR generation approach:**
- Use a minimal inline QR code generator (not a library)
- ~40 lines of JS using `canvas` to render QR matrix
- Or embed a small base64-encoded QR lib in the HTML

#### 6. 🐛 Fix Post Canvas — Text Wrapping
**File:** `index.html` — `postRender()` function
- Replace simple `ctx.fillText()` with word-wrap logic:
  ```js
  function wrapText(ctx, text, maxWidth) {
    const words = text.split(' ');
    const lines = [];
    let line = '';
    for (const word of words) {
      const test = line ? line + ' ' + word : word;
      if (ctx.measureText(test).width > maxWidth && line) {
        lines.push(line);
        line = word;
      } else {
        line = test;
      }
    }
    if (line) lines.push(line);
    return lines;
  }
  ```

#### 7. 🐛 Fix 2-Second Video Export Placeholder
**File:** `index.html` — `postExportVideo()`
- Replace `setTimeout(() => rec.stop(), 2000)` with:
  - User-selectable duration (input field)
  - Or set to 5 seconds default
  - Show countdown/progress during render

#### 8. 🛡️ Add CSP Headers
**File:** `server.py` — in `_send_raw()` and `do_GET()`
```python
self.send_header('Content-Security-Policy',
    "default-src 'self'; "
    "media-src 'self' blob:; "
    "img-src 'self' data: blob: https:; "
    "connect-src 'self' https://api.venice.ai https://www.googleapis.com https://api.buzzsprout.com https://graph.facebook.com https://api.github.com; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline';"
)
```

#### 9. Fix Launcher — Use Firefox (confirmed: user prefers Firefox over Chrome)
- Launcher already uses Firefox — no change needed
- Update AI_NOTES to reflect Firefox is the intended browser

---

## Session Update (2026-06-21)

### Changes Implemented

#### 🔒 App Password Authentication
- **server.py**: Added `_load_settings()`, `_check_auth()` methods
  - `GET /api/status` returns `passwordSet` + `passwordHash` for client-side verification
  - `GET /api/settings`, `POST /api/settings`, `POST /api/proxy` protected by `X-App-Key` header
  - `do_OPTIONS` allows `X-App-Key` header via CORS
- **index.html**: Added login overlay (`#loginOverlay`)
  - `checkAuth()` on init: checks `/api/status` for `passwordSet`, shows login if needed
  - `loginSubmit()`: SHA-256 hashes password, compares to stored hash from server
  - Auth state in `sessionStorage('contentAppAuth')` — persists per browser tab
  - Password field in Settings → Creative tab (`#settingAppPassword`)
  - SHA-256 hashed via `crypto.subtle.digest` before saving to `settings.json`
  - `loadSettings()`/`saveSettings()`/`_proxy()` all include `X-App-Key` header when set

#### 🔒 HTTPS via Tailscale Serve
- **launcher.py**: `_ensure_tailscale_serve()` runs `tailscale serve --bg --https=443 8080`
- **launcher.py**: `_resolve_magicdns()` extracts `machine.tailnet.ts.net` from `tailscale status --json`
- App URL defaults to `https://{magicdns}` if available
- **server.py**: `get_magicdns_url()` added, returns HTTPS URL in `/api/status` as `httpsUrl`
- **index.html**: `checkServerStatus()` prefers `d.httpsUrl` for display + QR code
- Launcher status shows `🔒 https://...` when HTTPS is active

#### 📱 QR Code on Home Tab
- **index.html**: Inline `generateQR(text, canvas)` — ~90 lines, no dependencies
  - Version 1 (21×21), byte mode, L-level error correction (7 EC codewords)
  - Full Reed-Solomon encoding with pre-computed Galois field tables
  - Renders to canvas below server status bar
  - Regenerates on each `checkServerStatus()` tick with current URL

#### 🐛 Post Canvas — Text Wrapping
- **index.html** `postRender()`: Replaced simple `ctx.fillText()` with word-wrap logic
  - Uses `ctx.measureText()` to break lines at `maxWidth = c.width * 0.9`
  - Multi-word text now wraps instead of overflowing

#### 🐛 Fix 2-Second Video Export
- **index.html** `postExportVideo()`: Replaced `setTimeout(() => rec.stop(), 2000)` with:
  - User-selectable duration input (`#postExportDur`, default 5s, range 1-60)
  - Real-time countdown during render (`#postExportStatus`)
  - `requestAnimationFrame`-based timing for accurate duration

#### 🛡️ CSP Headers
- **server.py**: Added `_add_csp()` method called from `_send_raw()` and `_do_static()`
  - `default-src 'self'`, `media-src 'self' blob:`, `img-src 'self' data: blob: https:`
  - `connect-src 'self'` + Venice/Google/Buzzsprout/Facebook/GitHub APIs
  - `script-src 'self' 'unsafe-inline'`, `style-src 'self' 'unsafe-inline'`

### Testing Checklist
- [ ] Run `tailscale serve --bg --https=443 8080`
- [ ] Access app from phone via `https://<machine>.<tailnet>.ts.net`
- [ ] Test mic + camera recording from phone (Record tab)
- [ ] Test screen recording from phone
- [ ] Set app password, verify login overlay appears
- [ ] Verify password persists across page reload (sessionStorage)
- [ ] Test settings API returns 401 without correct `X-App-Key` header
- [ ] Scan QR code from phone, verify it opens the correct URL
- [ ] Test post text overlay wrapping with long captions
- [ ] Test post video export (should not be 2 seconds anymore)
- [ ] Verify settings.json is in .gitignore (not tracked)
- [ ] Check CSP headers in browser dev tools
- [ ] After init reorder fix: verify login shows when password is set, settings persist after login

---
## Session Update (2026-06-21 — Fix Init Order + Handoff)

### Bug Found: Init Order Causes Settings Wipe

**Root cause:** In `init()`, `initSettings()` ran BEFORE `checkAuth()`. When a password was set:

1. `initSettings()` → `loadSettings()` hit `GET /api/settings` without `X-App-Key` header → server returned 401
2. `loadSettings()` returned `{}` → `_settings` was set to empty object
3. `checkAuth()` then showed login overlay (but `_settings` was already `{}`)
4. After login, nothing called `initSettings()` again — `_settings` stayed `{}`
5. If the user typed anything in Settings, `saveSettingsDebounced()` wrote `{}` to server → **permanently wiped `settings.json`**
6. On next page load: no password hash found → no login prompt → app loads with empty settings → self-perpetuating

**Fix applied** (`index.html:2716-2772`):
- `checkAuth()` now runs BEFORE `initSettings()` in `init()`
- Extracted post-auth init logic into `bootstrapApp()` (lines 2716-2765)
- `loginSubmit()` calls `await bootstrapApp()` after successful auth (line 1383)
- Login now shows before settings are loaded; settings load correctly after auth

### Current State

| Aspect | Status |
|--------|--------|
| `settings.json` | **`{}`** — already wiped by old bug |
| Init ordering | Fixed — `checkAuth()` before `initSettings()` |
| Post-login bootstrap | Fixed — `loginSubmit()` calls `bootstrapApp()` |
| App Password Auth | Implemented (SHA-256, `X-App-Key`, login overlay) |
| HTTPS/Tailscale | Implemented (`launcher.py` auto-serve, MagicDNS) |
| QR Code | Implemented (inline, no deps) |
| Text wrapping | Fixed (`ctx.measureText()`) |
| Video export duration | Fixed (user-selectable 1-60s, countdown) |
| CSP headers | Implemented (`server.py` `_add_csp()`) |
| `.gitignore` | Still needs `settings.json` and `projects.json` added |

### What User Needs to Do
Since `settings.json` is `{}`, the server has no password hash. The app loads without a login prompt but with no API keys. **They need to:**
1. Open Settings (gear icon) — should be immediately accessible since no password
2. Re-enter all API keys (Venice, YouTube, Meta, Buzzsprout, GitHub)
3. Optionally set a new password in the Creative tab
4. Hard refresh the browser (Ctrl+Shift+R) first to ensure they have the new code

### Fixes Applied (2026-06-21 — Second Session)
- **Syntax error in `saveSettingsDebounced()`** — lone `}` prematurely closed `setTimeout` callback, leaving three function calls orphaned + dangling `}, 300)` broke entire script parse. All functions were undefined → "nothing clicks". Fixed by removing orphaned lines (called inside `doSave()` anyhow) and closing callback properly.
- **Viewport** — removed `user-scalable=no` to allow pinch-zoom on phones
- **Nav touch targets** — increased `.nav-btn` padding from 4px to 8px for larger tap area

### TTS & STT Added
- **🔊 Teleprompter Speak** — `teleSpeak()` button in `.tele-controls` using `window.speechSynthesis`. Rate matches current speed slider. Click again to stop.
- **🎤 Script Dictation** — `scriptMicToggle()` button in script editor `.btn-group`. Uses `SpeechRecognition` (continuous + interim results). Inline transcription into `#scriptEditor`. Red glow when active.
- **🎤 Chat Voice Input** — `chatMicToggle()` button in `.chat-input-area`. Single-utterance `SpeechRecognition`, auto-sends after 300ms. Red glow when active.

### Phone Readiness Audit
| Issue | Severity | Status |
|---|---|---|
| `getUserMedia` blocked on HTTP from phone | 🔴 Critical | Fix: launch via `launcher.py` which runs `tailscale serve --bg --https=443 8080` then open `https://{magicdns}` on phone |
| `user-scalable=no` prevents zoom | 🟡 Medium | Fixed |
| Buttons below 44px tap target | 🟡 Medium | `.nav-btn` padding increased. `.btn-sm`/`.btn-xs`/`.header-btn` still small — future work |
| Teleprompter stage 340px fixed height | 🟡 Medium | Still pending — needs 375px breakpoint |
| CSP allows `media-src 'self' blob:` | ✅ Good | Web Speech API is browser-native, not affected by CSP |

---
## Session Update (2026-06-21 — Phone Auto-fill, Load Speed, Mobile Adaptation)

### Changes to `index.html`

#### 1. 🔑 Password Auto-fill (login overlay)
- **Login form** (`#loginForm`): Wrapped input + button in `<form onsubmit="event.preventDefault();loginSubmit()">`
- Added `name="password"` and `autocomplete="current-password"` to password input for iOS/Android password managers
- Changed Unlock button to `type="submit"` — browser auto-associates the form as a login form
- Removed manual `onkeydown` handler (form handles Enter natively)
- Added `autocomplete="off"` to all **settings** password fields (Venice, OpenRouter, YouTube, Meta, Buzzsprout, GitHub, App Password) to suppress "Password on HTTP" browser warnings — these are API keys, not user credentials

#### 2. ⚡ Loading Performance
- **Loading overlay** (`#loadingOverlay`): Added centered spinner with "Loading Content App…" text, shown immediately on `init()` before any async work
- **Critical path split**: `bootstrapApp()` now:
  1. Loads settings + scripts (`await initSettings()`, `await initScripts()`) — essential for UI
  2. Renders UI (`loadBrandSettings()`, `refreshHome()`) and hides loading overlay
  3. Defers all non-critical work via `defer()` — mic listing, SW registration, Venice styles, post render, server polling, chat init
- **`defer(fn)` helper**: Uses `requestIdleCallback(fn, {timeout:2000})` if available, falls back to `setTimeout(fn, 1)` — avoids blocking the paint
- Changed `init()` from `async` IIFE to plain IIFE with promise chaining so the loading overlay appears synchronously
- `loginSubmit()` calls `bootstrapApp()` after successful auth — loads settings correctly post-login

#### 3. 📱 Mobile Adaptation (CSS)
- **Scrollable nav**: `.nav` now has `overflow-x: auto; -webkit-overflow-scrolling: touch` with hidden scrollbar; `.nav-btn` changed from `flex:1` to `flex:1 0 auto; min-width:48px` so 7 tabs scroll on small screens instead of cramming
- **New `@media (max-width: 480px)` breakpoint**:
  - Smaller header (13px title, 30px buttons)
  - Tighter padding (8px content/tabs)
  - Teleprompter height 260px (was 340px) with smaller text
  - Post canvas max-height 260px
  - Stats grid 2 columns (was 3), smaller stat cards
  - Settings pairs collapse to single column
  - Smaller hero section, big record button 64px
  - Nav icons 18px, labels 9px
  - Smaller buttons, timers, form groups
  - Touch targets at minimum 44×44px height
  - Rec preview max-height 200px
  - Library add options single column
  - Chat bubbles wider (92%) with 14px text
- **New `@media (max-width: 360px)` breakpoint**:
  - Even smaller: teleprompter 200px, post canvas 200px, hero button 56px
  - Minimal padding (4px), smaller everything

#### 4. 🐛 Bug Fix: `requestIdleCallback` crash
- `defer(fn)` was passing `1` (number) as second arg to `requestIdleCallback`, which expects `Options` dictionary → `TypeError: Argument 2 can't be converted to a dictionary`
- Fixed with: `requestIdleCallback(fn, { timeout: 2000 })` when available, `setTimeout(fn, 1)` fallback otherwise

### Key Files Modified
| File | Lines | Changes |
|------|-------|---------|
| `index.html` | 52-54, 402-455, 1018-1040, 2833-2910 | CSS responsive, loading overlay, login form, init/bootstrap restructure |
| `AI_NOTES.md` | This section | Session documentation |

### Current Known Warnings (expected)
- **"Password fields on insecure HTTP"** — appears when accessing via `http://` (Tailscale IP). Goes away when using HTTPS (`https://<machine>.<tailnet>.ts.net`). Settings API key fields have `autocomplete="off"` to minimize warnings.

## Session Update (2026-06-21 — Crypto API Fix + Server Merge)

### Changes Made

#### 1. 🐛 Crypto API `hashPw()` crash on HTTP
- **File:** `index.html:1086-1093`
- **Bug:** `crypto.subtle.digest()` throws a DOMException on insecure HTTP contexts, but the code only checked `if(window.crypto&&crypto.subtle)` which is truthy even on HTTP. The pure-JS SHA-256 fallback was never reached.
- **Fix:** Wrapped `crypto.subtle.digest()` in try/catch — on error, falls through to the `sha256hex()` pure-JS implementation.

#### 2. 🐛 Server full-replace wipes settings on partial save
- **File:** `server.py:67-80`
- **Bug:** `POST /api/settings` did `json.dump(data, f)` replacing the entire file. If the client sent incomplete data (e.g., browser autofill triggers `saveSettingsDebounced()` before `initSettings()` finished), all unmapped fields were silently deleted.
- **Fix:** Server now merges incoming data into existing settings:
  ```python
  existing = self._load_settings()
  existing.update(data)
  existing = {k: v for k, v in existing.items() if v != ''}
  ```
  Empty-string values are stripped to handle deletions (e.g., `clearAppPassword()`).

#### 3. 🐛 `clearAppPassword()` used `delete` — incompatible with merge
- **File:** `index.html:1290-1296`
- **Bug:** `delete _settings.appPassword` removed the key, so the merge wouldn't clear it.
- **Fix:** Changed to `_settings.appPassword = ''` — server interprets empty string as deletion.

#### 4. 🛡️ Guard: skip `saveSettingsDebounced()` if settings not loaded
- **File:** `index.html:1206,1247`
- **Added:** `_settingsLoaded` flag, set by `initSettings()`. `saveSettingsDebounced()` returns early if `!_settingsLoaded`, preventing autofill-triggered saves from wiping data during page load.

### Current State
- ✅ Content app general settings save/load working
- ❌ "Crypto app" (password auth / Venice AI) — still not persisting after refresh
  - User reports settings for crypto-related features still don't survive page refresh
  - Likely needs server restart (Stop/Start in launcher) + hard browser refresh (Ctrl+Shift+R) to pick up new code
  - If still broken after restart, investigate: saved `settings.json` content, browser console errors, and `POST /api/settings` response

### Required Actions
1. Restart server (Stop → Start in launcher) for `server.py` changes
2. Hard refresh browser (Ctrl+Shift+R) for `index.html` changes

### Unfinished Items from Plan
- [ ] `.gitignore` — add `settings.json`, `projects.json`, `*.pem`, `*.cert`
- [ ] Fix `content-app-launcher.sh` stale path (still points to old directory)
- [ ] Verify `getUserMedia` works from phone via Tailscale HTTPS
- [ ] Increase `.btn-sm`/`.btn-xs`/`.header-btn` tap targets to 44px
- [ ] Add 375px breakpoint for teleprompter stage height
- [ ] Testing checklist above
