#!/bin/bash

export PATH=$PATH:/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin:/app/bin
export LC_ALL=C.UTF-8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SOCKET="/tmp/mpv_socket"
MODE_FILE="/root/output_mode"
BP_FILE="/root/bp_mode"
LOG_FILE="/root/mpv_error.log"
VOL_FILE="/root/owmb_last_volume"
INPUT_LINK="$1"
START_TIME="${2:-0}"

TARGET_VOL=30

# Ambil volume terakhir
if [ -S "$SOCKET" ]; then
    RAW_VOL=$(echo '{ "command": ["get_property", "volume"] }' | socat - "$SOCKET" 2>/dev/null)
    PARSED_VOL=$(echo "$RAW_VOL" | sed -n 's/.*"data": *\([0-9.]*\).*/\1/p')
    if [ -n "$PARSED_VOL" ]; then
        TARGET_VOL=$PARSED_VOL
        echo "$TARGET_VOL" > "$VOL_FILE"
    fi
fi
if [ -z "$PARSED_VOL" ] && [ -f "$VOL_FILE" ]; then
    TARGET_VOL=$(cat "$VOL_FILE")
fi

# Soft kill mpv sebelumnya
if [ -S "$SOCKET" ]; then
    echo '{ "command": ["quit"] }' | socat - "$SOCKET" 2>/dev/null || true
    sleep 0.3
fi
if pgrep mpv > /dev/null 2>&1; then
    killall mpv 2>/dev/null || true
    sleep 0.3
fi
rm -f "$SOCKET"
sleep 0.5

MPV_BIN=$(which mpv)
if [ -z "$MPV_BIN" ]; then MPV_BIN="/usr/bin/mpv"; fi

# === AUDIO DEVICE DETECTION ===
AUDIO_DEVICE=""
if [ -f "$MODE_FILE" ]; then
    READ_MODE=$(cat "$MODE_FILE" | tr -d '\n')
    if [ -n "$READ_MODE" ]; then
        AUDIO_DEVICE="$READ_MODE"
    fi
fi

# Fallback: deteksi device ALSA
if [ -z "$AUDIO_DEVICE" ]; then
    for dev in "alsa/plughw:1,2" "alsa/plughw:0,0" "alsa/plughw:1,0" "alsa/default"; do
        if [ -e "/dev/snd/" ] && mpv --audio-device=help 2>/dev/null | grep -qi "${dev#alsa/}"; then
            AUDIO_DEVICE="$dev"
            break
        fi
    done
fi
if [ -z "$AUDIO_DEVICE" ]; then
    AUDIO_DEVICE="alsa/plughw:0,0"
fi

# === EXTRA ARGS ===
EXTRA_ARGS=""
if [[ "$AUDIO_DEVICE" == *"bluealsa"* ]]; then
    EXTRA_ARGS="--ao=alsa --audio-format=s16 --audio-samplerate=44100 --audio-buffer=0.5"
else
    IS_BP="0"
    if [ -f "$BP_FILE" ]; then IS_BP=$(cat "$BP_FILE" | tr -d '[:space:]'); fi
    if [ "$IS_BP" == "1" ]; then
        EXTRA_ARGS="--ao=alsa --no-audio-resample --audio-buffer=0.2"
    else
        EXTRA_ARGS="--ao=alsa"
    fi
fi

# === YOUTUBE: Extract direct audio URL via Python ===
ACTUAL_URL="$INPUT_LINK"

