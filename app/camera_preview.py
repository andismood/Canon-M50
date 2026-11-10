"""Worker thread untuk streaming live preview dari HDMI capture card via OpenCV."""

import threading
import time
from enum import Enum
from typing import Optional, Tuple

import cv2

from app import config
from app.config import CAMERA_INDEX


class PreviewState(str, Enum):
    STOPPED = "stopped"
    STREAMING = "streaming"
    RECOVERING = "recovering"


class CameraPreviewManager:
    """Mengelola thread pembacaan frame video HDMI secara asynchronous.

    Catatan arsitektur Canon EOS M50 + HDMI Capture Card (UGREEN V4L2):
    - Capture card HDMI (`/dev/video0`) adalah perangkat USB terpisah dari koneksi USB PTP kamera.
    - Jangan menutup (`cap.release()`) capture card saat shutter gphoto2 berlangsung ataupun
      saat layar kamera gelap sesaat, karena menutup `/dev/video0` akan memutus negosiasi
      HDMI sink (EDID/HPD) dan memicu loop re-handshake tanpa henti.
    - Pemulihan HDMI Live View setelah shutter dilakukan di sisi USB kamera (`gphoto2 --reset`),
      sementara stream V4L2 capture card tetap dibiarkan terbuka dan hanya dibuka ulang bila
      pembacaan frame level driver (`cap.read()`) benar-benar gagal.
    """

    def __init__(self, camera_index: int = CAMERA_INDEX):
        self.camera_index = camera_index
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._reopen_event = threading.Event()

        self._state = PreviewState.STOPPED
        self._latest_frame_bytes: Optional[bytes] = None
        self._latest_frame_seq: int = 0

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def state(self) -> PreviewState:
        return self._state

    def start(self) -> None:
        """Memulai streaming preview."""
        if self._running:
            return
        self.camera_index = config.CAMERA_INDEX
        self._running = True
        self._reopen_event.clear()
        self._state = PreviewState.RECOVERING
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Menghentikan streaming preview."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        self._state = PreviewState.STOPPED
        with self._lock:
            self._latest_frame_bytes = None

    def request_reopen(self) -> None:
        """Meminta worker untuk merilis dan membuka ulang capture card bila diperlukan."""
        self._reopen_event.set()

    def get_latest_frame(self) -> Tuple[int, Optional[bytes]]:
        """Mengambil nomor sequence dan bytes JPEG frame terbaru."""
        with self._lock:
            return self._latest_frame_seq, self._latest_frame_bytes

    def _open_capture(self) -> Optional[cv2.VideoCapture]:
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_V4L2)
        if not cap.isOpened():
            cap.release()
            cap = cv2.VideoCapture(self.camera_index)

        if not cap.isOpened():
            cap.release()
            return None

        # Atur format MJPEG untuk bandwidth USB optimal dan FPS tinggi
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.PREVIEW_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.PREVIEW_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS, 30)
        # Hindari latensi penumpukan buffer antrean frame di driver V4L2
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def _worker(self) -> None:
        cap: Optional[cv2.VideoCapture] = None
        consecutive_failures = 0
        try:
            while self._running:
                if self._reopen_event.is_set():
                    self._reopen_event.clear()
                    if cap is not None:
                        cap.release()
                        cap = None
                    time.sleep(0.5)

                if cap is None:
                    self._state = PreviewState.RECOVERING
                    cap = self._open_capture()
                    if cap is None:
                        time.sleep(1.0)
                        continue
                    consecutive_failures = 0

                ok, frame = cap.read()
                if not ok or frame is None:
                    consecutive_failures += 1
                    if consecutive_failures >= 10:
                        cap.release()
                        cap = None
                        consecutive_failures = 0
                        time.sleep(0.5)
                    else:
                        time.sleep(0.05)
                    continue

                consecutive_failures = 0
                self._state = PreviewState.STREAMING

                success, encoded = cv2.imencode(
                    ".jpg",
                    frame,
                    [cv2.IMWRITE_JPEG_QUALITY, config.PREVIEW_JPEG_QUALITY],
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
            self._state = PreviewState.STOPPED
