"""Utilitas citra: decode foto shutter dari memori, deteksi wajah, dan crop persegi."""

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

import cv2
import numpy as np

from app.config import (
    CROP_JPEG_QUALITY,
    CROP_SIZE,
    FACE_DETECT_MAX_SIDE,
    FACE_MARGIN_BOTTOM,
    FACE_MARGIN_LEFT,
    FACE_MARGIN_RIGHT,
    FACE_MARGIN_TOP,
    MIN_CROP_SIZE,
)

# (x, y, lebar, tinggi) dalam piksel foto asli
FaceBox = Tuple[int, int, int, int]

# (nama file cascade, balik horizontal, minNeighbors). Dicoba berurutan sampai ada wajah.
_DETECTION_ATTEMPTS = (
    ("haarcascade_frontalface_alt2.xml", False, 4),
    ("haarcascade_frontalface_default.xml", False, 5),
    ("haarcascade_profileface.xml", False, 4),
    ("haarcascade_profileface.xml", True, 4),
)

_cascade_cache: Dict[str, cv2.CascadeClassifier] = {}
_cascade_lock = threading.Lock()


@dataclass(frozen=True)
class CropRect:
    """Kotak crop persegi dalam piksel foto asli."""

    left: int
    top: int
    size: int
    face_centered: bool = False


def decode_image(data: bytes) -> np.ndarray:
    """Decode bytes JPEG/PNG menjadi gambar BGR."""
    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Data foto dari kamera tidak dapat dibaca sebagai gambar.")
    return image


def make_display_jpeg(image: np.ndarray, max_side: int, quality: int = 85) -> bytes:
    """Membuat JPEG versi ringan untuk ditampilkan di UI (rasio aspek tetap)."""
    h, w = image.shape[:2]
    scale = min(1.0, max_side / max(w, h))
    if scale < 1.0:
        image = cv2.resize(
            image,
            (max(1, int(round(w * scale))), max(1, int(round(h * scale)))),
            interpolation=cv2.INTER_AREA,
        )
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise ValueError("Gagal menyiapkan gambar tampilan.")
    return encoded.tobytes()


def _load_cascade(name: str) -> cv2.CascadeClassifier:
    with _cascade_lock:
        cascade = _cascade_cache.get(name)
        if cascade is None:
            cascade = cv2.CascadeClassifier(cv2.data.haarcascades + name)
            if cascade.empty():
                raise RuntimeError(f"Gagal memuat model deteksi wajah OpenCV: {name}")
            _cascade_cache[name] = cascade
        return cascade


def detect_face(image: np.ndarray) -> Optional[FaceBox]:
    """Mendeteksi wajah utama pada foto. Mengembalikan None bila tidak ada wajah."""
    h, w = image.shape[:2]
    scale = min(1.0, FACE_DETECT_MAX_SIDE / max(w, h))
    small = image
    if scale < 1.0:
        small = cv2.resize(
            image,
            (max(1, int(round(w * scale))), max(1, int(round(h * scale)))),
            interpolation=cv2.INTER_AREA,
        )

    gray = cv2.equalizeHist(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY))
    gh, gw = gray.shape[:2]
    min_face = max(40, int(min(gw, gh) * 0.08))

    for cascade_name, flip, min_neighbors in _DETECTION_ATTEMPTS:
        source = cv2.flip(gray, 1) if flip else gray
        cascade = _load_cascade(cascade_name)
        with _cascade_lock:
            # detectMultiScale pada satu instance tidak aman dipanggil paralel.
            faces, _, weights = cascade.detectMultiScale3(
                source,
                scaleFactor=1.1,
                minNeighbors=min_neighbors,
                minSize=(min_face, min_face),
                outputRejectLevels=True,
            )
        if len(faces) == 0:
            continue

        # Ambil kandidat dengan keyakinan tertinggi (bukan yang terbesar: kotak besar sering false positive)
        best = int(np.argmax(np.asarray(weights, dtype=np.float64).reshape(-1)))
        fx, fy, fw, fh = (int(v) for v in faces[best])
        if flip:
            fx = gw - fx - fw
        # Kembalikan ke koordinat foto asli
        x = max(0, int(round(fx / scale)))
        y = max(0, int(round(fy / scale)))
        bw = min(w - x, int(round(fw / scale)))
        bh = min(h - y, int(round(fh / scale)))
        return x, y, bw, bh

    return None


