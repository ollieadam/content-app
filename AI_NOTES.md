# Content App — Architecture & Notes for AI Agents

## Overview
Single-page PWA for content creation. Records audio/video, edits into clips/shorts,
auto-detects silence, generates graphics via Venice AI, and exports social-media-ready
posts. Runs entirely in the browser (client-side). Local Python server for Tailscale access.

## Repository
- GitHub: `https://github.com/ollieadam/content-app`
- Local path: `/home/ollie/decentralized strength pod/`
- Desktop shortcut: `~/Desktop/Content App.desktop` → runs `server.py` → opens Firefox

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

### Originals (kept, not part of new app)
| File | Purpose |
|------|---------|
| `decentralized-strength-teleprompter.html` | Original standalone teleprompter |
| `video editor/clipper.html` | Original standalone clip editor |
| `video editor/to Edit/` | Raw video files (gitignored) |

### Documentation
| File | Purpose |
|------|---------|
| `AI_NOTES.md` | This file — architecture notes for AI agents |

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

## Desktop Launch (server.py)

### server.py features
- Python 3 http.server
- Binds to 0.0.0.0:8080 (accessible via Tailscale IP)
- GET /api/status → JSON with server state + detected IPs
- POST /api/shutdown → graceful shutdown via /api/shutdown endpoint
- Prints QR-code-friendly URL on startup
- CORS headers for local development

### Desktop .desktop file
- `~/Desktop/Content App.desktop`
- Exec: `python3 /path/to/server.py` in terminal
- Opens Firefox to http://localhost:8080

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
