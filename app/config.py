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

# Ukuran output crop (piksel) dan ukuran default kotak crop pada foto asli
CROP_SIZE = 640
CROP_JPEG_QUALITY = 100
MIN_CROP_SIZE = 200

# Deteksi wajah untuk menentukan kotak crop otomatis.
# Margin atas, bawah, kiri, dan kanan di sekeliling kotak wajah yang terdeteksi:
# - Nilai <= 5.0 dihitung sebagai rasio terhadap ukuran wajah (mis. 0.6 = 60% dari lebar/tinggi wajah).
# - Nilai > 5.0 dihitung sebagai piksel foto asli secara langsung (mis. 350 = 350 px).
FACE_MARGIN_TOP = 0.3
FACE_MARGIN_BOTTOM = 0.4
FACE_MARGIN_LEFT = 0.4
FACE_MARGIN_RIGHT = 0.4
FACE_DETECT_MAX_SIDE = 1000  # sisi terpanjang gambar (px) saat deteksi, demi kecepatan

# Gambar yang ditampilkan di tab hasil shutter diperkecil agar ringan dikirim ke UI.
# Proses crop tetap memakai foto asli resolusi penuh.
SHUTTER_DISPLAY_MAX_SIDE = 2400

# Lokasi penyimpanan
OUTPUT_DIR = Path("foto_mahasiswa")

