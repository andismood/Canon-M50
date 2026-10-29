"""Worker thread untuk streaming live preview dari HDMI capture card via OpenCV."""

import threading
import time
from typing import Optional, Tuple

import cv2

from app.config import (
    CAMERA_INDEX,
    PREVIEW_HEIGHT,
    PREVIEW_JPEG_QUALITY,
    PREVIEW_WIDTH,
)


class CameraPreviewManager:
    """Mengelola thread pembacaan frame video HDMI secara asynchronous."""

    def __init__(self, camera_index: int = CAMERA_INDEX):
        self.camera_index = camera_index
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._reopen_event = threading.Event()

        self._latest_frame_bytes: Optional[bytes] = None
        self._latest_frame_seq: int = 0

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Memulai streaming preview."""
        if self._running:
            return
        self._running = True
        self._reopen_event.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Menghentikan streaming preview."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        with self._lock:
            self._latest_frame_bytes = None

    def request_reopen(self) -> None:
        """Meminta worker untuk merilis dan membuka ulang capture card (mis. setelah shutter)."""
        self._reopen_event.set()

    def get_latest_frame(self) -> Tuple[int, Optional[bytes]]:
        """Mengambil nomor sequence dan bytes JPEG frame terbaru."""
        with self._lock:
            return self._latest_frame_seq, self._latest_frame_bytes

    def _worker(self) -> None:
        cap: Optional[cv2.VideoCapture] = None
        try:
            while self._running:
                # Buka ulang stream jika diminta setelah shutter
                if self._reopen_event.is_set():
                    self._reopen_event.clear()
                    if cap is not None:
                        cap.release()
                        cap = None
                    time.sleep(1.0)

                # Buka capture card jika belum aktif
                if cap is None:
                    cap = cv2.VideoCapture(self.camera_index, cv2.CAP_V4L2)
                    if not cap.isOpened():
                        # Coba fallback tanpa V4L2 flag jika diperlukan
                        cap = cv2.VideoCapture(self.camera_index)

                    if not cap.isOpened():
                        cap.release()
                        cap = None
                        time.sleep(1.0)
                        continue

                    # Atur format MJPEG untuk bandwidth USB optimal dan FPS tinggi
                    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, PREVIEW_WIDTH)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, PREVIEW_HEIGHT)
                    cap.set(cv2.CAP_PROP_FPS, 30)
                    # Hindari latensi penumpukan buffer antrean frame di driver V4L2
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                ok, frame = cap.read()
                if not ok or frame is None:
                    cap.release()
                    cap = None
                    time.sleep(0.5)
                    continue

                success, encoded = cv2.imencode(
                    ".jpg",
                    frame,
                    [cv2.IMWRITE_JPEG_QUALITY, PREVIEW_JPEG_QUALITY],
                )

                if success:
                    with self._lock:
                        self._latest_frame_bytes = encoded.tobytes()
                        self._latest_frame_seq += 1

        except Exception as exc:
            print(f"[CameraPreviewManager] Error preview_worker: {exc}")
        finally:
            if cap is not None:
                cap.release()

