import os
import zipfile
import shutil
import subprocess
import urllib.request
import ssl
import sys

# --- KONFIGURASI ---
FA_VERSION = "6.4.2"
FA_URL = f"https://use.fontawesome.com/releases/v{FA_VERSION}/fontawesome-free-{FA_VERSION}-web.zip"
ZIP_NAME = "temp_fa.zip"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Bypass SSL (Penting buat SBC/IoT lama)
ssl._create_default_https_context = ssl._create_unverified_context

def download_robust(url, dest):
    """Mencoba download pake wget (Linux) dulu, kalau gagal pake Python"""
    print(f"⬇️  Downloading FontAwesome v{FA_VERSION}...")
    
    # CARA 1: Pake WGET (Lebih Kuat & Stabil di Linux)
    if shutil.which("wget"):
        print("   [Mode: System Wget] - Lebih stabil...")
        try:
            # -c = continue (resume), -O = output file, --tries = coba ulang kalau gagal
            cmd = ["wget", "-c", "--tries=3", "--timeout=30", "-O", dest, url]
            subprocess.check_call(cmd)
            if os.path.exists(dest):
                print("✅ Download via Wget Selesai.")
                return True
        except subprocess.CalledProcessError:
            print("⚠️ Wget gagal, beralih ke Python Native...")
    
    # CARA 2: Pake Python Native (Chunk Download)
    print("   [Mode: Python Stream] - Memulai download...")
    try:
        with urllib.request.urlopen(url, timeout=45) as response:
            with open(dest, 'wb') as out_file:
                shutil.copyfileobj(response, out_file, length=16*1024) # Download per 16KB
        print("✅ Download via Python Selesai.")
        return True
    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")
        return False

def main():
    print(f"🚀 OpenWrt-Music-Box OFFLINE ASSET MANAGER (V2)")
    print(f"----------------------------------------")
    
    # 1. Cek & Bersihkan Folder Lama
    css_target = os.path.join(STATIC_DIR, "css")
    fonts_target = os.path.join(STATIC_DIR, "webfonts")
    
    if not os.path.exists(css_target): os.makedirs(css_target)
    
    # Hapus zip corrupt sisa download sebelumnya
    if os.path.exists(ZIP_NAME):
        print("🧹 Membersihkan file sampah lama...")
        os.remove(ZIP_NAME)

    # 2. Eksekusi Download
    if not download_robust(FA_URL, ZIP_NAME):
        print("❌ Download gagal total. Cek koneksi internet lu bray.")
        sys.exit(1)

    # 3. Ekstrak & Install
    print("📦 Extracting & Installing...")
    try:
        # Bersihkan folder font lama biar gak conflict
        if os.path.exists(fonts_target): shutil.rmtree(fonts_target)
        os.makedirs(fonts_target)

        with zipfile.ZipFile(ZIP_NAME, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            count = 0
            for file in file_list:
                # Ambil all.min.css
                if file.endswith("css/all.min.css"):
                    with zip_ref.open(file) as source, open(os.path.join(css_target, "all.min.css"), "wb") as target:
                        shutil.copyfileobj(source, target)
                    print(f"   -> Installed: css/all.min.css")
                
                # Ambil isi folder webfonts
                if "/webfonts/" in file and not file.endswith("/"):
                    filename = os.path.basename(file)
                    if filename:
                        with zip_ref.open(file) as source, open(os.path.join(fonts_target, filename), "wb") as target:
                            shutil.copyfileobj(source, target)
                        count += 1
            print(f"   -> Installed: {count} Font Files di webfonts/")

        print("✅ Extract Selesai.")

    except zipfile.BadZipFile:
        print("❌ Error: File ZIP rusak (Corrupt). Coba jalankan script lagi.")
    except Exception as e:
        print(f"❌ Error Extract: {e}")
    finally:
        # 4. Bersih-bersih Akhir
        if os.path.exists(ZIP_NAME):
            os.remove(ZIP_NAME)
            print("✨ Selesai. File temporary dihapus.")

    print(f"----------------------------------------")
    print(f"🎉 SUKSES! OpenWrt-Music-Box sekarang 100% OFFLINE.")

if __name__ == "__main__":
    main()