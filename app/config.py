"""Konfigurasi dan konstanta aplikasi."""

from pathlib import Path

# Daftar 7 pose pengambilan foto
POSES = [
    ("1", "Dengak", "Arahkan dagu sedikit ke atas"),
    ("2", "Nunduk", "Arahkan dagu sedikit ke bawah"),
    ("3", "Lurus", "Hadapkan wajah ke depan"),
    ("4", "Ke kiri 20 derajat", "Putar wajah ke kiri sekitar 20°"),
    ("5", "Ke kiri 30 derajat", "Putar wajah ke kiri sekitar 30°"),
    ("6", "Ke kanan 20 derajat", "Putar wajah ke kanan sekitar 20°"),
    ("7", "Ke kanan 30 derajat", "Putar wajah ke kanan sekitar 30°"),
]

# Konfigurasi HDMI Capture Card / OpenCV preview
CAMERA_INDEX = 0
PREVIEW_WIDTH = 1280
PREVIEW_HEIGHT = 720
PREVIEW_JPEG_QUALITY = 75

# Ukuran crop tetap (piksel foto asli)
CROP_SIZE = 640
CROP_JPEG_QUALITY = 100

# Lokasi penyimpanan
OUTPUT_DIR = Path("foto_mahasiswa")
TEMP_DIR = Path("temp_captures")

