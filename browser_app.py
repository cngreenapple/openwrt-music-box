"""
OpenWrt-Music-Box BROWSER MODE server.
Runs on port 2031, handles browser-based audio playback without mpv.
"""
from flask import Flask, render_template, request, jsonify, send_file, Response, abort, stream_with_context
import uuid
import subprocess
import json
import os
import re
import requests
from ytmusicapi import YTMusic

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLAYLIST_FILE = os.path.join(BASE_DIR, "playlist.json")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

AUDIO_EXTS = ('.mp3', '.flac', '.wav', '.m4a', '.ogg', '.opus', '.wma', '.aac', '.dsf', '.dff')
yt_music = YTMusic()

# In-memory queue state
browser_state = {
    "queue": [],
    "current_index": -1,
    "status": "stopped"
}

# ========================
# QUEUE MANAGEMENT (shared state with app.py via this simple in-memory store)
# ========================

@app.route('/browser_play', methods=['GET', 'POST'])
def browser_play():
    """Play a song in browser mode (no mpv)."""
    url = request.args.get('url') or request.form.get('link')
    mode = request.args.get('mode', 'play_now')
    title = request.args.get('title', 'Unknown Title')
    if not url: return jsonify({"error": "no url"})
    song_obj = {'link': url, 'title': title}

    if mode == 'play_now':
        if os.path.exists(url) and os.path.isfile(url):
            folder_path = os.path.dirname(url)
            try:
                folder_files = [f for f in os.listdir(folder_path) if f.lower().endswith(AUDIO_EXTS)]
                folder_files.sort(key=lambda x: x.lower())
                new_queue = []
                target_index = 0
                for idx, fname in enumerate(folder_files):
                    full_path = os.path.join(folder_path, fname)
                    new_queue.append({'link': full_path, 'title': fname})
                    if full_path == url: target_index = idx
                browser_state["queue"] = new_queue
                browser_state["current_index"] = target_index
            except:
                browser_state["queue"] = [song_obj]; browser_state["current_index"] = 0
        elif "youtube.com" in url or "youtu.be" in url:
            browser_state["queue"] = [song_obj]; browser_state["current_index"] = 0
            try:
                match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
                video_id = match.group(1) if match else None
                if video_id:
                    data = yt_music.get_watch_playlist(videoId=video_id, limit=20)
                    if 'tracks' in data:
                        new_queue = []
                        for t in data['tracks']:
                            vid = t.get('videoId')
                            if vid:
                                t_artist = t['artists'][0]['name'] if 'artists' in t and t['artists'] else ""
                                full_title = f"{t_artist} - {t['title']}" if t_artist else t['title']
                                new_queue.append({'link': f"https://music.youtube.com/watch?v={vid}", 'title': full_title})
                        if new_queue: browser_state["queue"] = new_queue; browser_state["current_index"] = 0
            except: pass
        else:
            browser_state["queue"] = [song_obj]; browser_state["current_index"] = 0
        
        browser_state["status"] = "playing"
    elif mode == 'enqueue':
        browser_state["queue"].append(song_obj)
    
    return jsonify({"status": "ok", "mode": mode, "queue_len": len(browser_state["queue"])})

@app.route('/play/current')
def play_current():
    idx = browser_state["current_index"]
    if 0 <= idx < len(browser_state["queue"]):
        s = browser_state["queue"][idx]
        return jsonify({"index": idx, "title": s['title'], "link": s['link'], "thumb": ""})
    return jsonify({"index": -1})

@app.route('/play/next_browser')
def next_browser():
    if not browser_state["queue"]:
        return jsonify({"index": -1})
    next_idx = browser_state["current_index"] + 1
    if next_idx < len(browser_state["queue"]):
        browser_state["current_index"] = next_idx
        next_song = browser_state["queue"][next_idx]
        return jsonify({"index": next_idx, "title": next_song['title'], "link": next_song['link'], "thumb": ""})
    else:
        browser_state["status"] = "stopped"
        return jsonify({"index": -1})

@app.route('/queue/list')
def get_queue():
    return jsonify({"queue": browser_state["queue"], "current_index": browser_state["current_index"]})

@app.route('/queue/clear')
def clear_queue():
    browser_state["queue"] = []; browser_state["current_index"] = -1
    return jsonify({"status": "cleared"})

@app.route('/control/jump')
def jump_to_index():
    try:
        idx = int(request.args.get('index', -1))
        if 0 <= idx < len(browser_state["queue"]):
            browser_state["current_index"] = idx
            song = browser_state["queue"][idx]
            return jsonify({"status": "ok", "title": song['title']})
    except: pass
    return jsonify({"error": "invalid index"})

