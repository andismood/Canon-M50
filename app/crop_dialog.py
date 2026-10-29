"""Dialog crop manual dengan kotak yang dapat digeser dan di-resize secara presisi (rasio 1:1)."""

from pathlib import Path
from typing import Callable, Optional

import flet as ft

from app.config import CROP_SIZE
from app.image_utils import crop_image_640, get_image_size


class ManualCropDialog:
    """Mengelola AlertDialog untuk menampilkan foto asli, zoom, pergeseran, dan pengubahan ukuran kotak crop."""

    VIEWPORT_W = 760
    VIEWPORT_H = 460

    def __init__(
        self,
        page: ft.Page,
        source_image_path: Path,
        destination_path: Path,
        pose_title: str,
        on_success: Callable[[Path], None],
        on_cancel: Callable[[], None],
    ):
        self.page = page
        self.source_image_path = source_image_path
        self.destination_path = destination_path
        self.pose_title = pose_title
        self.on_success = on_success
        self.on_cancel = on_cancel

        # Baca dimensi asli gambar
        self.orig_w, self.orig_h = get_image_size(source_image_path)
        if self.orig_w < CROP_SIZE or self.orig_h < CROP_SIZE:
            raise ValueError(
                f"Resolusi foto sumber ({self.orig_w}x{self.orig_h}) lebih kecil dari ukuran crop wajib ({CROP_SIZE}x{CROP_SIZE} px)."
            )

        # Ukuran kotak crop (awal 640x640 px, rasio 1:1)
        self.crop_size: float = float(CROP_SIZE)
        self.min_crop_size: float = 200.0
        self.max_crop_size: float = float(min(self.orig_w, self.orig_h))

        # Posisi crop dalam koordinat piksel asli (awal di tengah)
        self.crop_x: float = (self.orig_w - self.crop_size) / 2.0
        self.crop_y: float = (self.orig_h - self.crop_size) / 2.0

        # Zoom level
        # Fit scale agar muat di dalam viewport awal
        self.base_fit_scale = min(
            self.VIEWPORT_W / self.orig_w,
            self.VIEWPORT_H / self.orig_h,
            1.0,
        )
        self.zoom_factor: float = 1.0  # Pengali zoom relatif terhadap base_fit_scale

        # Komponen gambar latar
        self.image_control = ft.Image(
            src=str(source_image_path.resolve()),
            fit=ft.BoxFit.FILL,
            gapless_playback=True,
        )

        # Badge label ukuran kotak di sudut kiri atas
        self.crop_badge_text = ft.Text(
            f"{int(self.crop_size)}x{int(self.crop_size)}",
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

        # Handle resize di sudut kanan bawah kotak (tarik mouse untuk mengubah ukuran)
        self.resize_handle = ft.GestureDetector(
            content=ft.Container(
                width=24,
                height=24,
                bgcolor="#1677E8",
                border_radius=ft.BorderRadius(top_left=12, top_right=0, bottom_left=0, bottom_right=4),
                alignment=ft.Alignment.BOTTOM_RIGHT,
                padding=ft.Padding.only(right=2, bottom=2),
                content=ft.Icon(
                    ft.Icons.OPEN_IN_FULL,
                    size=13,
                    color="#FFFFFF",
                ),
                tooltip="Tarik sudut ini untuk memperbesar/memperkecil kotak (1:1)",
            ),
            on_pan_update=self._handle_resize_handle_pan,
        )

        # Wadah kotak crop (rectangle)
        self.crop_box = ft.Container(
            border=ft.Border.all(2, "#1677E8"),
            bgcolor="#331677E8",  # transparan biru
            border_radius=4,
            content=ft.Stack(
                controls=[
                    ft.Container(
                        alignment=ft.Alignment.TOP_LEFT,
                        content=self.crop_badge,
                    ),
                    ft.Container(
                        alignment=ft.Alignment.BOTTOM_RIGHT,
                        content=self.resize_handle,
                    ),
                ],
                expand=True,
            ),
        )

        # Stack gambar dan kotak crop
        self.stack = ft.Stack(
            controls=[self.image_control, self.crop_box],
        )

        # Gesture detector untuk menggeser kotak atau klik untuk memusatkan
        self.gesture_detector = ft.GestureDetector(
            content=self.stack,
            on_pan_update=self._handle_pan_update,
            on_tap_up=self._handle_tap_up,
        )

        # Kontainer viewport dengan scroll jika ukuran gambar melebihi viewport saat di-zoom
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

        self.status_text = ft.Text(
            "",
            size=11,
            color="#475569",
        )

        self.zoom_text = ft.Text(
            "Zoom: 100%",
            size=12,
            weight=ft.FontWeight.W_600,
            color="#334155",
        )

        self.crop_size_text = ft.Text(
            f"Kotak: {int(self.crop_size)}px",
            size=12,
            weight=ft.FontWeight.W_600,
            color="#1E293B",
        )

        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.CROP, color="#1677E8", size=24),
                    ft.Text(
                        f"Crop Manual Wajah - {pose_title}",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color="#1E293B",
                    ),
                ],
                spacing=8,
            ),
            content=ft.Container(
                width=self.VIEWPORT_W + 20,
                content=ft.Column(
                    controls=[
                        # Toolbar baris 1: Kontrol Zoom & Kontrol Ukuran Kotak
                        ft.Row(
                            controls=[
                                # Zoom controls
                                ft.IconButton(
                                    icon=ft.Icons.ZOOM_OUT,
                                    tooltip="Perkecil Tampilan Foto",
                                    on_click=lambda _: self._change_zoom(-0.15),
                                ),
                                self.zoom_text,
                                ft.IconButton(
                                    icon=ft.Icons.ZOOM_IN,
                                    tooltip="Perbesar Tampilan Foto",
                                    on_click=lambda _: self._change_zoom(+0.15),
                                ),
                                ft.OutlinedButton(
                                    "Reset Zoom",
                                    icon=ft.Icons.FIT_SCREEN,
                                    on_click=lambda _: self._reset_zoom(),
                                ),
                                ft.Container(width=12),
                                # Resize kotak crop controls
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
                                ft.Container(expand=True),
                                # Navigasi posisi
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
                            ],
                            alignment=ft.MainAxisAlignment.START,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        self.viewport_container,
                        ft.Row(
                            controls=[
                                ft.Text(
                                    "Tips: Seret mouse untuk memindahkan kotak. Tarik sudut kanan-bawah atau tombol [-] [+] untuk resize.",
                                    size=11,
                                    color="#64748B",
                                ),
                                ft.Container(expand=True),
                                self.status_text,
                            ],
                        ),
                    ],
                    spacing=8,
                    tight=True,
                ),
            ),
            actions=[
                ft.OutlinedButton(
                    "Batal / Ulangi",
                    icon=ft.Icons.CLOSE,
                    on_click=self._on_cancel_clicked,
                ),
                ft.FilledButton(
                    "Crop & Simpan Foto",
                    icon=ft.Icons.CHECK,
                    style=ft.ButtonStyle(
                        bgcolor="#16803C",
                        color="#FFFFFF",
                    ),
                    on_click=self._on_crop_clicked,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self._update_geometry()

    @property
    def current_scale(self) -> float:
        """Skala rasio antara piksel tampilan layar dan piksel foto asli."""
        return self.base_fit_scale * self.zoom_factor

    def _clamp_crop(self) -> None:
        """Memastikan ukuran dan posisi crop tidak keluar dari batas foto asli."""
        self.crop_size = max(self.min_crop_size, min(self.crop_size, self.max_crop_size))
        max_x = max(0.0, float(self.orig_w - self.crop_size))
        max_y = max(0.0, float(self.orig_h - self.crop_size))
        self.crop_x = max(0.0, min(self.crop_x, max_x))
        self.crop_y = max(0.0, min(self.crop_y, max_y))

    def _update_geometry(self) -> None:
        """Memperbarui ukuran kontrol tampilan layar berdasarkan skala, posisi, dan ukuran crop."""
        self._clamp_crop()
        scale = self.current_scale

        disp_w = max(10, int(round(self.orig_w * scale)))
        disp_h = max(10, int(round(self.orig_h * scale)))
        disp_box_size = max(10, int(round(self.crop_size * scale)))

        disp_box_left = int(round(self.crop_x * scale))
        disp_box_top = int(round(self.crop_y * scale))

        # Update kontrol Flet
        self.image_control.width = disp_w
        self.image_control.height = disp_h

        self.stack.width = disp_w
        self.stack.height = disp_h

        self.crop_box.left = disp_box_left
        self.crop_box.top = disp_box_top
        self.crop_box.width = disp_box_size
        self.crop_box.height = disp_box_size

        self.crop_badge_text.value = f"{int(self.crop_size)}x{int(self.crop_size)}"
        self.crop_size_text.value = f"Kotak: {int(self.crop_size)}px"
        self.zoom_text.value = f"Zoom: {int(round(self.zoom_factor * 100))}%"
        self.status_text.value = (
            f"Foto: {self.orig_w}x{self.orig_h} px | "
            f"Kotak: {int(self.crop_size)}x{int(self.crop_size)} px (Output: {CROP_SIZE}x{CROP_SIZE} px) di ({int(self.crop_x)}, {int(self.crop_y)})"
        )

    def _handle_pan_update(self, e: ft.DragUpdateEvent) -> None:
        """Menangani gesture drag untuk memindahkan posisi kotak crop."""
        dx = 0.0
        dy = 0.0
        if getattr(e, "local_delta", None):
            dx = float(e.local_delta.x)
            dy = float(e.local_delta.y)
        elif getattr(e, "global_delta", None):
            dx = float(e.global_delta.x)
            dy = float(e.global_delta.y)

        scale = self.current_scale
        if scale > 0:
            self.crop_x += dx / scale
            self.crop_y += dy / scale
            self._update_geometry()
            self.page.update()

    def _handle_resize_handle_pan(self, e: ft.DragUpdateEvent) -> None:
        """Menangani gesture drag pada sudut kanan bawah untuk me-resize kotak (rasio 1:1)."""
        dx = 0.0
        dy = 0.0
        if getattr(e, "local_delta", None):
            dx = float(e.local_delta.x)
            dy = float(e.local_delta.y)
        elif getattr(e, "global_delta", None):
            dx = float(e.global_delta.x)
            dy = float(e.global_delta.y)

        scale = self.current_scale
        if scale > 0:
            # Gunakan delta rata-rata (dx + dy) / 2 untuk mempertahankan rasio persegi 1:1
            delta = ((dx + dy) / 2.0) / scale
            old_size = self.crop_size
            new_size = max(self.min_crop_size, min(self.max_crop_size, old_size + delta))
            if abs(new_size - old_size) > 0.5:
                self.crop_size = new_size
                self._update_geometry()
                self.page.update()

    def _handle_tap_up(self, e: ft.TapEvent) -> None:
        """Menangani klik pada gambar untuk memusatkan kotak crop di titik klik."""
        scale = self.current_scale
        if scale <= 0 or not getattr(e, "local_position", None):
            return

        click_x_orig = e.local_position.x / scale
        click_y_orig = e.local_position.y / scale

        # Pusatkan kotak crop di koordinat klik
        self.crop_x = click_x_orig - (self.crop_size / 2.0)
        self.crop_y = click_y_orig - (self.crop_size / 2.0)
        self._update_geometry()
        self.page.update()

    def _resize_crop(self, delta: float) -> None:
        """Mengubah ukuran kotak crop dengan mempertahankan titik pusat dan aspect ratio 1:1."""
        old_size = self.crop_size
        new_size = max(self.min_crop_size, min(self.max_crop_size, old_size + delta))
        if abs(new_size - old_size) > 0.5:
            # Pertahankan titik tengah saat di-resize
            center_x = self.crop_x + (old_size / 2.0)
            center_y = self.crop_y + (old_size / 2.0)
            self.crop_size = new_size
            self.crop_x = center_x - (new_size / 2.0)
            self.crop_y = center_y - (new_size / 2.0)
            self._update_geometry()
            self.page.update()

    def _reset_crop_size(self) -> None:
        """Mengembalikan ukuran kotak ke standar CROP_SIZE (640x640 px)."""
        default_target = min(float(CROP_SIZE), self.max_crop_size)
        self._resize_crop(default_target - self.crop_size)

    def _nudge(self, delta_x: int, delta_y: int) -> None:
        """Menggeser kotak crop secara halus."""
        self.crop_x += delta_x
        self.crop_y += delta_y
        self._update_geometry()
        self.page.update()

    def _center_crop(self) -> None:
        """Memusatkan kotak crop di tengah gambar asli."""
        self.crop_x = (self.orig_w - self.crop_size) / 2.0
        self.crop_y = (self.orig_h - self.crop_size) / 2.0
        self._update_geometry()
        self.page.update()

    def _change_zoom(self, delta: float) -> None:
        """Mengubah faktor zoom perbesar/perkecil gambar."""
        new_zoom = max(0.4, min(3.0, self.zoom_factor + delta))
        if abs(new_zoom - self.zoom_factor) > 0.01:
            self.zoom_factor = new_zoom
            self._update_geometry()
            self.page.update()

    def _reset_zoom(self) -> None:
        """Mengembalikan zoom ke 100% dari rasio viewport."""
        self.zoom_factor = 1.0
        self._update_geometry()
        self.page.update()

    def show(self) -> None:
        """Menampilkan dialog pada halaman Flet."""
        if hasattr(self.page, "show_dialog"):
            self.page.show_dialog(self.dialog)
        elif hasattr(self.page, "open"):
            self.page.open(self.dialog)
        elif hasattr(self.page, "overlay"):
            if self.dialog not in self.page.overlay:
                self.page.overlay.append(self.dialog)
            self.dialog.open = True
            self.page.update()
        else:
            self.page.dialog = self.dialog
            self.dialog.open = True
            self.page.update()

    def close(self) -> None:
        """Menutup dialog."""
        if hasattr(self.page, "pop_dialog"):
            self.page.pop_dialog()
        elif hasattr(self.page, "close"):
            self.page.close(self.dialog)
        else:
            self.dialog.open = False
            self.page.update()

    def _on_cancel_clicked(self, e) -> None:
        self.close()
        self.on_cancel()

    def _on_crop_clicked(self, e) -> None:
        try:
            crop_image_640(
                input_path=self.source_image_path,
                output_path=self.destination_path,
                left=int(round(self.crop_x)),
                top=int(round(self.crop_y)),
                crop_size=int(round(self.crop_size)),
                target_size=CROP_SIZE,
            )
            self.close()
            self.on_success(self.destination_path)
        except Exception as exc:
            self.status_text.value = f"Gagal memotong gambar: {exc}"
            self.status_text.color = "#B91C1C"
            self.page.update()