def _margin_to_px(margin: float, ref_length: int) -> float:
    """Konversi nilai margin ke piksel (nilai <= 5.0 dianggap rasio terhadap ukuran wajah)."""
    if abs(margin) <= 5.0:
        return float(margin) * float(ref_length)
    return float(margin)


def compute_crop_rect(
    img_w: int,
    img_h: int,
    face: Optional[FaceBox],
    fixed_size: Optional[int] = None,
    margin_top: float = FACE_MARGIN_TOP,
    margin_bottom: float = FACE_MARGIN_BOTTOM,
    margin_left: float = FACE_MARGIN_LEFT,
    margin_right: float = FACE_MARGIN_RIGHT,
) -> CropRect:
    """Menentukan kotak crop persegi berdasarkan deteksi wajah dan konstanta margin.

    - Tanpa wajah: kotak default CROP_SIZE (atau fixed_size) di tengah foto.
    - Dengan wajah: memperhitungkan margin atas, bawah, kiri, dan kanan di sekeliling
      kotak wajah. Bila fixed_size diberikan, ukuran kotak dipertahankan dan hanya
      posisinya yang disesuaikan agar wajah berada di tengah sesuai margin.
    """
    max_side = min(img_w, img_h)
    min_side = min(MIN_CROP_SIZE, max_side)

    if face is None:
        base_size = fixed_size if fixed_size is not None else CROP_SIZE
        size = max(min_side, min(int(base_size), max_side)) // 2 * 2
        return CropRect((img_w - size) // 2, (img_h - size) // 2, size, False)

    fx, fy, fw, fh = face
    pad_top = _margin_to_px(margin_top, fh)
    pad_bottom = _margin_to_px(margin_bottom, fh)
    pad_left = _margin_to_px(margin_left, fw)
    pad_right = _margin_to_px(margin_right, fw)

    # Titik pusat kotak dengan memperhitungkan margin kiri/kanan dan atas/bawah
    cx = (fx + fw / 2.0) + (pad_right - pad_left) / 2.0
    cy = (fy + fh / 2.0) + (pad_bottom - pad_top) / 2.0

    if fixed_size is not None:
        size = int(max(min_side, min(int(fixed_size), max_side))) // 2 * 2
    else:
        desired = max(fw + pad_left + pad_right, fh + pad_top + pad_bottom)
        largest_centered = 2.0 * min(cx, img_w - cx, cy, img_h - cy)
        size = min(desired, largest_centered, float(max_side))
        size = int(max(size, min_side)) // 2 * 2

    left = max(0, min(int(round(cx - size / 2.0)), img_w - size))
    top = max(0, min(int(round(cy - size / 2.0)), img_h - size))
    centered = abs((left + size / 2.0) - cx) <= 1.0 and abs((top + size / 2.0) - cy) <= 1.0
    return CropRect(left, top, size, centered)


def crop_square(
    image: np.ndarray,
    left: int,
    top: int,
    size: int,
    target_size: int = CROP_SIZE,
) -> np.ndarray:
    """Memotong area persegi dari foto asli lalu menskalakannya tepat ke target_size x target_size."""
    h, w = image.shape[:2]
    size = max(1, min(int(size), w, h))
    left = max(0, min(int(left), w - size))
    top = max(0, min(int(top), h - size))

    cropped = image[top : top + size, left : left + size]
    if size != target_size:
        interpolation = cv2.INTER_AREA if size > target_size else cv2.INTER_LANCZOS4
        cropped = cv2.resize(cropped, (target_size, target_size), interpolation=interpolation)
    return cropped


def save_jpeg(image: np.ndarray, output_path: Path, quality: int = CROP_JPEG_QUALITY) -> Path:
    """Menyimpan gambar sebagai JPEG ke output_path (folder dibuat bila perlu)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output_path), image, [cv2.IMWRITE_JPEG_QUALITY, quality]):
        raise IOError(f"Gagal menyimpan hasil crop ke {output_path}")
    return output_path
