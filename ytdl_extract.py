#!/usr/bin/env python3
"""
ytdl_extract.py — Extract direct audio URL from YouTube using yt-dlp.
Output: JSON with audio_url, title, thumbnail
Usage: python3 ytdl_extract.py <youtube_url>
"""
import json, sys, os

# Try multiple import paths for yt-dlp
yt_dlp = None
for mod_name in ['yt_dlp', 'ytdlp', 'youtube_dl']:
    try:
        yt_dlp = __import__(mod_name)
        break
    except ImportError:
        continue

if not yt_dlp:
    # Fallback: try subprocess calling yt-dlp binary
    import subprocess
    result = {"error": "yt-dlp not installed"}
    print(json.dumps(result))
    sys.exit(1)

def extract(url):
    """Extract best audio URL from YouTube URL."""
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Get best audio format
            audio_url = None
            title = info.get('title', 'Unknown')
            thumbnail = info.get('thumbnail', '')
            
            # Try to get direct audio URL
            formats = info.get('formats', [])
            if formats:
                # Prefer audio-only formats
                audio_formats = [f for f in formats if f.get('vcodec') == 'none' and f.get('acodec') != 'none']
                if audio_formats:
                    # Sort by bitrate (highest first)
                    audio_formats.sort(key=lambda f: f.get('tbr', 0) or 0, reverse=True)
                    best = audio_formats[0]
                    audio_url = best.get('url') or best.get('manifest_url') or ''
                else:
                    # Fallback: use first format with audio
                    for f in formats:
                        if f.get('url') and f.get('acodec') != 'none':
                            audio_url = f['url']
                            break
            
            # If no format found, use the info URL
            if not audio_url:
                audio_url = info.get('url', '')
            
            result = {
                'audio_url': audio_url,
                'title': title,
                'thumbnail': thumbnail,
                'duration': info.get('duration', 0)
            }
            print(json.dumps(result))
            return 0
            
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result))
        return 1

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No URL provided"}))
        sys.exit(1)
    sys.exit(extract(sys.argv[1]))