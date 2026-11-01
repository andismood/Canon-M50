"""Konfigurasi dan konstanta aplikasi yang disinkronkan dengan SQLite."""

from pathlib import Path
from typing import Any, Dict, List, Tuple
from app import db

# Default fallback values
POSES: List[Tuple[str, str, str]] = [
    ("H-20", "Ke kiri 30 derajat", "Putar wajah ke kiri sekitar 30°"),
    ("H-10", "Ke kiri 20 derajat", "Putar wajah ke kiri sekitar 20°"),
    ("0", "Lurus", "Hadapkan wajah ke depan"),
    ("H10", "Ke kanan 20 derajat", "Putar wajah ke kanan sekitar 20°"),
    ("H20", "Ke kanan 30 derajat", "Putar wajah ke kanan sekitar 30°"),
    ("V3", "Dengak", "Arahkan dagu sedikit ke atas"),
    ("V-3", "Nunduk", "Arahkan dagu sedikit ke bawah"),
]

CAMERA_INDEX: int = 0
PREVIEW_WIDTH: int = 1280
PREVIEW_HEIGHT: int = 720
PREVIEW_JPEG_QUALITY: int = 75

CROP_SIZE: int = 640
CROP_JPEG_QUALITY: int = 100
MIN_CROP_SIZE: int = 200

FACE_MARGIN_TOP: float = 0.3
FACE_MARGIN_BOTTOM: float = 0.4
FACE_MARGIN_LEFT: float = 0.4
FACE_MARGIN_RIGHT: float = 0.4
FACE_DETECT_MAX_SIDE: int = 1000

SHUTTER_DISPLAY_MAX_SIDE: int = 2400
OUTPUT_DIR: Path = Path("foto_mahasiswa")


def load_config_from_db() -> None:
    """Memuat nilai konfigurasi dan poses dari database SQLite ke variabel modul."""
    global POSES, CAMERA_INDEX, PREVIEW_WIDTH, PREVIEW_HEIGHT, PREVIEW_JPEG_QUALITY
    global CROP_SIZE, CROP_JPEG_QUALITY, MIN_CROP_SIZE
    global FACE_MARGIN_TOP, FACE_MARGIN_BOTTOM, FACE_MARGIN_LEFT, FACE_MARGIN_RIGHT
    global FACE_DETECT_MAX_SIDE, SHUTTER_DISPLAY_MAX_SIDE, OUTPUT_DIR

    try:
        loaded_configs = db.get_all_configs()
        if loaded_configs:
            CAMERA_INDEX = int(loaded_configs.get("CAMERA_INDEX", CAMERA_INDEX))
            PREVIEW_WIDTH = int(loaded_configs.get("PREVIEW_WIDTH", PREVIEW_WIDTH))
            PREVIEW_HEIGHT = int(loaded_configs.get("PREVIEW_HEIGHT", PREVIEW_HEIGHT))
            PREVIEW_JPEG_QUALITY = int(loaded_configs.get("PREVIEW_JPEG_QUALITY", PREVIEW_JPEG_QUALITY))

            CROP_SIZE = int(loaded_configs.get("CROP_SIZE", CROP_SIZE))
            CROP_JPEG_QUALITY = int(loaded_configs.get("CROP_JPEG_QUALITY", CROP_JPEG_QUALITY))
            MIN_CROP_SIZE = int(loaded_configs.get("MIN_CROP_SIZE", MIN_CROP_SIZE))

            FACE_MARGIN_TOP = float(loaded_configs.get("FACE_MARGIN_TOP", FACE_MARGIN_TOP))
            FACE_MARGIN_BOTTOM = float(loaded_configs.get("FACE_MARGIN_BOTTOM", FACE_MARGIN_BOTTOM))
            FACE_MARGIN_LEFT = float(loaded_configs.get("FACE_MARGIN_LEFT", FACE_MARGIN_LEFT))
            FACE_MARGIN_RIGHT = float(loaded_configs.get("FACE_MARGIN_RIGHT", FACE_MARGIN_RIGHT))
            FACE_DETECT_MAX_SIDE = int(loaded_configs.get("FACE_DETECT_MAX_SIDE", FACE_DETECT_MAX_SIDE))

            SHUTTER_DISPLAY_MAX_SIDE = int(loaded_configs.get("SHUTTER_DISPLAY_MAX_SIDE", SHUTTER_DISPLAY_MAX_SIDE))
            out_val = loaded_configs.get("OUTPUT_DIR", OUTPUT_DIR)
            OUTPUT_DIR = Path(out_val) if not isinstance(out_val, Path) else out_val
            # Buat folder jika belum ada
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        loaded_poses = db.get_all_poses()
        if loaded_poses:
            POSES.clear()
            POSES.extend(loaded_poses)
    except Exception as exc:
        print(f"[config] Gagal memuat konfigurasi dari database: {exc}")


# Inisialisasi konfigurasi dari database saat modul pertama kali di-import
load_config_from_db()
