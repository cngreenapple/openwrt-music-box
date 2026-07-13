# 🎵 OpenWrt-Music-Box: Audiophile-Grade Music Server for OpenWrt

Turn your idle OpenWrt Router or Set-Top Box (STB) into a High-End, Bit-Perfect Music Streamer.

OpenWrt-Music-Box is a lightweight, Dockerized music player tailored specifically for OpenWrt environments. It bypasses the standard Linux audio resampling, delivering pure, untouched audio data directly to your USB DAC. Combined with seamless Bluetooth A2DP support and a smart local library manager, it's the ultimate audio engine for your homelab.

---

## 📋 Table of Contents

- [✨ Key Features](#-key-features)
- [🚀 One-Command Installation](#-one-command-installation)
- [🏗️ Architecture](#️-architecture)
- [📚 Full API Reference](#-full-api-reference)
- [🖥️ Frontend Code Map](#️-frontend-code-map)
- [🗃️ Database Schema](#️-database-schema)
- [🎛️ EQ Preset Reference](#️-eq-preset-reference)
- [🛠️ Configuration](#️-configuration)
- [🖥️ OpenWrt LuCI Integration](#️-openwrt-luci-integration)
- [📖 Usage](#-usage)
- [⚙️ Tech Stack](#️-tech-stack)
- [📁 Project Structure](#-project-structure)
- [🧹 Logging](#-logging)
- [🐛 Troubleshooting](#-troubleshooting)
- [🔄 Changelog](#-changelog)
- [📝 License](#-license)

---

## ✨ Key Features

* 🎧 **Bit-Perfect Audio Output:** Delivers pure, untouched digital audio (e.g., 24-bit/96kHz) directly to your USB DAC without system resampling.
* 📡 **Bluetooth A2DP Support:** Custom integrated `bluealsa` allows seamless pairing and streaming to your TWS or Bluetooth Speakers right from the Web UI.
* 🗂️ **Smart Background Scanner:** Asynchronous deep-scanning of your internal/external HDDs (`/mnt`). Automatically extracts ID3 tags using `mutagen` and stores them in a lightning-fast SQLite WAL-mode database.
* 🌐 **Responsive Web UI:** Control playback, manage queues, browse folders, and pair Bluetooth devices from any browser.
* ☁️ **YouTube Music & Lyrics API:** Integrated with `ytmusicapi` for cloud streaming and `LRCLIB` for real-time synced lyrics.
* 🐳 **Fully Dockerized:** Runs in an isolated, lightweight Debian container, keeping your OpenWrt host perfectly clean.
* 🎚️ **10-Band Equalizer + Crossfeed:** Built-in parametric EQ with 16 presets and binaural crossfeed for headphones.
* 🌐 **Browser Play Mode:** Stream audio directly in your browser without server-side playback. Supports YouTube, local files, radio streams, and uploaded audio.
* 📁 **File Upload:** Upload audio files via the Web UI for instant playback.
* 📱 **PWA Ready:** Install as a Progressive Web App on your phone for a native-like experience.

---

## 🚀 One-Command Installation

**Satu perintah untuk SEMUA platform — install, start, & LuCI setup otomatis:**

```bash
git clone https://github.com/cngreenapple/openwrt-music-box.git && cd openwrt-music-box && chmod +x install.sh && ./install.sh
```

Script akan **otomatis**:
| Step | Aksi |
|------|------|
| 1-6 | Install semua dependencies & Python packages |
| 7 | **Auto-start service** — Docker (OpenWrt) atau background (Debian/Alpine) |
| 8 | **Auto-setup LuCI** — jika terdeteksi OpenWrt, langsung pasang tab di panel admin |
| ✓ | **Verifikasi** — cek apakah service sudah running di port **2030** |

Akses di: **http://localhost:2030** atau **http://<ip-router>:2030**

---

## 🏗️ Architecture

### Audio Pipeline

The audio pipeline differs based on the selected **Play Mode**:

```
┌──────────────────────────────────────────────────────────────────────┐
│                        SERVER MODE                                   │
│                                                                      │
│  Browser ──GET /play──▶ Flask ──play.sh──▶ mpv ──ALSA──▶ USB DAC    │
│                    │                    │         │                  │
│                    │                    │    ┌────┴─────┐           │
│                    │                    │    │ bluealsa  │           │
│                    │                    │    │ (BT A2DP) │           │
│                    │                    │    └────┬─────┘           │
│                    │                    │         │                  │
│                    │         metadata_worker()    └──▶ BT Speaker   │
│                    │           (every 1s)                          │
│                    └──▶ /status ◀──── mpv_socket                   │
│                              (pollStatus)                          │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                       BROWSER MODE                                   │
│                                                                      │
│  Browser ──GET /play──▶ Flask ──(no mpv)──▶ /play/current           │
│                    │                              │                  │
│                    │                              ▼                  │
│                    │                     /stream or /youtube_proxy   │
│                    │                              │                  │
│                    │                              ▼                  │
│                    │              ┌──────────────────────────┐       │
│                    │              │ HTML5 <audio> element     │       │
│                    │              │  ├── GainNode (Volume)   │       │
│                    │              │  ├── BiquadFilter x10    │       │
│                    │              │  │   (10-band EQ)        │       │
│                    │              │  ├── StereoPanner(Balance)│       │
│                    │              │  └── AudioDestination     │       │
│                    │              └──────────────────────────┘       │
│                    │                                               │
│                    └──▶ /status ◀──(defaults, no mpv)              │
│                              (pollStatus)                          │
└──────────────────────────────────────────────────────────────────────┘
```

### WebAudio Graph (Browser Mode)

```
<audio> element
    │
    ▼
createMediaElementSource()  ←── dipanggil SEKALI saja!
    │
    ▼
  GainNode  ←── Volume (0-100%)
    │
    ▼
BiquadFilter[0]  ←── 32Hz (Sub)
BiquadFilter[1]  ←── 64Hz (Low)
BiquadFilter[2]  ←── 125Hz (Kick)
BiquadFilter[3]  ←── 250Hz (Mid)
BiquadFilter[4]  ←── 500Hz (Body)
BiquadFilter[5]  ←── 1kHz (Vox)
BiquadFilter[6]  ←── 2kHz (Detl)
BiquadFilter[7]  ←── 4kHz (Pres)
BiquadFilter[8]  ←── 8kHz (Treb)
BiquadFilter[9]  ←── 16kHz (Air)
    │
    ▼
StereoPannerNode  ←── Balance (L/R)
    │
    ▼
AudioContext.destination
```

---

## 📚 Full API Reference

### 🔄 Playback

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| `GET/POST` | `/play?url=&mode=&title=` | Add song to queue and start playing | `{"status":"ok","mode":"play_now","queue_len":5}` |
| `GET` | `/play/mode?mode=` | Set play mode (`server` or `browser`) | `{"status":"ok","mode":"server"}` |
| `GET` | `/play/current` | Get current playing item info | `{"index":0,"title":"Song","link":"/path","thumb":"..."}` |
| `GET` | `/play/next_browser` | Advance queue for browser mode (no mpv) | `{"index":1,"title":"Next","link":"...","thumb":"..."}` |

**Parameters for `/play`:**
| Param | Required | Default | Description |
|-------|----------|---------|-------------|
| `url` | ✅ | — | File path, YouTube URL, or stream URL |
| `mode` | ❌ | `play_now` | `play_now` to play immediately, `enqueue` to add to queue |
| `title` | ❌ | `Unknown Title` | Display title for the queue |

**Behavior by mode:**
- **`play_now`**: Clears queue, sets current song, starts playback
- **`enqueue`**: Appends to queue, auto-starts if stopped and queue was empty

**Note:** For local files with `play_now`, the server scans the directory and adds all audio files to the queue.

---

### 🎮 Control

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/control/pause` | Toggle play/pause (mpv cycle pause) |
| `GET` | `/control/stop` | Stop playback, clear queue |
| `GET` | `/control/next` | Advance to next track in queue |
| `GET` | `/control/prev` | Go to previous track (or restart current if < 3s) |
| `GET` | `/control/shuffle` | Shuffle remaining queue (current track stays) |
| `GET` | `/control/volume?val=` | Set volume (0-100) via mpv |
| `GET` | `/control/seek?val=` | Seek to percentage (0-100) via mpv |
| `GET` | `/control/jump?index=` | Jump to specific index in queue |
| `GET` | `/control/output?mode=` | Switch audio output (jack/hdmi/bluetooth) |

**Server mode flow for `/control/next`:**
```
control("next") → play_next_in_queue()
                 → update current_index + 1
                 → trigger_play(next_song.link)
                 → play.sh kills old mpv, starts new mpv
                 → metadata_worker detects new path → updates /status
```

**Browser mode flow for `ctl('next')`:**
```
ctl("next") → nextBrowserTrack()
            → fetch('/play/next_browser') → returns {index, link, title}
            → playBrowserAudio(link, title) → sets browserAudio.src
            → browserAudio.play() → WebAudio processes audio
```

---

### ⚖️ Equalizer & Balance

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/control/eq?f1=..f10=` | Set 10-band EQ gains (-12 to +12) |
| `GET` | `/control/preset?name=` | Apply EQ preset by name |
| `GET` | `/control/balance?l=&r=` | Set left/right channel volume (0.0-1.0) |
| `GET` | `/control/crossfeed?state=` | Toggle binaural crossfeed (on/off) |
| `GET` | `/get_crossfeed` | Get crossfeed state |
| `GET` | `/control/bitperfect` | Toggle bit-perfect mode |
| `GET` | `/get_bitperfect` | Get bit-perfect state |

**EQ frequency mapping:**
| Key | Frequency | Label |
|-----|-----------|-------|
| `f1` | 32 Hz | Sub |
| `f2` | 64 Hz | Low |
| `f3` | 125 Hz | Kick |
| `f4` | 250 Hz | Mid |
| `f5` | 500 Hz | Body |
| `f6` | 1 kHz | Vox |
| `f7` | 2 kHz | Detl |
| `f8` | 4 kHz | Pres |
| `f9` | 8 kHz | Treb |
| `f10` | 16 kHz | Air |

---

### 📋 Queue

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/queue/list` | Get full queue with current index |
| `GET` | `/queue/clear` | Clear the entire queue |

**Response for `/queue/list`:**
```json
{
  "queue": [
    {"link": "/path/to/song.mp3", "title": "Artist - Song Title"},
    {"link": "...", "title": "..."}
  ],
  "current_index": 0
}
```

---

### 📡 Status & Metadata

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/status` | Get full player state (title, artist, time, queue, etc.) |
| `GET` | `/get_lyrics` | Fetch synced/plain lyrics from LRCLIB |

**`/status` response fields:**
| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Current track title |
| `artist` | string | Artist name |
| `album` | string | Album name |
| `genre` | string | Genre |
| `year` | string | Release year |
| `tech_info` | string | Audio codec info (e.g. "FLAC • 1411kbps • 44.1kHz • 16bit • Lossless") |
| `current_time` | float | Current playback position in seconds |
| `total_time` | float | Total track duration in seconds |
| `status` | string | `"playing"`, `"paused"`, `"stopped"`, `"loading"` |
| `volume` | int | Current volume (0-100) |
| `status_output` | string | `"jack"`, `"hdmi"`, `"bluetooth"` |
| `active_preset` | string | Current EQ preset name |
| `thumb` | string | Album art URL |
| `queue` | array | Current playlist queue |
| `current_index` | int | Current queue index |
| `play_mode` | string | `"server"` or `"browser"` |
| `timer_display` | string | Sleep timer display (e.g. "15m") |
| `timer_active` | bool | Whether sleep timer is active |

---

### 📂 File Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/get_files?path=` | Browse filesystem (returns dirs + audio files) |
| `POST` | `/upload` | Upload audio file (multipart/form-data) |
| `GET` | `/uploads` | List uploaded files |
| `GET` | `/stream?path=` | Stream local file with HTTP Range support |
| `GET` | `/youtube_proxy?url=` | Proxy YouTube audio stream (via yt-dlp) |
| `GET` | `/radio_proxy?url=` | Proxy radio stream (via requests) |

**`/get_files` response by path:**
```
GET /get_files?path=/
→ Internal Storage (/root), External HDD/USB (/mnt), Uploads, Music Library

GET /get_files?path=/root/music
→ [..] parent dir, sorted list of directories + audio files
```

**Note:** Files starting with `.` are hidden. Only files matching `AUDIO_EXTS` are shown.

---

### 🎵 Library Database

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/library/scan` | Start async scan of music directory |
| `GET` | `/library/status` | Get scan progress |
| `GET` | `/library/tracks?sort=` | Get all tracks (sort: title/artist/album/newest) |
| `GET` | `/library/search_db?q=` | Search tracks by title, artist, or album |
| `GET/POST` | `/system/default_path` | Get or set default music scan path |

---

### 🎵 Saved Playlists

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/get_playlist` | Load saved playlist (JSON from file) |
| `POST` | `/save_playlist` | Save playlist (send JSON body) |
| `GET` | `/playlist/export_m3u` | Export queue as M3U file download |
| `POST` | `/playlist/import_m3u` | Import M3U/M3U8/PLS playlist (raw text body) |

---

### 🔵 Bluetooth

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/bt/scan` | Scan for Bluetooth devices (10s timeout) |
| `GET` | `/bt/connect?mac=` | Pair and connect to device |
| `GET` | `/bt/disconnect?mac=` | Disconnect device |

**Bluetooth connection flow:**
```
1. bluetoothctl scan off
2. bluetoothctl power on
3. timeout 10s bluetoothctl scan on
4. bluetoothctl devices → JSON list
5. (on connect) bluetoothctl pair, trust, connect
6. Verify "Connected: yes" in bluetoothctl info
7. Set mpv audio-device to bluealsa
8. Save to /root/output_mode
```

---

### ⏱️ System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/system/timer?min=` | Set sleep timer (0 to disable) |
| `GET` | `/` | Serve web UI (`templates/index.html`) |

---

## 🖥️ Frontend Code Map

### Main Variables & State

| Variable | Type | Description |
|----------|------|-------------|
| `browserAudio` | HTMLAudioElement | The `<audio id="browser-audio">` element |
| `audioCtx` | AudioContext | WebAudio context (initialized ONCE) |
| `sourceNode` | MediaElementSource | WebAudio source from browserAudio |
| `gainNode` | GainNode | Volume control (0.0-1.0) |
| `pannerNode` | StereoPannerNode | Balance control (-1 to 1) |
| `eqFilters[]` | BiquadFilter[10] | 10-band peaking EQ filters |
| `audioInitialized` | bool | Prevents double init of WebAudio |
| `settings` | object | EQ gains (`f1`-`f10`), volume, preset |
| `systemState` | object | `playMode` (server/browser), `powerMode` |
| `isPlaying` | bool | Local play state |
| `globalTime` | float | Smoothed playback position |
| `totalDuration` | float | Track duration |
| `pendingPlay` | bool | Guard against double-play (COREv8) |

### Key Functions

#### 🎧 `playBrowserAudio(src, title)` — Main Playback Engine
```
Purpose: Play audio in browser mode
Flow:
  1. Set browserAudio.src = src (file stream or proxy URL)
  2. Parse title "Artist - Song" format → set #tit, #art, #tech-specs
  3. browserAudio.play() → catch autoplay errors
  4. WebAudio graph automatically processes audio
Note: createMediaElementSource() called ONLY ONCE at init
```

#### 🔄 `nextBrowserTrack()` — Next Track
```
Purpose: Advance to next track in browser mode
Flow:
  1. fetch('/play/next_browser') → backend advances current_index
  2. Build stream URL (local: /stream, YouTube: /youtube_proxy)
  3. Call playBrowserAudio(src, d.title)
```

#### ▶️ `togglePlay()` — Play/Pause
```
Server mode:
  fetch('/control/pause') → mpv cycle pause
Browser mode:
  If playing: browserAudio.pause()
  If paused + has src: browserAudio.play() (resume, no reload)
  If paused + no src: fetch('/play/current') → playBrowserAudio()
```

#### 🎛️ `ctl(action)` — Control Actions
```
Actions: pause, prev, next, shuffle, stop
Browser mode flow:
  prev: globalTime > 3? seek to 0. Else fetch previous track from queue.
  next: nextBrowserTrack()
  shuffle: fetch('/control/shuffle')
  stop: browserAudio.pause() + clear src
```

#### 🔊 `sendEq()` — EQ Update
```
Debounced (100ms). Sends f1-f10 to:
  - WebAudio BiquadFilter nodes (browser mode)
  - Flask /control/eq endpoint (server mode)
```

#### 📊 `pollStatus()` — Status Poll (1s interval)
```
Server mode:
  Update: tit, art, tech-specs, volume slider, seekbar, play state
  From: /status endpoint (reads mpv metadata)
Browser mode:
  SKIP tit/art/tech-specs (would overwrite with defaults)
  Update: seekbar, cover art, mini queue
```

#### 📋 `updateMiniQueue()` — Mini Queue Display
```
Shows next 2 tracks below seekbar. Refreshes every pollStatus().
```

#### 📋 `initPlaylistPopup()` / `togglePlaylistPopup()` — Playlist Popup
```
Toggle popup with full queue list.
Click item → jump to track (both modes).
Browser mode: calls playBrowserAudio() directly.
```

#### 🎚️ EQ Knobs — `setupKnobs()`, `onDrag()`, `updateUI()`
```
Rotary knobs mapped to -12 to +12 (24-step range).
CSS transform: rotate(deg) for visual.
Event handlers: mousedown, mousemove, mouseup on document.
```

---

## 🗃️ Database Schema

**File:** `music.db` (SQLite, WAL journal mode)

### Table: `tracks`

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | Auto-generated ID |
| `path` | TEXT UNIQUE | Full file path |
| `filename` | TEXT | Base filename |
| `title` | TEXT | Track title from ID3 tag |
| `artist` | TEXT | Artist from ID3 tag |
| `album` | TEXT | Album from ID3 tag |
| `genre` | TEXT | Genre from ID3 tag |
| `year` | TEXT | Year from ID3 tag date |
| `duration` | INTEGER | Track duration in seconds |
| `added_at` | REAL | Unix timestamp when added |

### Sample Queries

```sql
-- Get all tracks sorted by title
SELECT * FROM tracks ORDER BY title ASC;

-- Search by artist
SELECT * FROM tracks WHERE artist LIKE '%Bach%' LIMIT 50;

-- Count by genre
SELECT genre, COUNT(*) as count FROM tracks GROUP BY genre;

-- Newest additions
SELECT title, artist, added_at FROM tracks ORDER BY added_at DESC LIMIT 10;

-- Album listing
SELECT album, artist, COUNT(*) as tracks FROM tracks GROUP BY album ORDER BY album;
```

---

## 🎛️ EQ Preset Reference

### Preset Values (gain in dB per frequency)

| Preset | 32Hz | 64Hz | 125Hz | 250Hz | 500Hz | 1kHz | 2kHz | 4kHz | 8kHz | 16kHz |
|--------|------|------|-------|-------|-------|------|------|------|------|-------|
| **Normal** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Bass** | 7 | 6 | 5 | 3 | 0 | 0 | 0 | -1 | -2 | -3 |
| **Rock** | 5 | 3 | 1 | -1 | -2 | 0 | 2 | 4 | 5 | 5 |
| **Pop** | -1 | 1 | 3 | 4 | 4 | 2 | 0 | 1 | 2 | 2 |
| **Jazz** | 2 | 2 | 4 | 2 | 2 | 4 | 2 | 2 | 3 | 3 |
| **Vocal** | -3 | -3 | -2 | 0 | 4 | 6 | 5 | 3 | 1 | -1 |
| **Dance** | 8 | 7 | 4 | 0 | 0 | 2 | 4 | 5 | 6 | 5 |
| **Acoust** | 1 | 2 | 2 | 3 | 4 | 4 | 3 | 2 | 3 | 2 |
| **Party** | 7 | 6 | 4 | 1 | 2 | 4 | 5 | 5 | 6 | 5 |
| **Soft** | 0 | -1 | -1 | 1 | 2 | 1 | 0 | -1 | -2 | -4 |
| **Metal** | 6 | 5 | 0 | -2 | -3 | 0 | 3 | 6 | 7 | 7 |
| **Classic** | 4 | 3 | 2 | 2 | -1 | -1 | 0 | 2 | 3 | 4 |
| **RnB** | 6 | 5 | 3 | 0 | -1 | 2 | 3 | 2 | 3 | 4 |
| **Live** | -2 | 0 | 2 | 3 | 4 | 4 | 4 | 3 | 2 | 1 |
| **Techno** | 8 | 7 | 0 | -2 | -2 | 0 | 2 | 4 | 6 | 6 |
| **KZEDCPro** | 6 | 5 | 3 | 1 | 0 | 0 | -1 | -1 | 0 | 0 |

### EQ Implementation

The EQ is implemented differently based on mode:

**Server Mode (mpv):**
```
lavfi=[firequalizer=gain_entry='entry(32,0);entry(64,0);...']
```
Applied via mpv's audio filter chain.

**Browser Mode (WebAudio):**
```javascript
// 10 BiquadFilter nodes in series, type='peaking'
filter.frequency.value = freqs[i];  // 32, 64, 125, ... 16000
filter.Q.value = 1.0;
filter.gain.value = settings['f' + (i+1)];  // -12 to +12
```

---

## 🛠️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OWRTMB_PORT` | `2030` | Web UI port |
| `OWRTMB_HOST` | `0.0.0.0` | Bind address |
| `OWRTMB_LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |

### Key File Paths

| Path | Description |
|------|-------------|
| `/tmp/mpv_socket` | MPV IPC socket (server mode) |
| `/root/output_mode` | Saved audio output device string |
| `/root/bp_mode` | Bit-perfect mode flag (0/1) |
| `/root/st4_last_volume` | Last volume state |
| `music.db` | SQLite library database |
| `playlist.json` | Saved playlist data |
| `static/covers/` | Extracted album art cache |
| `uploads/` | User uploaded files |
| `owrt_musicbox.log` | Application log |

---

## 🖥️ OpenWrt LuCI Integration

Add a tab to OpenWrt admin panel:

```bash
cat <<'EOF' >/usr/lib/lua/luci/controller/openwrtmusicbox.lua
module("luci.controller.openwrtmusicbox", package.seeall)
function index()
    entry({"admin", "openwrtmusicbox"}, template("openwrtmusicbox"), _("OpenWrt-Music-Box"), 90).leaf=true
end
EOF

cat <<'EOF' >/usr/lib/lua/luci/view/openwrtmusicbox.htm
<%+header%>
<div class="cbi-map">
    <iframe id="owmb-player" style="width: 100%; min-height: 90vh; border: none; border-radius: 2px;"></iframe>
</div>
<script type="text/javascript">
    document.getElementById("owmb-player").src = window.location.protocol + "//" + window.location.hostname + ":2030";
</script>
<%+footer%>
EOF

rm -rf /tmp/luci-*
```

---

## 📖 Usage

### 🎮 Player Controls
1. **Play Music:** Search YouTube Music via the search bar, paste a YouTube URL, or browse local files in Media Center.
2. **Play Mode:** Choose between **Server mode** (mpv plays audio on the device) or **Browser mode** (audio streams to your browser).
3. **Queue Management:** View, reorder (click to jump), shuffle, and clear your queue.
4. **Equalizer:** Drag the 10-band parametric EQ knobs, or select from **16 presets** (Bass, Rock, Pop, Jazz, Vocal, Metal, etc.)
5. **Balance & Crossfeed:** Adjust left/right balance, mute individual channels, or enable binaural crossfeed for headphones.

### 🎤 Lyrics
- Click the microphone icon to fetch real-time synced lyrics from LRCLIB.

### 🔊 Audio Output
- **Line Out (Jack):** Default analog output via 3.5mm jack.
- **HDMI:** Digital audio via HDMI.
- **Bluetooth:** Scan, pair, and stream to TWS or Bluetooth speakers.

### 📁 File Upload
- Upload audio files directly from the Media Center tab — supports MP3, FLAC, WAV, M4A, OGG, OPUS, AAC, DSF, DFF.

### ⏱️ Sleep Timer
- Set a timer (15min, 30min, 1 hour) to auto-stop playback.

### 📱 PWA
- Open in browser → Add to Home Screen for a native app-like experience.

### Browser Mode Streaming Details

| Endpoint | Description |
|----------|-------------|
| `GET /youtube_proxy?url=` | Proxies YouTube audio stream to the browser (avoids CORS issues) |
| `GET /radio_proxy?url=` | Proxies internet radio streams to the browser |
| `GET /stream?path=` | Streams local audio files with HTTP Range support |
| `POST /upload` | Upload audio files for instant playback |
| `GET /playlist/export_m3u` | Export queue as M3U playlist file |
| `POST /playlist/import_m3u` | Import M3U/M3U8/PLS playlist files |

---

## ⚙️ Tech Stack

* **Backend:** Python 3.11+ (Flask 3.x)
* **Audio Engine:** MPV & BlueALSA
* **YouTube Streaming:** yt-dlp + ytmusicapi + mpv built-in ytdl
* **Database:** SQLite3 (WAL Mode for high concurrency)
* **Metadata:** Mutagen
* **Frontend:** Vanilla JS, FontAwesome 6, PWA
* **Container:** Multi-stage Docker build (Debian Bookworm)
* **Browser Audio:** WebAudio API (GainNode, BiquadFilter, StereoPanner)

---

## 📁 Project Structure

```
openwrt-music-box/
├── app.py                # Main Flask application (1110+ lines)
│                         # ├── State management (Lock + app_state)
│                         # ├── mpv_send (Unix socket IPC)
│                         # ├── trigger_play / play_next_in_queue
│                         # ├── metadata_worker (background thread)
│                         # ├── 20+ API routes
│                         # └── EQ, YouTube proxy, radio proxy
│
├── library.py            # SQLite library manager (WAL mode)
│                         # ├── LibraryManager class
│                         # ├── ID3 tag extraction (mutagen)
│                         # ├── Async directory scanner
│                         # ├── Search, sort, CRUD
│                         # └── lib_mgr singleton
│
├── bt_manager.py         # Bluetooth manager class
│
├── play.sh               # MPV audio player wrapper (88 lines)
│                         # ├── Volume persistence
│                         # ├── Audio device detection
│                         # ├── Bit-perfect mode config
│                         # └── Cache & ytdl options
│
├── toggle_output.sh      # Audio output switcher
├── install.sh            # All-in-one installer (6 steps)
├── run.sh                # Convenience start script (auto-generated)
├── Dockerfile            # Multi-stage Docker build
├── docker-compose.yml    # Docker Compose configuration
├── requirements.txt      # Python dependencies
├── .gitignore            # Git ignore rules
│
├── static/
│   ├── js/script.js      # Frontend (830+ lines, COREv9)
│   │                     # ├── WebAudio init (ONE-TIME)
│   │                     # ├── 10-band EQ via BiquadFilter
│   │                     # ├── StereoPanner balance
│   │                     # ├── GainNode volume
│   │                     # ├── playBrowserAudio engine
│   │                     # ├── Queue management
│   │                     # └── Playlist popup
│   │
│   ├── sw.js             # Service Worker (PWA offline cache)
│   ├── css/style.css     # Main stylesheet
│   ├── css/all.min.css   # FontAwesome 6
│   ├── img/              # Images & icons
│   ├── covers/           # Extracted album covers cache
│   └── webfonts/         # FontAwesome 6 fonts
│
└── templates/
    └── index.html        # Single-page web UI (242 lines)
                          # ├── Player card (dashboard)
                          # ├── Controls & seek
                          # ├── EQ section with knobs
                          # ├── Search, Queue, Library
                          # └── Popups (radio, output, timer, etc.)
```

---

## 🧹 Logging

- **File:** `owrt_musicbox.log` di direktori aplikasi (otomatis dibuat)
- **Stdout:** Juga tampil di terminal / `docker logs`
- **Level:** Atur via `OWRTMB_LOG_LEVEL` (DEBUG, INFO, WARNING, ERROR)

Contoh melihat log:
```bash
tail -f owrt_musicbox.log
docker logs -f openwrt-music-box
```

---

## 🐛 Troubleshooting

| Masalah | Solusi |
|---------|--------|
| **mpv not found** | Di OpenWrt, mpv tidak tersedia. Gunakan metode Docker |
| **YouTube playback error** | Pastikan `yt-dlp` terinstall: `pip3 list \| grep yt-dlp` |
| **Bluetooth not working** | Pastikan D-Bus policy sudah dibuat |
| **No audio in browser mode** | Periksa konsol browser untuk error `createMediaElementSource`. Refresh halaman jika WebAudio corrupt. |
| **Next/prev tidak bersuara** | Pastikan di browser mode, backend `trigger_play()` skip mpv. Cek commit `5419309` |
| **Metadata "Ready"/"Waiting..." terus** | Ini bug frontend — `pollStatus()` overwrite di browser mode. Komit `c3353a4` fix ini dengan parse `"Artist - Title"` |
| **EQ/Volume/Balance tidak berfungsi** | COREv8 hapus WebAudio. COREv9 (`5419309`) restore dengan `createMediaElementSource` satu kali. |
| **Docker build gagal: DNS** | Konfigurasi `/etc/docker/daemon.json` dengan `"dns": ["8.8.8.8", "1.1.1.1"]` |
| **Play → pause → play restart** | Bug di `togglePlay()` browser mode — komit `5936aa8` fix dengan resume tanpa reload src |

---

## 🔄 Changelog

### 2024-07-13 — `c3353a4` — Metadata display fix
- `playBrowserAudio()` now parses "Artist - Title" format
- Sets `#art` and `#tech-specs` directly (no longer reliant on backend)

### 2024-07-13 — `5936aa8` — Pause/Resume + Browser metadata fix
- `togglePlay()` browser mode: resume without reloading src
- `pollStatus()` browser mode: skip overwriting tit/art/tech-specs

### 2024-07-13 — `5419309` — COREv9: WebAudio restored
- `initWebAudioOnce()` — `createMediaElementSource()` dipanggil SEKALI
- Ganti lagu hanya dengan `browserAudio.src = baru`, graph tetap utuh

### 2024-07-13 — `fdc96a7` — COREv8: Stable playback (No WebAudio)
- Hapus WebAudio sementara karena `createMediaElementSource()` corrupt
- `playBrowserAudio()` dengan reset + `canplay` event

### 2024-07-13 — `b72bd17` — Autoplay + Volume sync
- `play()` promise catch → toast "Tap to play" + click handler
- Volume slider hanya sync di server mode

### 2024-07-13 — `4aa1ab1` — Browser mode + Playlist popup
- `trigger_play()` skip mpv di browser mode
- `metadata_worker` skip mpv polling di browser mode
- Playlist popup dashboard dengan toggle

### 2024-07-13 — `bafb008` — 3 perbaikan besar
- WebAudio: 10-band EQ, StereoPanner, GainNode
- Mini queue auto-refresh
- Browser mode playback via HTML5 audio

### 2024-07-13 — `406cce6` — Audio device + race condition fix
- `play.sh`: fix audio device override bug
- `metadata_worker`: reset idle_counter saat status "loading"

### 2024-07-13 — `3705ee4` — Next/Prev queue fix
- Hapus browser-mode conditionals di `play_next_in_queue()` dan `/play`

---

## 📝 License

This project is open-source and available under the MIT License. Feel free to fork, modify, and build upon it!