# ========================
# STREAMING & PROXY
# ========================

@app.route('/stream')
def stream_file():
    path = request.args.get('path', '')
    if not path or not os.path.exists(path): abort(404)
    range_header = request.headers.get('Range', None)
    file_size = os.path.getsize(path)
    ext = os.path.splitext(path)[1].lower()
    mime_map = {'.mp3':'audio/mpeg','.flac':'audio/flac','.wav':'audio/wav','.m4a':'audio/mp4','.ogg':'audio/ogg','.opus':'audio/ogg','.wma':'audio/x-ms-wma','.aac':'audio/aac'}
    mime = mime_map.get(ext, 'audio/mpeg')
    if range_header:
        m = re.search(r'(\d+)-(\d*)', range_header)
        if m:
            byte1 = int(m.group(1)); byte2 = int(m.group(2)) if m.group(2) else file_size-1
            length = byte2 - byte1 + 1
            with open(path, 'rb') as f: f.seek(byte1); data = f.read(length)
            resp = Response(data, 206, mimetype=mime, content_type=mime, direct_passthrough=True)
            resp.headers.add('Content-Range', f'bytes {byte1}-{byte2}/{file_size}')
            resp.headers.add('Accept-Ranges', 'bytes'); resp.headers.add('Content-Length', str(length))
            return resp
    return send_file(path, mimetype=mime)

@app.route('/youtube_proxy')
def youtube_proxy():
    url = request.args.get('url', '')
    if not url: return jsonify({"error": "no url"}), 400
    try:
        import yt_dlp
        ydl_opts = {'format': 'bestaudio/best', 'quiet': True, 'no_warnings': True, 'youtube_include_dash_manifest': False}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            direct_url = info.get('url', '')
        if not direct_url: return jsonify({"error": "could not extract audio URL"}), 500
        headers = {'User-Agent': 'Mozilla/5.0', 'Accept': '*/*', 'Range': request.headers.get('Range', 'bytes=0-')}
        resp = requests.get(direct_url, headers=headers, stream=True, timeout=30)
        def generate():
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk: yield chunk
        response = Response(stream_with_context(generate()), status=resp.status_code, content_type=resp.headers.get('Content-Type', 'audio/webm'))
        if 'Content-Range' in resp.headers: response.headers['Content-Range'] = resp.headers['Content-Range']
        if 'Content-Length' in resp.headers: response.headers['Content-Length'] = resp.headers['Content-Length']
        if 'Accept-Ranges' in resp.headers: response.headers['Accept-Ranges'] = resp.headers['Accept-Ranges']
        return response
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/radio_proxy')
def radio_proxy():
    url = request.args.get('url', '')
    if not url: return jsonify({"error": "no url"}), 400
    try:
        headers = {'User-Agent': 'Mozilla/5.0', 'Accept': '*/*'}
        resp = requests.get(url, headers=headers, stream=True, timeout=30)
        def generate():
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk: yield chunk
        return Response(stream_with_context(generate()), status=resp.status_code, content_type=resp.headers.get('Content-Type', 'audio/mpeg'))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========================
# FILE MANAGEMENT
# ========================

@app.route('/get_files')
def get_files():
    target = request.args.get('path', '/')
    items = []
    if target == '/':
        return jsonify([
            {'name': '🏠 Internal Storage (/root)', 'path': '/root', 'type': 'dir'},
            {'name': '💾 External HDD/USB (/mnt)', 'path': '/mnt', 'type': 'dir'},
            {'name': '📁 Uploads', 'path': UPLOAD_DIR, 'type': 'dir'},
            {'name': '🎵 Music Library', 'path': '/root/music', 'type': 'dir'}
        ])
    try:
        abs_path = os.path.abspath(target)
        if abs_path != '/':
            parent = os.path.dirname(abs_path)
            if abs_path in ['/root', '/mnt']: parent = '/'
            items.append({'name': '..', 'path': parent, 'type': 'dir'})
        with os.scandir(abs_path) as entries:
            entry_list = list(entries)
            entry_list.sort(key=lambda e: (not e.is_dir(), e.name.lower()))
            for entry in entry_list:
                if entry.name.startswith('.'): continue
                if entry.is_dir():
                    items.append({'name': entry.name, 'path': entry.path, 'type': 'dir'})
                elif entry.is_file() and entry.name.lower().endswith(AUDIO_EXTS):
                    items.append({'name': entry.name, 'path': entry.path, 'type': 'file'})
    except: pass
    return jsonify(items)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files: return jsonify({"error":"no file"}),400
    f = request.files['file']
    if not f.filename: return jsonify({"error":"no filename"}),400
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in AUDIO_EXTS: return jsonify({"error":"unsupported format"}),400
    uid = str(uuid.uuid4())[:8]
    safe_name = f"{uid}_{f.filename}"
    f.save(os.path.join(UPLOAD_DIR, safe_name))
    return jsonify({"status":"ok","filename":safe_name,"path":os.path.join(UPLOAD_DIR, safe_name)})

