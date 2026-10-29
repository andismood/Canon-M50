"""Utilitas pengolahan citra dan pemotongan (crop) foto 640x640."""

from pathlib import Path
from typing import Optional, Tuple

import cv2

from app.config import CROP_JPEG_QUALITY, CROP_SIZE


def get_image_size(image_path: Path) -> Tuple[int, int]:
    """Mengembalikan ukuran (width, height) dari gambar."""
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Gagal membaca file gambar: {image_path}")
    h, w = img.shape[:2]
    return w, h


def crop_image_640(
    input_path: Path,
    output_path: Path,
    left: int,
    top: int,
    crop_size: int = CROP_SIZE,
    target_size: int = CROP_SIZE,
) -> Path:
    """Memotong area crop_size x crop_size dari foto asli, resize presisi ke target_size x target_size jika berbeda, lalu simpan."""
    image = cv2.imread(str(input_path))
    if image is None:
        raise ValueError(f"Gagal membaca gambar untuk di-crop: {input_path}")

    h, w = image.shape[:2]

    # Batasi agar ukuran crop tidak melebihi dimensi foto
    actual_crop_size = max(50, min(int(crop_size), min(w, h)))

    # Batasi agar koordinat tidak melebihi batas gambar
    clamped_left = max(0, min(int(left), w - actual_crop_size))
    clamped_top = max(0, min(int(top), h - actual_crop_size))

    cropped = image[
        clamped_top : clamped_top + actual_crop_size,
        clamped_left : clamped_left + actual_crop_size,
    ]

    # Pertahankan presisi dimensi output tepat target_size x target_size (640x640 px)
    if cropped.shape[0] != target_size or cropped.shape[1] != target_size:
        if actual_crop_size > target_size:
            interp = cv2.INTER_AREA
        else:
            interp = cv2.INTER_LANCZOS4
        cropped = cv2.resize(
            cropped,
            (target_size, target_size),
            interpolation=interp,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    success = cv2.imwrite(
        str(output_path),
        cropped,
        [cv2.IMWRITE_JPEG_QUALITY, CROP_JPEG_QUALITY],
    )

    if not success:
        raise IOError(f"Gagal menyimpan hasil crop ke {output_path}")

    return output_path

