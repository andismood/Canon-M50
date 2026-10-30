"""Integrasi shutter kamera menggunakan gphoto2."""

import shutil
import subprocess
import threading
from pathlib import Path
from typing import List, Tuple

_camera_command_lock = threading.Lock()


def is_gphoto2_installed() -> bool:
    """Mengecek apakah executable gphoto2 tersedia di sistem."""
    return shutil.which("gphoto2") is not None


def run_gphoto(args: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
    """Menjalankan perintah gphoto2 dengan thread lock dan timeout."""
    with _camera_command_lock:
        return subprocess.run(
            ["gphoto2"] + args,
            capture_output=True,
            text=True,
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


def capture_and_download(destination: Path, timeout: int = 90) -> Tuple[bool, str]:
    """Mengambil foto asli dari kamera dan mengunduhnya ke file tujuan sementara."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        res = run_gphoto(
            [
                "--capture-image-and-download",
                "--filename",
                str(destination),
                "--force-overwrite",
            ],
            timeout=timeout,
        )
        if res.returncode != 0 or not destination.exists() or destination.stat().st_size == 0:
            detail = (res.stderr or res.stdout or "File foto tidak terbentuk").strip()
            return False, detail
        return True, "Foto berhasil diambil."
    except subprocess.TimeoutExpired:
        return False, "Pengambilan foto melewati batas waktu (timeout). Periksa kamera."
    except Exception as exc:
        return False, f"Kesalahan saat mengambil foto: {exc}"

