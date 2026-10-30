"""Komponen antarmuka pengguna (UI) Flet untuk aplikasi pengambilan foto mahasiswa."""

from pathlib import Path
from typing import Callable, Dict, List, Optional

import flet as ft

from app.config import POSES
from app.crop_panel import ShutterCropPanel


class AppUI:
    """Mengelola pembuatan dan pembaruan komponen tampilan UI."""

    TAB_LIVE = 0
    TAB_RESULT = 1

    def __init__(
        self,
        page: ft.Page,
        on_camera_toggle: Callable[[], None],
        on_capture_pose: Callable[[int], None],
        on_save_data: Callable[[], None],
        on_crop_saved: Callable[[Path], None],
        on_crop_cancel: Callable[[], None],
    ):
        self.page = page
        self.on_camera_toggle = on_camera_toggle
        self.on_capture_pose = on_capture_pose
        self.on_save_data = on_save_data
        self.on_crop_saved = on_crop_saved
        self.on_crop_cancel = on_crop_cancel

        # Form fields
        self.nim_field = ft.TextField(label="NIM *", dense=True, border=ft.OutlineInputBorder(border_radius=10,),)
        self.nama_field = ft.TextField(label="Nama Lengkap Mahasiswa", dense=True, border=ft.OutlineInputBorder(border_radius=10,),)
        # self.alamat_field = ft.TextField(
        #     label="Alamat",
        #     multiline=True,
        #     min_lines=2,
        #     max_lines=3,
        #     dense=True,
        #     border_radius=8,
        # )
        # self.kode_prodi_field = ft.TextField(label="Kode Prodi", dense=True, border_radius=8)
        self.nama_prodi_field = ft.TextField(label="Nama Prodi", dense=True, border=ft.OutlineInputBorder(border_radius=10,),)
        # self.kode_fakultas_field = ft.TextField(label="Kode Fakultas", dense=True, border_radius=8)
        self.nama_fakultas_field = ft.TextField(label="Nama Fakultas", dense=True, border=ft.OutlineInputBorder(border_radius=10,),)
        # self.kode_institusi_field = ft.TextField(label="Kode Institusi", dense=True, border_radius=8)
        self.nama_institusi_field = ft.TextField(label="Nama Institusi", dense=True, border=ft.OutlineInputBorder(border_radius=10,),)
        self.semester_field = ft.TextField(label="Semester", dense=True, border=ft.OutlineInputBorder(border_radius=10,),)
        
        # Status text
        self.camera_status = ft.Text("Kamera belum aktif", color="#64748B", size=13)
        self.pose_status = ft.Text("Pilih posisi wajah, lalu ambil foto.", color="#334155", size=13)

        # Preview controls
        self.preview_image = ft.Image(
            src=b"",
            fit=ft.BoxFit.CONTAIN,
            width=760,
            height=390,
            gapless_playback=True,
            border_radius=8,
        )
        self.preview_placeholder = ft.Column(
            controls=[
                ft.Icon(ft.Icons.VIDEOCAM_OFF_OUTLINED, size=54, color="#6482A8"),
                ft.Text("Video preview belum aktif", size=15, weight=ft.FontWeight.W_600, color="#334155"),
                ft.Text("Sambungkan HDMI capture card, lalu klik tombol 'Camera On'.", size=12, color="#64748B"),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
        )
        self.preview_box = ft.Container(
            width=760,
            height=390,
            bgcolor="#E8EEF7",
            border_radius=9,
            padding=5,
            alignment=ft.Alignment.CENTER,
            content=self.preview_placeholder,
        )

        # Panel crop hasil shutter (isi tab kedua)
        self.crop_panel = ShutterCropPanel(
            page,
            on_saved=self._handle_crop_saved,
            on_cancel=self._handle_crop_cancel,
            on_auto_saved=self._handle_crop_auto_saved,
        )

        # Tab panel: Live Preview | Hasil Shutter & Crop.
        # Isi tab diganti lewat visible (bukan TabBarView) agar geser mouse di kotak crop
        # tidak berpindah tab, dan live preview tetap berjalan di latar belakang.
        self.tabs = ft.Tabs(
            length=2,
            selected_index=self.TAB_LIVE,
            on_change=self._on_tab_changed,
            content=ft.Column(
                tight=True,
                spacing=8,
                controls=[
                    ft.TabBar(
                        tabs=[
                            ft.Tab(label="Live Preview", icon=ft.Icons.VIDEOCAM),
                             ft.Tab(label="Hasil Shutter & Crop", icon=ft.Icons.CROP),
                        ],
                    ),
                    self.preview_box,
                    self.crop_panel.control,
                ],
            ),
        )

        # Camera Button
        self.camera_button = ft.FilledButton(
            "Camera On",
            icon=ft.Icons.VIDEOCAM,
            on_click=lambda _: self.on_camera_toggle(),
            height=46,
            style=ft.ButtonStyle(
                bgcolor="#1677E8",
                color="#FFFFFF",
                shape=ft.RoundedRectangleBorder(radius=9),
            ),
        )

        self.mahasiswa_simpan_button = ft.FilledButton(
            "Simpan",
            icon=ft.Icons.SAVE,
            on_click=lambda _: self.on_save_data(),
            height=44,
            style=ft.ButtonStyle(
            bgcolor="#16803C",
            color="#FFFFFF",
            shape=ft.RoundedRectangleBorder(radius=9),
            ),
        )

        self.mahasiswa_cancle_button = ft.FilledButton(
                    "Batal",
                    icon=ft.Icons.CANCEL,
                    # on_click=lambda _: self.on_save_data(),
                    height=44,
                    style=ft.ButtonStyle(
                    bgcolor="#5D6661",
                    color="#FFFFFF",
                    shape=ft.RoundedRectangleBorder(radius=9),
                    ),
                )

        # Pose Cards
        self.pose_image_boxes: List[ft.Container] = []
        self.pose_labels: List[ft.Text] = []
        self.pose_buttons: List[ft.OutlinedButton] = []

    def select_tab(self, index: int) -> None:
        """Berpindah tab tanpa menghentikan live preview."""
        self.tabs.selected_index = index
        self._apply_tab_visibility(index)
        self.page.update(self.tabs)

    def _apply_tab_visibility(self, index: int) -> None:
        self.preview_box.visible = index == self.TAB_LIVE
        self.crop_panel.control.visible = index == self.TAB_RESULT

    def _on_tab_changed(self, e) -> None:
        try:
            index = int(e.data)
        except (TypeError, ValueError):
            index = self.tabs.selected_index
        self.tabs.selected_index = index
        self._apply_tab_visibility(index)
        self.page.update(self.preview_box, self.crop_panel.control)

    async def show_shutter_photo(self, jpeg_bytes: bytes, pose_label: str, destination: Path) -> bool:
        """Menampilkan hasil shutter (dari memori) di tab Hasil Shutter & Crop."""
        auto_saved = await self.crop_panel.load_photo(jpeg_bytes, pose_label, destination)
        self.select_tab(self.TAB_RESULT)
        return auto_saved

    def _handle_crop_auto_saved(self, destination: Path) -> None:
        self.on_crop_saved(destination)

    def _handle_crop_saved(self, destination: Path) -> None:
        self.select_tab(self.TAB_LIVE)
        self.on_crop_saved(destination)

    def _handle_crop_cancel(self) -> None:
        self.select_tab(self.TAB_LIVE)
        self.on_crop_cancel()

    def get_nim(self) -> str:
        return (self.nim_field.value or "").strip()

    def get_form_values(self) -> Dict[str, str]:
        return {
            "nim": self.get_nim(),
            "nama": (self.nama_field.value or "").strip(),
            "semester": (self.semester_field.value or "").strip(),
            "kode_prodi": (self.kode_prodi_field.value or "").strip(),
            "nama_prodi": (self.nama_prodi_field.value or "").strip(),
            "kode_fakultas": (self.kode_fakultas_field.value or "").strip(),
            "nama_fakultas": (self.nama_fakultas_field.value or "").strip(),
            "kode_institusi": (self.kode_institusi_field.value or "").strip(),
            "nama_institusi": (self.nama_institusi_field.value or "").strip(),
        }

    def notify(self, message: str, color: str = "#334155") -> None:
        self.camera_status.value = message
        self.camera_status.color = color
        self.page.update()

    def set_camera_state(self, is_active: bool) -> None:
        if is_active:
            self.camera_button.content = "Camera Off"
            self.camera_button.icon = ft.Icons.VIDEOCAM_OFF
            self.camera_button.style.bgcolor = "#DC2626"
            if self.preview_box.content is not self.preview_image:
                self.preview_box.content = self.preview_image
        else:
            self.camera_button.content = "Camera On"
            self.camera_button.icon = ft.Icons.VIDEOCAM
            self.camera_button.style.bgcolor = "#1677E8"
            self.preview_box.content = self.preview_placeholder
            self.preview_image.src = b""
        self.page.update()

    def update_preview_frame(self, frame_bytes: bytes) -> None:
        self.preview_image.src = frame_bytes
        if self.preview_box.content is not self.preview_image:
            self.preview_box.content = self.preview_image
            self.preview_box.update()
        else:
            self.preview_image.update()

    def set_pose_thumbnail(self, index: int, image_path: Path) -> None:
        if 0 <= index < len(self.pose_image_boxes):
            try:
                data = image_path.read_bytes()
                self.pose_image_boxes[index].content = ft.Image(
                    src=data,
                    width=139,
                    height=95,
                    fit=ft.BoxFit.COVER,
                    border_radius=8,
                    gapless_playback=True,
                )
                self.pose_labels[index].value = "✓ Foto tersimpan"
                self.pose_labels[index].color = "#16803C"
                self.pose_status.value = f"Foto {index + 1}/7 tersimpan: {POSES[index][1]}"
                self.page.update()
            except Exception as exc:
                print(f"[UI] Error loading thumbnail: {exc}")

    def reset_pose_thumbnail(self, index: int) -> None:
        if 0 <= index < len(self.pose_image_boxes):
            self.pose_image_boxes[index].content = ft.Column(
                controls=[
                    ft.Icon(ft.Icons.PERSON, size=34, color="#6482A8"),
                    ft.Text("Belum diambil", size=10, color="#64748B"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=3,
            )
            self.pose_labels[index].value = "Belum diambil"
            self.pose_labels[index].color = "#64748B"
            self.pose_status.value = f"Foto pose {index + 1} ({POSES[index][1]}) dibatalkan."
            self.page.update()

    def build_pose_card(self, index: int, number: str, title: str, instruction: str) -> ft.Container:
        image_box = ft.Container(
            height=95,
            bgcolor="#E8EEF7",
            border_radius=8,
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.PERSON, size=34, color="#6482A8"),
                    ft.Text("Belum diambil", size=10, color="#64748B"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=3,
            ),
        )
        label = ft.Text("Belum diambil", size=11, color="#64748B")
        button = ft.OutlinedButton(
            "Ambil foto",
            icon=ft.Icons.PHOTO_CAMERA,
            on_click=lambda _, i=index: self.on_capture_pose(i),
        )

        card = ft.Container(
            width=155,
            padding=8,
            border=ft.Border.all(1, "#D5E2F4"),
            border_radius=10,
            bgcolor="#FFFFFF",
            content=ft.Column(
                controls=[
                    image_box,
                    ft.Row(
                        controls=[
                            ft.Container(
                                width=25,
                                height=25,
                                border_radius=20,
                                bgcolor="#1677E8",
                                alignment=ft.Alignment.CENTER,
                                content=ft.Text(number, color="#FFFFFF", weight=ft.FontWeight.BOLD),
                            ),
                            ft.Text(title, size=12, weight=ft.FontWeight.BOLD, color="#17365D"),
                        ],
                        spacing=7,
                    ),
                    ft.Text(instruction, size=10, color="#52657D"),
                    label,
                    button,
                ],
                spacing=6,
            ),
        )

        self.pose_image_boxes.append(image_box)
        self.pose_labels.append(label)
        self.pose_buttons.append(button)
        return card

    def build_layout(self) -> ft.Control:
        header = ft.Container(
            padding=16,
            bgcolor="#24558C",
            border_radius=12,
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.PHOTO_CAMERA, size=32, color="#FFFFFF"),
                    ft.Column(
                        controls=[
                            ft.Text(
                                "Aplikasi Pengambilan Foto Mahasiswa",
                                size=22,
                                weight=ft.FontWeight.BOLD,
                                color="#FFFFFF",
                            ),
                            ft.Text(
                                "gphoto2 • 7 Pose Wajah • Live Preview OpenCV • Crop Wajah 640x640",
                                size=13,
                                color="#DCEBFA",
                            ),
                        ],
                        spacing=2,
                    ),
                ],
                spacing=12,
            ),
        )

        preview_panel = ft.Container(
            padding=14,
            bgcolor="#FFFFFF",
            border=ft.Border.all(1, "#D6E4F5"),
            border_radius=12,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.CAMERA_ALT, color="#1767B1", size=22),
                            ft.Text("Kamera & Hasil Shutter", size=18, weight=ft.FontWeight.BOLD, color="#17365D"),
                            ft.Container(expand=True),
                            self.camera_status,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self.tabs,
                    ft.Text(
                        "Preview berasal dari HDMI capture card via OpenCV; foto asli diambil via gphoto2 USB "
                        "dan langsung ditampilkan di tab Hasil Shutter & Crop.",
                        size=11,
                        color="#52657D",
                    ),
                    ft.Row(
                        controls=[self.camera_button],
                        spacing=10,
                        wrap=True,
                    ),
                ],
                spacing=10,
            ),
        )

        poses_panel = ft.Container(
            padding=14,
            bgcolor="#FFFFFF",
            border=ft.Border.all(1, "#D6E4F5"),
            border_radius=12,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.FACE, color="#1767B1", size=22),
                            ft.Text("Pengambilan 7 Foto Wajah", size=18, weight=ft.FontWeight.BOLD, color="#17365D"),
                        ],
                        spacing=8,
                    ),
                    self.pose_status,
                    ft.Row(
                        controls=[
                            self.build_pose_card(i, num, title, desc)
                            for i, (num, title, desc) in enumerate(POSES)
                        ],
                        wrap=True,
                        spacing=9,
                        run_spacing=9,
                    ),
                ],
                spacing=10,
            ),
        )

        form_panel = ft.Container(
            padding=16,
            bgcolor="#FFFFFF",
            border=ft.Border.all(1, "#D6E4F5"),
            border_radius=12,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.BADGE, color="#1767B1", size=22),
                            ft.Text("Data Mahasiswa", size=18, weight=ft.FontWeight.BOLD, color="#17365D"),
                        ],
                        spacing=8,
                    ),
                    self.nim_field,
                    self.nama_field,
                    # self.alamat_field,
                    # self.kode_prodi_field,
                    self.nama_institusi_field,
                    self.nama_fakultas_field,
                    self.nama_prodi_field,
                    self.semester_field,
                    # self.kode_institusi_field,
                    ft.Row(
                        controls=[self.mahasiswa_simpan_button,self.mahasiswa_cancle_button]
                    ),
                    
                    ft.Text(
                        "Data mahasiswa disimpan ke data_mahasiswa.json beserta 7 foto hasil crop 640x640.",
                        size=11,
                        color="#64748B",
                    ),
                ],
                spacing=10,
            ),
        )

        return ft.Column(
            controls=[
                header,
                ft.Row(
                    controls=[
                        ft.Container(
                            expand=6,
                            content=ft.Row(
                                controls=[preview_panel, form_panel],
                                spacing=14,
                                vertical_alignment=ft.CrossAxisAlignment.START,
                            ),
                            
                        ),
                        
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    spacing=14,
                ),
                ft.Row(
                    ft.Container(
                        expand=4,
                        content=poses_panel,
                        ),
                )
            ],
            spacing=14,
            expand=True,
        )

