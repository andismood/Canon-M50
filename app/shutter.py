"""Integrasi shutter kamera menggunakan gphoto2."""

import os
import shutil
import subprocess
import threading
from typing import Dict, List, Optional, Tuple

_camera_command_lock = threading.Lock()

_JPEG_SOI = b"\xff\xd8\xff"
_JPEG_EOI = b"\xff\xd9"


def _get_gphoto_env() -> Dict[str, str]:
    """Menyiapkan environment bersih untuk subprocess gphoto2.

    Saat dijalankan dari executable PyInstaller (folder dist), PyInstaller mengubah
    LD_LIBRARY_PATH ke folder _internal yang berisi library bundel (seperti libgphoto2
    bawaan wheel Python) tanpa driver port USB sistem, sehingga `/usr/bin/gphoto2`
    gagal mendeteksi port USB (Devices found: -2).
    """
    env = os.environ.copy()
    env["PATH"] = "/usr/local/bin:/usr/bin:/bin:" + env.get("PATH", "")

    # Pulihkan LD_LIBRARY_PATH asli sebelum diubah oleh bootloader PyInstaller
    orig_ld = env.get("LD_LIBRARY_PATH_ORIG")
    if orig_ld is not None:
        if orig_ld:
            env["LD_LIBRARY_PATH"] = orig_ld
        else:
            env.pop("LD_LIBRARY_PATH", None)
    else:
        env.pop("LD_LIBRARY_PATH", None)

    env.pop("CAMLIBS", None)
    env.pop("IOLIBS", None)
    return env


def get_gphoto2_path() -> Optional[str]:
    """Mencari path executable gphoto2 di sistem."""
    env = _get_gphoto_env()
    return shutil.which("gphoto2", path=env.get("PATH"))


def is_gphoto2_installed() -> bool:
    """Mengecek apakah executable gphoto2 tersedia di sistem."""
    return get_gphoto2_path() is not None


def run_gphoto(args: List[str], timeout: int = 30, text: bool = True) -> subprocess.CompletedProcess:
    """Menjalankan perintah gphoto2 dengan thread lock, timeout, dan environment bersih.

    Gunakan text=False bila stdout berisi data biner (mis. --stdout).
    """
    env = _get_gphoto_env()
    gphoto_path = shutil.which("gphoto2", path=env.get("PATH")) or "gphoto2"
    with _camera_command_lock:
        return subprocess.run(
            [gphoto_path] + args,
            capture_output=True,
            text=text,
            timeout=timeout,
            check=False,
            env=env,
        )


def detect_camera(timeout: int = 15) -> Tuple[bool, str]:
    """
    Mendeteksi kamera DSLR/Mirrorless melalui gphoto2 CLI.
    """
    env = _get_gphoto_env()
    gphoto_path = shutil.which("gphoto2", path=env.get("PATH"))

    if not gphoto_path:
        return (
            False,
            "Perintah gphoto2 tidak ditemukan.\n"
            "Silakan install dengan:\n"
            "sudo apt install gphoto2"
        )

    try:
        with _camera_command_lock:
            res = subprocess.run(
                [gphoto_path, "--auto-detect"],
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )

        output = (
            (res.stdout or "")
            + "\n"
            + (res.stderr or "")
        ).strip()

        print("GPHOTO2 PATH:", gphoto_path)
        print("GPHOTO2 RETURN CODE:", res.returncode)
        print("GPHOTO2 OUTPUT:", output)

        if res.returncode != 0:
            return False, output or (
                "gphoto2 gagal mendeteksi kamera."
            )

        # Periksa tabel hasil auto-detect
        lines = output.splitlines()

        for line in lines:
            normalized = line.strip().lower()

            if (
                "usb:" in normalized
                or "ptpip:" in normalized
            ):
                return True, "Kamera terdeteksi."

        return False, (
            output or "Kamera tidak terdeteksi via USB."
        )

    except subprocess.TimeoutExpired:
        return False, "Pemeriksaan kamera timeout."

    except Exception as exc:
        return False, f"Gagal menjalankan gphoto2: {exc}"
    
# def detect_camera(timeout: int = 15) -> Tuple[bool, str]:
#     """Mengecek apakah kamera terhubung via USB dan terdeteksi oleh gphoto2."""
#     if not is_gphoto2_installed():
#         return False, "Perintah gphoto2 tidak ditemukan di sistem. Instal dengan 'sudo apt install gphoto2'."

#     try:
#         res = run_gphoto(["--auto-detect"], timeout=timeout)
#         output = (res.stdout or "") + (res.stderr or "")
#         if res.returncode == 0 and "usb:" in output.lower():
#             return True, "Kamera terdeteksi."
#         return False, output.strip() or "Kamera tidak terdeteksi via USB."
#     except subprocess.TimeoutExpired:
#         return False, "Pemeriksaan kamera timeout."
#     except Exception as exc:
#         return False, f"Gagal menjalankan gphoto2: {exc}"


def extract_jpeg(data: bytes) -> Optional[bytes]:
    """Mengambil bagian JPEG dari output gphoto2, membuang teks status di sekitarnya."""
    start = data.find(_JPEG_SOI)
    end = data.rfind(_JPEG_EOI)
    if start == -1 or end <= start:
        return None
    return data[start : end + len(_JPEG_EOI)]


def reset_camera_usb(timeout: int = 10) -> None:
    """Me-reset koneksi USB kamera (gphoto2 --reset) agar Canon EOS M50 keluar
    dari mode PC/PTP dan mengaktifkan kembali output Live View HDMI.
    """
    try:
        run_gphoto(["--reset"], timeout=timeout, text=True)
    except Exception as exc:
        print(f"[shutter] Gagal reset USB kamera: {exc}")


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
    finally:
        # Wajib reset sesi USB PTP setelah shutter agar HDMI Live View Canon M50 kembali menyala
        reset_camera_usb()
