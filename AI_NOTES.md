# Content App — Architecture & Notes for AI Agents

## Overview
Single-page PWA for content creation. Records audio/video, edits into clips/shorts,
auto-detects silence, generates graphics via Venice AI, and exports social-media-ready
posts. Runs entirely in the browser (client-side). Local Python server for Tailscale access.

## Repository
- GitHub: `https://github.com/ollieadam/content-app`
- Local path: `/home/ollie/decentralized strength pod/`
- Desktop shortcut: `~/Desktop/Content App.desktop` → runs `launcher.py` → persistent launcher window → opens Chrome `--app`

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
`launcher.py` (via .desktop file) → starts `server.py` subprocess → waits for server ready → user clicks "Open Content App" → `google-chrome-stable --app=http://localhost:8080` (frameless window, no tabs/address bar)

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
- "🎬 Open Content App" button → `google-chrome-stable --app=http://localhost:8080`
- "⏹ Stop Server" button — POSTs /api/shutdown, terminates server process
- Close window = stop server + exit
- WM_CLASS = `"content-app-launcher", "Content-app-launcher"` for Cinnamon taskbar matching
- Centred on screen, not resizable
- Status indicator: ○ Starting server… → ● Running

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
- Firefox caused double-tab issues; replaced with Chrome `--app`

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
