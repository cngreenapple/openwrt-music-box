import sqlite3
import os
import threading
import time
import logging
from mutagen import File as MutagenFile

logger = logging.getLogger('OpenWrtMusicBox.Library')

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music.db")
AUDIO_EXTS = ('.mp3', '.flac', '.wav', '.m4a', '.ogg', '.opus', '.wma', '.aac')

class LibraryManager:
    def __init__(self):
        self.scanning = False
        self.total_files = 0
        self.scanned_files = 0
        self.status_msg = "Idle"
        self.init_db()

    def init_db(self):
        """Bikin tabel database kalau belum ada"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("PRAGMA journal_mode=WAL")
        c.execute('''
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE,
                filename TEXT,
                title TEXT,
                artist TEXT,
                album TEXT,
                genre TEXT,
                year TEXT,
                duration INTEGER,
                added_at REAL
            )
        ''')
        conn.commit()
        conn.close()

    def get_metadata(self, filepath):
        """Baca ID3 Tags dari file"""
        meta = {
            'title': os.path.basename(filepath),
            'artist': 'Unknown Artist',
            'album': 'Unknown Album',
            'genre': 'Unknown',
            'year': '',
            'duration': 0
        }
        try:
            audio = MutagenFile(filepath, easy=True)
            if audio:
                # EasyID3 mapping
                meta['title'] = audio.get('title', [meta['title']])[0]
                meta['artist'] = audio.get('artist', ['Unknown Artist'])[0]
                meta['album'] = audio.get('album', ['Unknown Album'])[0]
                meta['genre'] = audio.get('genre', ['Unknown'])[0]
                meta['year'] = audio.get('date', [''])[0].split('-')[0]
                meta['duration'] = int(audio.info.length)
        except:
            pass
        return meta

    def scan_directory(self, root_path):
        """Logic Scan berjalan di Background Thread"""
        if self.scanning: return
        self.scanning = True
        self.status_msg = "Scanning..."

        def worker():
            try:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                
                # 1. Hitung total file dulu biar ada progress bar
                file_list = []
                for root, dirs, files in os.walk(root_path):
                    for f in files:
                        if f.lower().endswith(AUDIO_EXTS):
                            file_list.append(os.path.join(root, f))
                
                self.total_files = len(file_list)
                self.scanned_files = 0

                # 2. Proses Insert/Update Database
                for filepath in file_list:
                    try:
                        # Cek dulu apa file sudah ada di DB?
                        c.execute("SELECT id FROM tracks WHERE path = ?", (filepath,))
                        if c.fetchone() is None:
                            # Kalau belum ada, baca metadata & insert
                            m = self.get_metadata(filepath)
                            c.execute('''
                                INSERT INTO tracks (path, filename, title, artist, album, genre, year, duration, added_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (filepath, os.path.basename(filepath), m['title'], m['artist'],
                                  m['album'], m['genre'], m['year'], m['duration'], time.time()))
                            conn.commit()
                    except Exception as e:
                        logger.error(f"Error scan file {filepath}: {e}")
                        pass
                    
                    self.scanned_files += 1

                conn.close()
                self.status_msg = f"Completed. {self.total_files} Tracks."
            
            except Exception as e:
                self.status_msg = f"Error: {e}"
            
            finally:
                # PASTIKAN status scanning kembali normal walaupun ada error
                self.scanning = False

        threading.Thread(target=worker, daemon=True).start()

    def get_all_tracks(self, sort_by='title'):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row # Biar return dict, bukan tuple
        c = conn.cursor()
        # Whitelist sort options to prevent SQL injection
        order_map = {
            'title': "title ASC",
            'artist': "artist ASC, album ASC, title ASC",
            'album': "album ASC, artist ASC",
            'newest': "added_at DESC"
        }
        order_sql = order_map.get(sort_by, "title ASC")
        c.execute(f"SELECT * FROM tracks ORDER BY {order_sql}")
        rows = [dict(row) for row in c.fetchall()]
        conn.close()
        return rows

    def search_tracks(self, query):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        sql = """
            SELECT * FROM tracks
            WHERE title LIKE ? OR artist LIKE ? OR album LIKE ?
            LIMIT 50
        """
        arg = f"%{query}%"
        c.execute(sql, (arg, arg, arg))
        rows = [dict(row) for row in c.fetchall()]
        conn.close()
        return rows

    def get_scan_status(self):
        return {
            "scanning": self.scanning,
            "progress": int((self.scanned_files / self.total_files) * 100) if self.total_files > 0 else 0,
            "message": self.status_msg,
            "total": self.total_files
        }

# Singleton Instance
lib_mgr = LibraryManager()