#!/bin/bash
# ============================================
# Owrt-MusicBox / OpenWrt-Music-Box Uninstaller
# ============================================
# Menghapus semua bekas instalasi (container Docker,
# image, venv, file runtime, LuCI) dari versi LAMA
# maupun BARU. Siap untuk install fresh.
# ============================================

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log_info()  { echo -e "${CYAN}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_done()  { echo -e "${GREEN}✅ $1${NC}"; }

echo ""
echo -e "${RED}============================================${NC}"
echo -e "${RED}    Owrt-MusicBox — Uninstall${NC}"
echo -e "${RED}============================================${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ============================================
# 1. STOP & HAPUS Docker Container
# ============================================
echo -e "${YELLOW}---[1/6] Docker Container ---${NC}"

# Cari semua container terkait
for name in "owrt-musicbox" "openwrt-music-box" "st4-player"; do
    CID=$(docker ps -a --format '{{.ID}} {{.Names}}' 2>/dev/null | grep -i "$name" | head -1 | awk '{print $1}')
    if [ -n "$CID" ]; then
        log_info "Stopping & removing container: $name"
        docker stop "$CID" 2>/dev/null || true
        docker rm "$CID" 2>/dev/null || true
        log_ok "Removed container: $name"
    fi
done

# Hapus container via docker-compose (jika ada compose file)
if [ -f "$SCRIPT_DIR/docker-compose.yml" ]; then
    cd "$SCRIPT_DIR"
    docker-compose down 2>/dev/null || true
    log_info "docker-compose down executed"
fi

# ============================================
# 2. HAPUS Docker Image
# ============================================
echo ""
echo -e "${YELLOW}---[2/6] Docker Images ---${NC}"

for img in "owrt-musicbox" "openwrt-music-box" "openwrt-music-box-openwrt-music-box" "st4-player"; do
    IID=$(docker images --format '{{.Repository}}:{{.Tag}} {{.ID}}' 2>/dev/null | grep -i "$img" | head -1 | awk '{print $2}')
    if [ -n "$IID" ]; then
        log_info "Removing image: $img"
        docker rmi "$IID" 2>/dev/null || true
        log_ok "Removed image: $img"
    fi
done

# Hapus image yang tidak ada tag (dangling)
docker image prune -f 2>/dev/null || true
log_info "Pruned dangling images"

# ============================================
# 3. HAPUS Python Virtual Environment
# ============================================
echo ""
echo -e "${YELLOW}---[3/6] Python Virtual Environment ---${NC}"

if [ -d "$SCRIPT_DIR/venv" ]; then
    rm -rf "$SCRIPT_DIR/venv"
    log_ok "Removed: $SCRIPT_DIR/venv"
else
    log_info "No venv found"
fi

# ============================================
# 4. HAPUS File Runtime & Database
# ============================================
echo ""
echo -e "${YELLOW}---[4/6] Runtime Files & Database ---${NC}"

# File runtime di root
for f in /root/output_mode /root/bp_mode /root/owmb_last_volume /root/st4_last_volume; do
    if [ -f "$f" ]; then
        rm -f "$f"
        log_ok "Removed: $f"
    fi
done

# Database
for f in music.db music.db-wal music.db-shm st4player.log owrt_musicbox.log; do
    if [ -f "$SCRIPT_DIR/$f" ]; then
        rm -f "$SCRIPT_DIR/$f"
        log_ok "Removed: $SCRIPT_DIR/$f"
    fi
done

# Data directory
if [ -d "$SCRIPT_DIR/data" ]; then
    rm -rf "$SCRIPT_DIR/data"
    log_ok "Removed: $SCRIPT_DIR/data"
fi

# Playlist
if [ -f "$SCRIPT_DIR/playlist.json" ]; then
    rm -f "$SCRIPT_DIR/playlist.json"
    log_ok "Removed: playlist.json"
fi

# run.sh
if [ -f "$SCRIPT_DIR/run.sh" ]; then
    rm -f "$SCRIPT_DIR/run.sh"
    log_ok "Removed: run.sh"
fi

# Socket MPV (kalau ada)
if [ -f "/tmp/mpv_socket" ]; then
    rm -f /tmp/mpv_socket
    log_ok "Removed: /tmp/mpv_socket"
fi

# Covers
if [ -d "$SCRIPT_DIR/static/covers" ]; then
    rm -rf "$SCRIPT_DIR/static/covers"
    log_ok "Removed: static/covers"
fi

# ============================================
# 5. HAPUS LuCI Integration
# ============================================
echo ""
echo -e "${YELLOW}---[5/6] LuCI Integration ---${NC}"

# Controller — cek beberapa nama
for name in openwrtmusicbox owrtmusicbox st4player; do
    if [ -f "/usr/lib/lua/luci/controller/${name}.lua" ]; then
        rm -f "/usr/lib/lua/luci/controller/${name}.lua"
        log_ok "Removed: /usr/lib/lua/luci/controller/${name}.lua"
    fi
done

# View
for name in openwrtmusicbox owrtmusicbox st4player; do
    if [ -f "/usr/lib/lua/luci/view/${name}.htm" ]; then
        rm -f "/usr/lib/lua/luci/view/${name}.htm"
        log_ok "Removed: /usr/lib/lua/luci/view/${name}.htm"
    fi
done

# Clear LuCI cache
if [ -d /tmp/luci-* ]; then
    rm -rf /tmp/luci-*
    log_ok "Cleared LuCI cache"
fi

# ============================================
# 6. HAPUS Default Path File (optional)
# ============================================
echo ""
echo -e "${YELLOW}---[6/6] Misc ---${NC}"

if [ -f "$SCRIPT_DIR/default_path.txt" ]; then
    rm -f "$SCRIPT_DIR/default_path.txt"
    log_ok "Removed: default_path.txt"
fi

# MPV error log
if [ -f "/root/mpv_error.log" ]; then
    rm -f /root/mpv_error.log
    log_ok "Removed: /root/mpv_error.log"
fi

# ============================================
# SELESAI
# ============================================
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}       ✅ UNINSTALL COMPLETE!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "${YELLOW}Semua bekas instalasi telah dihapus:${NC}"
echo -e "  • Docker container & image (lama & baru)"
echo -e "  • Python virtual environment"
echo -e "  • Database, log, runtime files"
echo -e "  • LuCI integration (lama & baru)"
echo ""
echo -e "${CYAN}Sekarang Anda bisa install fresh:${NC}"
echo -e "  ./install.sh"
echo -e "  Atau: git clone && cd openwrt-music-box && ./install.sh"
echo ""