if [[ "$INPUT_LINK" == *"youtube.com"* || "$INPUT_LINK" == *"youtu.be"* || "$INPUT_LINK" == *"music.youtube.com"* ]]; then
    echo "[YTDL] Extracting audio URL from YouTube..."
    
    # Coba extract via Python script
    YTDL_SCRIPT="$SCRIPT_DIR/ytdl_extract.py"
    if [ -f "$YTDL_SCRIPT" ]; then
        YTDL_OUTPUT=$(python3 "$YTDL_SCRIPT" "$INPUT_LINK" 2>/dev/null)
        AUDIO_URL=$(echo "$YTDL_OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('audio_url','') or d.get('url',''))" 2>/dev/null)
        TITLE=$(echo "$YTDL_OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('title',''))" 2>/dev/null)
        ERROR=$(echo "$YTDL_OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error',''))" 2>/dev/null)
        
        if [ -n "$AUDIO_URL" ] && [ "$AUDIO_URL" != "None" ]; then
            ACTUAL_URL="$AUDIO_URL"
            echo "[YTDL] Extracted: $TITLE"
        else
            echo "[YTDL] Python extract failed: $ERROR"
            echo "[YTDL] Falling back to MPV built-in ytdl..."
        fi
    fi
    
    # Fallback: coba extract via yt-dlp binary langsung
    if [ "$ACTUAL_URL" = "$INPUT_LINK" ]; then
        YT_DLP_BIN=$(which yt-dlp 2>/dev/null)
        if [ -z "$YT_DLP_BIN" ] && [ -f "$SCRIPT_DIR/bin/yt-dlp" ]; then
            YT_DLP_BIN="$SCRIPT_DIR/bin/yt-dlp"
        fi
        if [ -n "$YT_DLP_BIN" ]; then
            AUDIO_URL=$("$YT_DLP_BIN" -f bestaudio --get-url "$INPUT_LINK" 2>/dev/null)
            if [ -n "$AUDIO_URL" ]; then
                ACTUAL_URL="$AUDIO_URL"
                echo "[YTDL] Extracted via yt-dlp binary"
            fi
        fi
    fi
fi

# === CACHE & YT-DLP OPTIONS (for non-extracted URLs) ===
CACHE_OPTS="--cache=yes --demuxer-max-bytes=20M --demuxer-max-back-bytes=10M"
YTDL_OPTS=""

if [ -f "$ACTUAL_URL" ]; then
    CACHE_OPTS="--cache=yes --demuxer-max-bytes=5M"
else
    # Only use ytdl options if we couldn't extract the URL
    if [ "$ACTUAL_URL" = "$INPUT_LINK" ]; then
        YT_DLP_BIN=$(which yt-dlp 2>/dev/null)
        if [ -z "$YT_DLP_BIN" ] && [ -f "$SCRIPT_DIR/bin/yt-dlp" ]; then
            YT_DLP_BIN="$SCRIPT_DIR/bin/yt-dlp"
        fi
        if [ -n "$YT_DLP_BIN" ]; then
            YTDL_OPTS="--script-opts=ytdl_hooks-ytdl_path=$YT_DLP_BIN --ytdl-format=bestaudio/best --ytdl-raw-options=ignore-errors=,no-check-certificate="
        else
            YTDL_OPTS="--ytdl-format=bestaudio/best --ytdl-raw-options=ignore-errors=,no-check-certificate="
        fi
        # Enable ytdl in MPV
        YTDL_OPTS="$YTDL_OPTS --ytdl=yes"
    fi
fi

# Simpan AUDIO_DEVICE
echo "$AUDIO_DEVICE" > "$MODE_FILE" 2>/dev/null || true

echo "[PLAY] URL: ${ACTUAL_URL:0:80}..."
echo "[PLAY] Device: $AUDIO_DEVICE"

nohup "$MPV_BIN" "$ACTUAL_URL" \
    --start="$START_TIME" \
    --input-ipc-server="$SOCKET" \
    --no-video \
    --force-window=no \
    --no-terminal \
    --volume="$TARGET_VOL" \
    --audio-device="$AUDIO_DEVICE" \
    --keep-open=yes \
    --idle=yes \
    --gapless=yes \
    --msg-level=all=error \
    $CACHE_OPTS \
    $YTDL_OPTS \
    $EXTRA_ARGS \
    >> "$LOG_FILE" 2>&1 &
disown