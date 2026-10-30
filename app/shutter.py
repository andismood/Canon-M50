"""Integrasi shutter kamera menggunakan gphoto2."""

import shutil
import subprocess
import threading
from typing import List, Optional, Tuple

_camera_command_lock = threading.Lock()

_JPEG_SOI = b"\xff\xd8\xff"
_JPEG_EOI = b"\xff\xd9"


def is_gphoto2_installed() -> bool:
    """Mengecek apakah executable gphoto2 tersedia di sistem."""
    return shutil.which("gphoto2") is not None


def run_gphoto(args: List[str], timeout: int = 30, text: bool = True) -> subprocess.CompletedProcess:
    """Menjalankan perintah gphoto2 dengan thread lock dan timeout.

    Gunakan text=False bila stdout berisi data biner (mis. --stdout).
    """
    with _camera_command_lock:
        return subprocess.run(
            ["gphoto2"] + args,
            capture_output=True,
            text=text,
            timeout=timeout,
            check=False,
        )


def detect_camera(timeout: int = 15) -> Tuple[bool, str]:
    """Mengecek apakah kamera terhubung via USB dan terdeteksi oleh gphoto2."""
    if not is_gphoto2_installed():
        return False, "Perintah gphoto2 tidak ditemukan di sistem. Instal dengan 'sudo apt install gphoto2'."

    try:
        res = run_gphoto(["--auto-detect"], timeout=timeout)
        output = (res.stdout or "") + (res.stderr or "")
        if res.returncode == 0 and "usb:" in output.lower():
            return True, "Kamera terdeteksi."
        return False, output.strip() or "Kamera tidak terdeteksi via USB."
    except subprocess.TimeoutExpired:
        return False, "Pemeriksaan kamera timeout."
    except Exception as exc:
        return False, f"Gagal menjalankan gphoto2: {exc}"


def extract_jpeg(data: bytes) -> Optional[bytes]:
    """Mengambil bagian JPEG dari output gphoto2, membuang teks status di sekitarnya."""
    start = data.find(_JPEG_SOI)
    end = data.rfind(_JPEG_EOI)
    if start == -1 or end <= start:
        return None
    return data[start : end + len(_JPEG_EOI)]


def capture_to_memory(timeout: int = 90) -> Tuple[Optional[bytes], str]:
    """Mengambil foto asli dari kamera dan mengembalikannya sebagai bytes JPEG (tanpa file sementara)."""
    try:
        res = run_gphoto(
            ["--capture-image-and-download", "--stdout"],
            timeout=timeout,
            text=False,
        )
        jpeg = extract_jpeg(res.stdout or b"")
        if res.returncode != 0 or jpeg is None:
            detail = (res.stderr or b"").decode("utf-8", errors="replace").strip()
            return None, detail or "Data foto JPEG tidak diterima dari kamera."
        return jpeg, "Foto berhasil diambil."
    except subprocess.TimeoutExpired:
        return None, "Pengambilan foto melewati batas waktu (timeout). Periksa kamera."
    except Exception as exc:
        return None, f"Kesalahan saat mengambil foto: {exc}"
