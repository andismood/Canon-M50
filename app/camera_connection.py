"""Koordinator koneksi kamera Canon EOS M50 (shutter USB gphoto2 + preview HDMI capture card)."""

import threading
import time
from typing import Optional, Tuple

from app.camera_preview import CameraPreviewManager
from app.shutter import capture_to_memory, reset_camera_usb

CAPTURE_RETRIES = 1
RETRY_DELAY = 1.0

_RETRYABLE_ERRORS = (
    "device busy",
    "i/o in progress",
    "could not claim",
    "ptp i/o error",
    "ptp timeout",
    "unspecified error",
)


class CameraConnectionManager:
    """Mengatur eksekusi shutter USB gphoto2 dan pemulihan Live View HDMI Canon EOS M50.

    Pada Canon EOS M50:
    - Sesi USB PTP `gphoto2 --capture-image-and-download` membuat kamera masuk ke mode PC/PTP
      sehingga output HDMI Live View dimatikan oleh firmware kamera.
    - `capture_to_memory()` otomatis memanggil `gphoto2 --reset` di blok `finally` begitu foto
      selesai diambil, sehingga kamera keluar dari mode PC/PTP dan kembali menyalakan HDMI Live View.
    - Stream OpenCV pada HDMI capture card (`/dev/video0`) tetap dibiarkan terbuka agar sink HDMI
      tidak kehilangan sinkronisasi.
    """

    def __init__(self, preview: CameraPreviewManager):
        self.preview = preview
        self._capture_lock = threading.Lock()

    @staticmethod
    def _is_retryable(msg: str) -> bool:
        lowered = (msg or "").lower()
        return any(key in lowered for key in _RETRYABLE_ERRORS)

    @staticmethod
    def _friendly_error(msg: str) -> str:
        if "could not claim" in (msg or "").lower():
            return (
                f"{msg}\nKamera sedang dikunci proses lain (mis. gvfs). Jalankan: "
                "killall gvfs-gphoto2-volume-monitor, atau unmount kamera di File Manager."
            )
        return msg

    def capture(self, timeout: int = 90) -> Tuple[Optional[bytes], str]:
        """Mengambil foto via USB gphoto2 lalu memulihkan HDMI Live View (panggil lewat asyncio.to_thread)."""
        with self._capture_lock:
            jpeg, msg = capture_to_memory(timeout)
            attempt = 0
            while jpeg is None and attempt < CAPTURE_RETRIES and self._is_retryable(msg):
                attempt += 1
                print(f"[CameraConnection] Kamera sibuk, reset USB & retry shutter ({attempt}): {msg}")
                reset_camera_usb()
                time.sleep(RETRY_DELAY)
                jpeg, msg = capture_to_memory(timeout)

            if jpeg is None:
                return None, self._friendly_error(msg)
            return jpeg, msg