@app.route('/uploads')
def list_uploads():
    files = []
    if os.path.exists(UPLOAD_DIR):
        for fn in sorted(os.listdir(UPLOAD_DIR), key=lambda x: os.path.getmtime(os.path.join(UPLOAD_DIR, x)), reverse=True):
            fp = os.path.join(UPLOAD_DIR, fn)
            if os.path.isfile(fp) and fn.lower().endswith(AUDIO_EXTS):
                files.append({"name":fn, "path":fp, "size":os.path.getsize(fp)})
    return jsonify(files)

@app.route('/search')
def search_yt():
    query = request.args.get('q', '')
    if not query: return jsonify([])
    try:
        results = yt_music.search(query, filter="videos", limit=30)
        data = []
        for r in results:
            thumb = r['thumbnails'][-1]['url'] if 'thumbnails' in r else ""
            artists = ", ".join([a['name'] for a in r.get('artists', [])])
            data.append({'title': r.get('title'), 'artist': artists, 'duration': r.get('duration',''), 'thumb': thumb, 'link': f"https://music.youtube.com/watch?v={r['videoId']}", 'videoId': r['videoId']})
        return jsonify(data)
    except: return jsonify([])

# ========================
# PLAYLIST
# ========================

@app.route('/get_playlist')
def get_playlist():
    if os.path.exists(PLAYLIST_FILE):
        try:
            with open(PLAYLIST_FILE, 'r') as f: return jsonify(json.load(f))
        except: pass
    return jsonify([])

@app.route('/save_playlist', methods=['POST'])
def save_playlist():
    try:
        with open(PLAYLIST_FILE, 'w') as f: json.dump(request.json, f)
        return jsonify({"status": "ok"})
    except: return jsonify({"error": "failed"}), 500

@app.route('/playlist/export_m3u')
def export_m3u():
    from io import StringIO
    if not browser_state["queue"]:
        return jsonify({"error": "empty queue"}), 404
    lines = ["#EXTM3U"]
    for item in browser_state["queue"]:
        lines.append(f"#EXTINF:-1,{item['title']}")
        lines.append(item['link'])
    content = "\n".join(lines)
    return Response(content, mimetype='audio/x-mpegurl', headers={'Content-Disposition': 'attachment; filename=playlist.m3u'})

@app.route('/playlist/import_m3u', methods=['POST'])
def import_m3u():
    try:
        text = request.get_data(as_text=True)
        if not text: return jsonify({"status": "error", "info": "empty"}), 400
        lines = text.strip().split('\n')
        imported = 0
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('['): continue
            if line.startswith('http') or os.path.exists(line):
                browser_state["queue"].append({'link': line, 'title': "Unknown"})
                imported += 1
        if imported > 0 and browser_state["status"] == "stopped":
            browser_state["current_index"] = 0
        return jsonify({"status": "ok", "imported": imported})
    except Exception as e:
        return jsonify({"status": "error", "info": str(e)}), 500

@app.route('/system/default_path', methods=['GET', 'POST'])
def handle_default_path():
    DEFAULT_PATH_FILE = os.path.join(BASE_DIR, "default_path.txt")
    if request.method == 'POST':
        try:
            data = request.json; new_path = data.get('path', '/root')
            if os.path.exists(new_path):
                with open(DEFAULT_PATH_FILE, 'w') as f: f.write(new_path)
                return jsonify({"status": "ok", "path": new_path})
            else: return jsonify({"error": "Path not found"}), 404
        except Exception as e: return jsonify({"error": str(e)}), 500
    else:
        path = "/root/music"
        if os.path.exists(DEFAULT_PATH_FILE):
            try:
                with open(DEFAULT_PATH_FILE, 'r') as f: path = f.read().strip()
            except: pass
        return jsonify({"path": path})

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    print("Browser mode server starting on port 2031...")
    app.run(host='0.0.0.0', port=2031, debug=False)