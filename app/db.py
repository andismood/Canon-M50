"""Manajemen database SQLite untuk konfigurasi aplikasi dan daftar pose."""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Lokasi database SQLite di root folder proyek (sejajar dengan main.py)
DB_PATH = Path(__file__).resolve().parent.parent / "config.db"

# Nilai default awal sesuai config.py
DEFAULT_CONFIGS = {
    "CAMERA_INDEX": ("0", "int", "Index kamera capture card"),
    "PREVIEW_WIDTH": ("1280", "int", "Lebar frame live preview"),
    "PREVIEW_HEIGHT": ("720", "int", "Tinggi frame live preview"),
    "PREVIEW_JPEG_QUALITY": ("75", "int", "Kualitas JPEG live preview"),
    "CROP_SIZE": ("640", "int", "Ukuran output crop piksel"),
    "CROP_JPEG_QUALITY": ("100", "int", "Kualitas simpan JPEG crop"),
    "MIN_CROP_SIZE": ("200", "int", "Ukuran minimum bounding crop"),
    "FACE_MARGIN_TOP": ("0.3", "float", "Margin atas deteksi wajah"),
    "FACE_MARGIN_BOTTOM": ("0.4", "float", "Margin bawah deteksi wajah"),
    "FACE_MARGIN_LEFT": ("0.4", "float", "Margin kiri deteksi wajah"),
    "FACE_MARGIN_RIGHT": ("0.4", "float", "Margin kanan deteksi wajah"),
    "FACE_DETECT_MAX_SIDE": ("1000", "int", "Maksimal sisi foto saat deteksi wajah"),
    "SHUTTER_DISPLAY_MAX_SIDE": ("2400", "int", "Maksimal sisi tampilan di tab shutter"),
    "OUTPUT_DIR": ("foto_mahasiswa", "str", "Folder penyimpanan foto mahasiswa"),
}

DEFAULT_POSES = [
    ("1", "Dengak", "Arahkan dagu sedikit ke atas"),
    ("2", "Nunduk", "Arahkan dagu sedikit ke bawah"),
    ("3", "Lurus", "Hadapkan wajah ke depan"),
    ("4", "Ke kiri 20 derajat", "Putar wajah ke kiri sekitar 20°"),
    ("5", "Ke kiri 30 derajat", "Putar wajah ke kiri sekitar 30°"),
    ("6", "Ke kanan 20 derajat", "Putar wajah ke kanan sekitar 20°"),
    ("7", "Ke kanan 30 derajat", "Putar wajah ke kanan sekitar 30°"),
]


def get_connection() -> sqlite3.Connection:
    """Mendapatkan koneksi ke database SQLite."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(force_reset: bool = False) -> None:
    """Inisialisasi tabel SQLite dan isi default value jika belum ada."""
    with get_connection() as conn:
        cursor = conn.cursor()

        if force_reset:
            cursor.execute("DROP TABLE IF EXISTS app_config")
            cursor.execute("DROP TABLE IF EXISTS poses")

        # Buat tabel app_config
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS app_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                type TEXT NOT NULL,
                description TEXT
            )
            """
        )

        # Buat tabel poses
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS poses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL
            )
            """
        )

        # Cek apakah app_config kosong, jika ya isi default
        cursor.execute("SELECT COUNT(*) FROM app_config")
        if cursor.fetchone()[0] == 0:
            for key, (val, val_type, desc) in DEFAULT_CONFIGS.items():
                cursor.execute(
                    "INSERT INTO app_config (key, value, type, description) VALUES (?, ?, ?, ?)",
                    (key, val, val_type, desc),
                )

        # Cek apakah poses kosong, jika ya isi default
        cursor.execute("SELECT COUNT(*) FROM poses")
        if cursor.fetchone()[0] == 0:
            for code, title, desc in DEFAULT_POSES:
                cursor.execute(
                    "INSERT INTO poses (code, title, description) VALUES (?, ?, ?)",
                    (code, title, desc),
                )

        conn.commit()


# ==================== CRUD CONFIGS ====================

def get_all_configs() -> Dict[str, Any]:
    """Mengambil semua konfigurasi yang telah dikonversi ke tipe data aslinya."""
    init_db()
    configs: Dict[str, Any] = {}
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value, type FROM app_config")
        for row in cursor.fetchall():
            key = row["key"]
            val_str = row["value"]
            val_type = row["type"]

            try:
                if val_type == "int":
                    configs[key] = int(val_str)
                elif val_type == "float":
                    configs[key] = float(val_str)
                elif val_type == "path":
                    configs[key] = Path(val_str)
                else:
                    if key == "OUTPUT_DIR":
                        configs[key] = Path(val_str)
                    else:
                        configs[key] = val_str
            except (ValueError, TypeError):
                configs[key] = val_str
    return configs


def get_config_raw() -> List[Dict[str, Any]]:
    """Mengambil seluruh data config dalam bentuk list dictionary mentah untuk UI."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value, type, description FROM app_config")
        return [dict(row) for row in cursor.fetchall()]


def update_config(key: str, value: str) -> None:
    """Mengupdate satu nilai konfigurasi."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE app_config SET value = ? WHERE key = ?", (str(value), key))
        conn.commit()


def update_configs_bulk(configs: Dict[str, str]) -> None:
    """Mengupdate beberapa konfigurasi sekaligus."""
    with get_connection() as conn:
        cursor = conn.cursor()
        for key, val in configs.items():
            cursor.execute("UPDATE app_config SET value = ? WHERE key = ?", (str(val), key))
        conn.commit()


# ==================== CRUD POSES ====================

def get_all_poses() -> List[Tuple[str, str, str]]:
    """Mengambil daftar poses dalam format tuple (code, title, description)."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT code, title, description FROM poses ORDER BY id ASC")
        return [(str(row["code"]), str(row["title"]), str(row["description"])) for row in cursor.fetchall()]


def get_poses_raw() -> List[Dict[str, Any]]:
    """Mengambil daftar poses mentah beserta ID-nya untuk keperluan UI form CRUD."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, code, title, description FROM poses ORDER BY id ASC")
        return [dict(row) for row in cursor.fetchall()]


def add_pose(code: str, title: str, description: str) -> int:
    """Menambah pose baru ke tabel poses."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO poses (code, title, description) VALUES (?, ?, ?)",
            (code.strip(), title.strip(), description.strip()),
        )
        conn.commit()
        return cursor.lastrowid


def update_pose(pose_id: int, code: str, title: str, description: str) -> None:
    """Mengupdate data pose berdasarkan ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE poses SET code = ?, title = ?, description = ? WHERE id = ?",
            (code.strip(), title.strip(), description.strip(), pose_id),
        )
        conn.commit()


def delete_pose(pose_id: int) -> None:
    """Menghapus pose berdasarkan ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM poses WHERE id = ?", (pose_id,))
        conn.commit()


def reset_to_default() -> None:
    """Mengembalikan database ke konfigurasi default config.py."""
    init_db(force_reset=True)

