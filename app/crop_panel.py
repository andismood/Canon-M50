"""Panel crop hasil shutter (isi tab 'Hasil Shutter & Crop').

Foto dari kamera langsung dipegang di memori (tanpa file sementara). Kotak crop persegi
bawaan 640 px otomatis menyesuaikan area wajah yang terdeteksi dengan wajah di tengah kotak,
dan tetap bisa digeser, di-resize (rasio 1:1), serta di-zoom secara manual.
"""

import asyncio
from pathlib import Path
from typing import Callable, Optional

import flet as ft
import numpy as np

from app.config import CROP_SIZE, MIN_CROP_SIZE, SHUTTER_DISPLAY_MAX_SIDE
from app.image_utils import (
    CropRect,
    FaceBox,
    compute_crop_rect,
    crop_square,
    decode_image,
    detect_face,
    make_display_jpeg,
    save_jpeg,
)


class ShutterCropPanel:
    """Menampilkan foto hasil shutter beserta kotak crop yang dapat disesuaikan."""

    VIEWPORT_W = 760
    VIEWPORT_H = 390
    ZOOM_MIN = 0.5
    ZOOM_MAX = 4.0
    ZOOM_STEP = 0.25

    def __init__(
        self,
        page: ft.Page,
        on_saved: Callable[[Path], None],
        on_cancel: Callable[[], None],
        on_auto_saved: Optional[Callable[[Path], None]] = None,
    ):
        self.page = page
        self.on_saved = on_saved
        self.on_cancel = on_cancel
        self.on_auto_saved = on_auto_saved

        # State foto aktif (hanya di memori)
        self._image: Optional[np.ndarray] = None
        self._destination: Optional[Path] = None
        self._face: Optional[FaceBox] = None
        self._user_resized = False
        self.orig_w = 0
        self.orig_h = 0

        # Kotak crop (koordinat & ukuran dalam piksel foto asli)
        self.crop_x = 0.0
        self.crop_y = 0.0
        self.crop_size = float(CROP_SIZE)
        self.min_crop_size = float(MIN_CROP_SIZE)
        self.max_crop_size = float(CROP_SIZE)

        self.base_fit_scale = 1.0
        self.zoom_factor = 1.0

        self._build_controls()

    # ------------------------------------------------------------------ UI

    def _build_controls(self) -> None:
        self.image_control = ft.Image(
            src=b"",
            fit=ft.BoxFit.FILL,
            gapless_playback=False,
        )

        # Kotak hasil deteksi wajah (oranye), hanya sebagai penanda
        self.face_box = ft.Container(
            border=ft.Border.all(2, "#F59E0B"),
            border_radius=2,
            visible=False,
        )

        self.crop_badge_text = ft.Text(
            f"{CROP_SIZE}x{CROP_SIZE}",
            size=10,
            color="#FFFFFF",
            weight=ft.FontWeight.BOLD,
        )
        self.crop_badge = ft.Container(
            bgcolor="#E61677E8",
            padding=ft.Padding.symmetric(horizontal=5, vertical=2),
            border_radius=3,
            content=self.crop_badge_text,
        )

        # Handle di sudut kanan-bawah untuk me-resize kotak (rasio 1:1)
        self.resize_handle = ft.GestureDetector(
            content=ft.Container(
                width=24,
                height=24,
                bgcolor="#1677E8",
                border_radius=ft.BorderRadius(top_left=12, top_right=0, bottom_left=0, bottom_right=4),
                alignment=ft.Alignment.BOTTOM_RIGHT,
                padding=ft.Padding.only(right=2, bottom=2),
                content=ft.Icon(ft.Icons.OPEN_IN_FULL, size=13, color="#FFFFFF"),
                tooltip="Tarik sudut ini untuk memperbesar/memperkecil kotak (1:1)",
            ),
            on_pan_update=self._handle_resize_handle_pan,
        )

        self.crop_box = ft.Container(
            border=ft.Border.all(2, "#1677E8"),
            bgcolor="#331677E8",
            border_radius=4,
            content=ft.Stack(
                controls=[
                    ft.Container(alignment=ft.Alignment.TOP_LEFT, content=self.crop_badge),
                    ft.Container(alignment=ft.Alignment.BOTTOM_RIGHT, content=self.resize_handle),
                ],
                expand=True,
            ),
        )

        self.stack = ft.Stack(controls=[self.image_control, self.face_box, self.crop_box])

        self.gesture_detector = ft.GestureDetector(
            content=self.stack,
            on_pan_update=self._handle_pan_update,
            on_tap_up=self._handle_tap_up,
        )

        self.viewport_container = ft.Container(
            width=self.VIEWPORT_W,
            height=self.VIEWPORT_H,
            bgcolor="#1E293B",
            border_radius=8,
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[self.gesture_detector],
                        scroll=ft.ScrollMode.AUTO,
                        alignment=ft.MainAxisAlignment.CENTER,
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        self.title_text = ft.Text("", size=14, weight=ft.FontWeight.BOLD, color="#17365D")
        self.face_status = ft.Text(
            "",
            size=12,
            weight=ft.FontWeight.W_600,
            color="#475569",
            expand=True,
            text_align=ft.TextAlign.RIGHT,
        )
        self.status_text = ft.Text("", size=11, color="#475569")
        self.zoom_text = ft.Text("Zoom: 100%", size=12, weight=ft.FontWeight.W_600, color="#334155")
        self.crop_size_text = ft.Text(
            f"Kotak: {CROP_SIZE}px", size=12, weight=ft.FontWeight.W_600, color="#1E293B"
        )

        self.detect_button = ft.OutlinedButton(
            "Deteksi Wajah",
            icon=ft.Icons.FACE,
            tooltip="Deteksi ulang wajah lalu sesuaikan kotak (wajah di tengah)",
            on_click=self._on_detect_clicked,
        )
        self.cancel_button = ft.OutlinedButton(
            "Batal / Ulangi",
            icon=ft.Icons.CLOSE,
            on_click=self._on_cancel_clicked,
        )
        self.crop_button = ft.FilledButton(
            "Crop & Simpan Foto",
            icon=ft.Icons.CHECK,
            style=ft.ButtonStyle(bgcolor="#16803C", color="#FFFFFF"),
            on_click=self._on_crop_clicked,
        )

        toolbar = ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.ZOOM_OUT,
                    tooltip="Perkecil Tampilan Foto",
                    on_click=lambda _: self._change_zoom(-self.ZOOM_STEP),
                ),
                self.zoom_text,
                ft.IconButton(
                    icon=ft.Icons.ZOOM_IN,
                    tooltip="Perbesar Tampilan Foto",
                    on_click=lambda _: self._change_zoom(+self.ZOOM_STEP),
                ),
                ft.IconButton(
                    icon=ft.Icons.FIT_SCREEN,
                    tooltip="Reset Zoom",
                    on_click=lambda _: self._reset_zoom(),
                ),
                ft.Container(width=8),
                ft.IconButton(
                    icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
                    tooltip="Perkecil Ukuran Kotak (-40px)",
                    on_click=lambda _: self._resize_crop(-40),
                ),
                self.crop_size_text,
                ft.IconButton(
                    icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                    tooltip="Perbesar Ukuran Kotak (+40px)",
                    on_click=lambda _: self._resize_crop(+40),
                ),
                ft.OutlinedButton(
                    "Reset 640px",
                    icon=ft.Icons.ASPECT_RATIO,
                    tooltip="Kembalikan ukuran kotak ke standar 640x640",
                    on_click=lambda _: self._reset_crop_size(),
                ),
                ft.Container(width=8),
                ft.IconButton(
                    icon=ft.Icons.ARROW_LEFT,
                    tooltip="Geser Kiri (25px)",
                    on_click=lambda _: self._nudge(-25, 0),
                ),
                ft.IconButton(
                    icon=ft.Icons.ARROW_UPWARD,
                    tooltip="Geser Atas (25px)",
                    on_click=lambda _: self._nudge(0, -25),
                ),
                ft.IconButton(
                    icon=ft.Icons.ARROW_DOWNWARD,
                    tooltip="Geser Bawah (25px)",
                    on_click=lambda _: self._nudge(0, 25),
                ),
                ft.IconButton(
                    icon=ft.Icons.ARROW_RIGHT,
                    tooltip="Geser Kanan (25px)",
                    on_click=lambda _: self._nudge(25, 0),
                ),
                ft.IconButton(
                    icon=ft.Icons.CENTER_FOCUS_STRONG,
                    tooltip="Pusatkan Kotak di Tengah Foto",
                    on_click=lambda _: self._center_crop(),
                ),
                self.detect_button,
            ],
            wrap=True,
            spacing=2,
            run_spacing=2,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.editor_view = ft.Column(
            visible=False,
            spacing=8,
            tight=True,
            controls=[
                ft.Row(
                    controls=[self.title_text, self.face_status],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                toolbar,
                self.viewport_container,
                ft.Text(
                    "Seret kotak untuk memindahkan, tarik sudut kanan-bawah untuk resize.",
                    size=11,
                    color="#64748B",
                ),
                self.status_text,
                ft.Row(
                    controls=[self.cancel_button, self.crop_button],
                    alignment=ft.MainAxisAlignment.END,
                    spacing=10,
                ),
            ],
        )

        self.empty_view = ft.Container(
            width=self.VIEWPORT_W,
            height=self.VIEWPORT_H,
            bgcolor="#E8EEF7",
            border_radius=9,
            padding=5,
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.CROP_ORIGINAL, size=54, color="#6482A8"),
                    ft.Text(
                        "Belum ada hasil shutter",
                        size=15,
                        weight=ft.FontWeight.W_600,
                        color="#334155",
                    ),
                    ft.Text(
                        "Klik 'Ambil foto' pada salah satu pose. Hasilnya muncul di tab ini.",
                        size=12,
                        color="#64748B",
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=6,
            ),
        )

        self.control = ft.Column(
            visible=False,
            tight=True,
            controls=[self.empty_view, self.editor_view],
        )

    # ------------------------------------------------------- Public API

    @property
    def has_photo(self) -> bool:
        return self._image is not None

    async def load_photo(self, jpeg_bytes: bytes, pose_label: str, destination: Path) -> bool:
        """Memuat foto shutter dari memori, mendeteksi wajah, lalu menyesuaikan kotak crop.

        Jika wajah terdeteksi, foto langsung di-crop otomatis ke destination dan
        on_auto_saved dipanggil agar tampil di thumbnail pose sebagai referensi.

        Returns:
            True bila wajah terdeteksi dan otomatis disimpan, False bila tidak.

        Raises:
            ValueError: bila foto tidak terbaca atau resolusinya lebih kecil dari CROP_SIZE.
        """
        image = await asyncio.to_thread(decode_image, jpeg_bytes)
        height, width = image.shape[:2]
        if width < CROP_SIZE or height < CROP_SIZE:
            raise ValueError(
                f"Resolusi foto ({width}x{height}) lebih kecil dari ukuran crop wajib "
                f"({CROP_SIZE}x{CROP_SIZE} px)."
            )

        display_jpeg = await asyncio.to_thread(make_display_jpeg, image, SHUTTER_DISPLAY_MAX_SIDE)
        face = await asyncio.to_thread(detect_face, image)

        self._image = image
        self._destination = destination
        self._face = face
        self._user_resized = False
        self.orig_w, self.orig_h = width, height
        self.max_crop_size = float(min(width, height))
        self.min_crop_size = float(min(MIN_CROP_SIZE, self.max_crop_size))
        self.base_fit_scale = min(self.VIEWPORT_W / width, self.VIEWPORT_H / height, 1.0)
        self.zoom_factor = 1.0

        rect = compute_crop_rect(width, height, face)
        self._apply_rect(rect)

        auto_saved = False
        if face is not None:
            await asyncio.to_thread(
                self._write_crop, image, destination, rect.left, rect.top, rect.size
            )
            auto_saved = True

        self._set_face_status(face, rect, auto_saved=auto_saved)

        self.image_control.src = display_jpeg
        self.title_text.value = f"Pose {pose_label}"
        self.status_text.color = "#475569"
        self._set_busy(False, update=False)
        self.empty_view.visible = False
        self.editor_view.visible = True
        self._update_geometry()
        self.page.update(self.control)

        if auto_saved and self.on_auto_saved is not None:
            self.on_auto_saved(destination)
        return auto_saved

    def clear(self) -> None:
        """Membuang foto dari memori dan kembali ke tampilan kosong."""
        self._image = None
        self._destination = None
        self._face = None
        self._user_resized = False
        self.face_box.visible = False
        self.editor_view.visible = False
        self.empty_view.visible = True
        self.page.update(self.control)

    # ----------------------------------------------------- Geometry

    @property
    def current_scale(self) -> float:
        """Skala antara piksel layar dan piksel foto asli."""
        return self.base_fit_scale * self.zoom_factor

    def _apply_rect(self, rect: CropRect) -> None:
        self.crop_size = float(rect.size)
        self.crop_x = float(rect.left)
        self.crop_y = float(rect.top)

    def _clamp_crop(self) -> None:
        self.crop_size = max(self.min_crop_size, min(self.crop_size, self.max_crop_size))
        self.crop_x = max(0.0, min(self.crop_x, float(self.orig_w) - self.crop_size))
        self.crop_y = max(0.0, min(self.crop_y, float(self.orig_h) - self.crop_size))

    def _update_geometry(self) -> None:
        self._clamp_crop()
        scale = self.current_scale

        disp_w = max(10, int(round(self.orig_w * scale)))
        disp_h = max(10, int(round(self.orig_h * scale)))
        disp_box = max(10, int(round(self.crop_size * scale)))

        self.image_control.width = disp_w
        self.image_control.height = disp_h
        self.stack.width = disp_w
        self.stack.height = disp_h

        self.crop_box.left = int(round(self.crop_x * scale))
        self.crop_box.top = int(round(self.crop_y * scale))
        self.crop_box.width = disp_box
        self.crop_box.height = disp_box

        if self._face is not None:
            fx, fy, fw, fh = self._face
            self.face_box.left = int(round(fx * scale))
            self.face_box.top = int(round(fy * scale))
            self.face_box.width = max(4, int(round(fw * scale)))
            self.face_box.height = max(4, int(round(fh * scale)))
            self.face_box.visible = True
        else:
            self.face_box.visible = False

        side = int(round(self.crop_size))
        self.crop_badge_text.value = f"{side}x{side}"
        self.crop_size_text.value = f"Kotak: {side}px"
        self.zoom_text.value = f"Zoom: {int(round(self.zoom_factor * 100))}%"
        self.status_text.value = (
            f"Foto {self.orig_w}x{self.orig_h} px | Kotak {side}x{side} di "
            f"({int(round(self.crop_x))}, {int(round(self.crop_y))}) → {CROP_SIZE}x{CROP_SIZE} px"
        )

    def _refresh(self) -> None:
        self._update_geometry()
        self.page.update(self.stack, self.zoom_text, self.crop_size_text, self.status_text)

    def _set_face_status(
        self, face: Optional[FaceBox], rect: CropRect, auto_saved: bool = False
    ) -> None:
        if face is None:
            self.face_status.value = (
                f"Wajah tidak terdeteksi — kotak default {rect.size}px di tengah foto. Atur manual."
            )
            self.face_status.color = "#B45309"
        elif auto_saved:
            self.face_status.value = (
                f"Wajah terdeteksi — otomatis di-crop & disimpan ke thumbnail ({rect.size}px)."
            )
            self.face_status.color = "#16803C"
        elif rect.face_centered:
            self.face_status.value = f"Wajah terdeteksi — kotak {rect.size}px, wajah di tengah."
            self.face_status.color = "#16803C"
        else:
            self.face_status.value = (
                f"Wajah terdeteksi dekat tepi foto — kotak {rect.size}px, wajah tidak bisa tepat di tengah."
            )
            self.face_status.color = "#B45309"

    def _set_busy(self, busy: bool, update: bool = True) -> None:
        self.crop_button.disabled = busy
        self.cancel_button.disabled = busy
        self.detect_button.disabled = busy
        if update:
            self.page.update(self.crop_button, self.cancel_button, self.detect_button)

    # ------------------------------------------------------ Gestures

    @staticmethod
    def _event_delta(e) -> tuple:
        delta = getattr(e, "local_delta", None) or getattr(e, "global_delta", None)
        if delta is None:
            return 0.0, 0.0
        return float(delta.x), float(delta.y)

    def _handle_pan_update(self, e: ft.DragUpdateEvent) -> None:
        if self._image is None:
            return
        dx, dy = self._event_delta(e)
        scale = self.current_scale
        if scale > 0:
            self.crop_x += dx / scale
            self.crop_y += dy / scale
            self._refresh()

    def _handle_resize_handle_pan(self, e: ft.DragUpdateEvent) -> None:
        if self._image is None:
            return
        dx, dy = self._event_delta(e)
        scale = self.current_scale
        if scale > 0:
            # Rata-rata dx & dy menjaga kotak tetap persegi
            delta = ((dx + dy) / 2.0) / scale
            new_size = max(self.min_crop_size, min(self.max_crop_size, self.crop_size + delta))
            if abs(new_size - self.crop_size) > 0.5:
                self.crop_size = new_size
                self._user_resized = True
                self._refresh()

    def _handle_tap_up(self, e: ft.TapEvent) -> None:
        scale = self.current_scale
        if self._image is None or scale <= 0 or not getattr(e, "local_position", None):
            return
        self.crop_x = e.local_position.x / scale - self.crop_size / 2.0
        self.crop_y = e.local_position.y / scale - self.crop_size / 2.0
        self._refresh()

    # ------------------------------------------------------- Actions

    def _resize_crop(self, delta: float, mark_user: bool = True) -> None:
        """Resize kotak (1:1) dengan mempertahankan titik pusatnya."""
        if self._image is None:
            return
        old_size = self.crop_size
        new_size = max(self.min_crop_size, min(self.max_crop_size, old_size + delta))
        if abs(new_size - old_size) > 0.5:
            center_x = self.crop_x + old_size / 2.0
            center_y = self.crop_y + old_size / 2.0
            self.crop_size = new_size
            self.crop_x = center_x - new_size / 2.0
            self.crop_y = center_y - new_size / 2.0
            if mark_user:
                self._user_resized = True
            self._refresh()

    def _reset_crop_size(self) -> None:
        self._user_resized = False
        self._resize_crop(min(float(CROP_SIZE), self.max_crop_size) - self.crop_size, mark_user=False)

    def _nudge(self, delta_x: int, delta_y: int) -> None:
        if self._image is None:
            return
        self.crop_x += delta_x
        self.crop_y += delta_y
        self._refresh()

    def _center_crop(self) -> None:
        if self._image is None:
            return
        self.crop_x = (self.orig_w - self.crop_size) / 2.0
        self.crop_y = (self.orig_h - self.crop_size) / 2.0
        self._refresh()

    def _change_zoom(self, delta: float) -> None:
        if self._image is None:
            return
        new_zoom = max(self.ZOOM_MIN, min(self.ZOOM_MAX, self.zoom_factor + delta))
        if abs(new_zoom - self.zoom_factor) > 0.01:
            self.zoom_factor = new_zoom
            self._refresh()

    def _reset_zoom(self) -> None:
        if self._image is None:
            return
        self.zoom_factor = 1.0
        self._refresh()

    async def _on_detect_clicked(self, e) -> None:
        image = self._image
        if image is None:
            return
        self._set_busy(True)
        self.face_status.value = "Mendeteksi wajah..."
        self.face_status.color = "#64748B"
        self.page.update(self.face_status)
        try:
            face = await asyncio.to_thread(detect_face, image)
        except Exception as exc:
            self._set_busy(False)
            self.face_status.value = f"Gagal mendeteksi wajah: {exc}"
            self.face_status.color = "#B91C1C"
            self.page.update(self.face_status)
            return
        if self._image is not image:  # foto diganti/dibatalkan saat deteksi berjalan
            return

        self._face = face
        # Pertahankan ukuran kotak bila sebelumnya sudah diperbesar/diperkecil oleh user
        fixed_size = int(round(self.crop_size)) if self._user_resized else None
        rect = compute_crop_rect(self.orig_w, self.orig_h, face, fixed_size=fixed_size)
        self._apply_rect(rect)

        auto_saved = False
        if face is not None and self._destination is not None:
            try:
                await asyncio.to_thread(
                    self._write_crop, image, self._destination, rect.left, rect.top, rect.size
                )
                auto_saved = True
            except Exception as exc:
                self._set_busy(False)
                self.status_text.value = f"Gagal menyimpan crop otomatis: {exc}"
                self.status_text.color = "#B91C1C"
                self.page.update(self.status_text)
                return

        self._set_face_status(face, rect, auto_saved=auto_saved)
        self._set_busy(False, update=False)
        self._update_geometry()
        self.page.update(self.editor_view)

        if auto_saved and self.on_auto_saved is not None and self._destination is not None:
            self.on_auto_saved(self._destination)

    def _on_cancel_clicked(self, e) -> None:
        self.clear()
        self.on_cancel()

    async def _on_crop_clicked(self, e) -> None:
        image, destination = self._image, self._destination
        if image is None or destination is None:
            return

        left = int(round(self.crop_x))
        top = int(round(self.crop_y))
        size = int(round(self.crop_size))

        self._set_busy(True)
        try:
            await asyncio.to_thread(self._write_crop, image, destination, left, top, size)
        except Exception as exc:
            self._set_busy(False)
            self.status_text.value = f"Gagal memotong gambar: {exc}"
            self.status_text.color = "#B91C1C"
            self.page.update(self.status_text)
            return

        self.clear()
        self.on_saved(destination)

    @staticmethod
    def _write_crop(image: np.ndarray, destination: Path, left: int, top: int, size: int) -> None:
        save_jpeg(crop_square(image, left, top, size, CROP_SIZE), destination)
