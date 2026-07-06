#!/bin/bash
# Menerima string device (misal: "alsa/bluealsa:DEV=XX...")
DEVICE_STRING="$1"
MODE_FILE="/root/output_mode"

# Bersihkan input dari spasi/newline yang tidak perlu
CLEAN_DEV=$(echo "$DEVICE_STRING" | tr -d '\n' | xargs)

if [ -z "$CLEAN_DEV" ]; then
    # Default fallback ke Jack Audio (Tinkerboard Card 1, Dev 2)
    echo "alsa/plughw:1,2" > "$MODE_FILE"
else
    echo "$CLEAN_DEV" > "$MODE_FILE"
fi

# Pastikan file tetap bisa dibaca/tulis oleh Python
chmod 666 "$MODE_FILE"