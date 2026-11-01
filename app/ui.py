"""Komponen antarmuka pengguna (UI) Flet untuk aplikasi pengambilan foto mahasiswa."""

import asyncio
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import flet as ft

from app.config import POSES
from app.config_ui import ConfigFormDialog
from app.crop_panel import ShutterCropPanel

MAHASISWA_API_URL = ""


def _fetch_mahasiswa_by_nim(nim: str, timeout: float = 10.0) -> Optional[Dict[str, Any]]:
    """Mengambil data mahasiswa dari API berdasarkan NIM (dijalankan di thread terpisah)."""
    query = urllib.parse.urlencode({"nim": nim})
    url = f"{MAHASISWA_API_URL}?{query}"
    req = urllib.request.Request(
        url,
        method="GET",
        headers={"Accept": "application/json", "User-Agent": "Canon-M50-FletApp/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        payload = json.loads(raw)

    if isinstance(payload, list):
        return payload[0] if len(payload) > 0 and isinstance(payload[0], dict) else None
    if isinstance(payload, dict):
        if "data" in payload and isinstance(payload["data"], list):
            return payload["data"][0] if payload["data"] else None
        if payload.get("nim") or payload.get("nama_mahasiswa"):
            return payload
    return None


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
        # on_cancle_save:Callable[[],None],
    ):
        self.page = page
        self.on_camera_toggle = on_camera_toggle
        self.on_capture_pose = on_capture_pose
        self.on_save_data = on_save_data
        self.on_crop_saved = on_crop_saved
        self.on_crop_cancel = on_crop_cancel
        # self.on_cancle_save = on_cancle_save

        # Config Form Dialog
        self.config_dialog = ConfigFormDialog(page=page, on_saved_callback=self._on_config_updated)

        # Form fields
        self._extra_student_data: Dict[str, str] = {}
        self.nim_field = ft.TextField(
            label="NIM *", 
            dense=True, 
            border=ft.OutlineInputBorder(border_radius=10,), 
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.InputFilter(
                allow=True,
                regex_string=r"[0-9]",
            ),
            on_submit=self.cari_mahasiswa,
            )
        self.nama_field = ft.TextField(label="Nama Lengkap Mahasiswa", dense=True, border=ft.OutlineInputBorder(border_radius=10,),read_only=True)
        # self.alamat_field = ft.TextField(
        #     label="Alamat",
        #     multiline=True,
        #     min_lines=2,
        #     max_lines=3,
        #     dense=True,
        #     border_radius=8,
        # )
        # self.kode_prodi_field = ft.TextField(label="Kode Prodi", dense=True, border_radius=8)
        self.nama_prodi_field = ft.TextField(label="Nama Prodi", dense=True, border=ft.OutlineInputBorder(border_radius=10,),read_only=True)
        # self.kode_fakultas_field = ft.TextField(label="Kode Fakultas", dense=True, border_radius=8)
        self.nama_fakultas_field = ft.TextField(label="Nama Fakultas", dense=True, border=ft.OutlineInputBorder(border_radius=10,),read_only=True)
        # self.kode_institusi_field = ft.TextField(label="Kode Institusi", dense=True, border_radius=8)
        self.nama_institusi_field = ft.TextField(label="Nama Institusi", dense=True, border=ft.OutlineInputBorder(border_radius=10,),read_only=True)
        self.semester_field = ft.TextField(label="Semester", dense=True, border=ft.OutlineInputBorder(border_radius=10,),read_only=True)

        self.student_detail_column = ft.Column(
            controls=[
                self.nama_field,
                self.nama_institusi_field,
                self.nama_fakultas_field,
                self.nama_prodi_field,
                self.semester_field,
            ],
            spacing=10,
            visible=False,
        )
        
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
            visible=False,
            style=ft.ButtonStyle(
            bgcolor="#16803C",
            color="#FFFFFF",
            shape=ft.RoundedRectangleBorder(radius=9),
            ),
        )

        self.mahasiswa_cancle_button = ft.FilledButton(
                    "Batal",
                    icon=ft.Icons.CANCEL,
                    on_click=lambda _: self.tampilkan_pesan("Apakah Anda yakin ingin membatalkan data?"),
                    height=44,
                    visible=False,
                    style=ft.ButtonStyle(
                    bgcolor="#5D6661",
                    color="#FFFFFF",
                    shape=ft.RoundedRectangleBorder(radius=9),
                    ),
                )
        
        self.mahasiswa_cari_button = ft.FilledButton(
                    "Cari",
                    icon=ft.Icons.SEARCH,
                    on_click=self.cari_mahasiswa,
                    height=44,
                    style=ft.ButtonStyle(
                    bgcolor="#05191D",
                    color="#FFFFFF",
                    shape=ft.RoundedRectangleBorder(radius=9),
                    ),
                )

        # Pose Cards
        self.pose_cards_row = ft.Row(
            wrap=True,
            spacing=9,
            run_spacing=9,
        )
        self._layout_ready = False
        self.pose_image_boxes: List[ft.Container] = []
        self.pose_labels: List[ft.Text] = []
        self.pose_buttons: List[ft.OutlinedButton] = []

    def _on_config_updated(self) -> None:
        """Callback ketika konfigurasi atau poses diperbarui dari form settings."""
        self.rebuild_pose_cards()
        self.notify("Pengaturan aplikasi telah diperbarui.", "#16803C")

    def rebuild_pose_cards(self) -> None:
        """Menyusun ulang kartu pose di UI berdasarkan nilai POSES terbaru."""

        self.pose_image_boxes.clear()
        self.pose_labels.clear()
        self.pose_buttons.clear()
        self.pose_cards_row.controls.clear()

        for i, (num, title, desc) in enumerate(POSES):
            self.pose_cards_row.controls.append(
                self.build_pose_card(i, num, title, desc)
            )

        # Update hanya jika UI sudah selesai dibuat
        if getattr(self, "_layout_ready", False):
            self.pose_cards_row.update()

    # def rebuild_pose_cards(self) -> None:
    #     """Menyusun ulang kartu pose di UI berdasarkan nilai POSES terbaru."""
    #     self.pose_image_boxes.clear()
    #     self.pose_labels.clear()
    #     self.pose_buttons.clear()
    #     self.pose_cards_row.controls.clear()

    #     for i, (num, title, desc) in enumerate(POSES):
    #         self.pose_cards_row.controls.append(self.build_pose_card(i, num, title, desc))
        
    #     if self.pose_cards_row.page is not None:
    #         self.pose_cards_row.update()
            

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
            "nama_prodi": (self.nama_prodi_field.value or "").strip(),
            "nama_fakultas": (self.nama_fakultas_field.value or "").strip(),
            "nama_institusi": (self.nama_institusi_field.value or "").strip(),
            "tempat_lahir": self._extra_student_data.get("tempat_lahir", ""),
            "tanggal_Lahir": self._extra_student_data.get("tanggal_Lahir", ""),
            "status_mahasiswa": self._extra_student_data.get("status_mahasiswa", ""),
        }

    async def cari_mahasiswa(self, _=None) -> None:
        """Mencari data mahasiswa lewat API berdasarkan NIM dan menampilkan form detail."""
        nim = self.get_nim()
        if not nim:
            self.notify("Masukkan NIM terlebih dahulu untuk mencari data.", "#B45309")
            return

        self.mahasiswa_cari_button.disabled = True
        self.mahasiswa_cari_button.content = "Mencari..."
        self.notify(f"Mencari data mahasiswa NIM {nim}...", "#1677E8")

        try:
            data = await asyncio.to_thread(_fetch_mahasiswa_by_nim, nim)
        except urllib.error.HTTPError as exc:
            self.mahasiswa_cari_button.disabled = False
            self.mahasiswa_cari_button.content = "Cari"
            self.notify(f"Gagal mengambil data dari API (HTTP {exc.code}).", "#B91C1C")
            return
        except Exception as exc:
            self.mahasiswa_cari_button.disabled = False
            self.mahasiswa_cari_button.content = "Cari"
            self.notify(f"Gagal menghubungi API mahasiswa: {exc}", "#B91C1C")
            return

        self.mahasiswa_cari_button.disabled = False
        self.mahasiswa_cari_button.content = "Cari"

        if not data:
            self.student_detail_column.visible = False
            self.mahasiswa_simpan_button.visible = False
            self.mahasiswa_cancle_button.visible = False
            self.notify(f"Data mahasiswa dengan NIM {nim} tidak ditemukan.", "#B45309")
            return

        self.nim_field.value = str(data.get("nim") or nim)
        self.nama_field.value = str(data.get("nama_mahasiswa") or "")
        self.nama_prodi_field.value = str(data.get("nama_prodi") or "")
        self.nama_fakultas_field.value = str(data.get("fakultas") or "")
        self.nama_institusi_field.value = str(data.get("institusi") or "")
        semester_val = data.get("semester")
        self.semester_field.value = str(semester_val) if semester_val is not None else ""

        self._extra_student_data = {
            "tempat_lahir": str(data.get("tempat_lahir") or ""),
            "tanggal_Lahir": str(data.get("tanggal_Lahir") or ""),
            "status_mahasiswa": str(data.get("status_mahasiswa") or ""),
        }

        self.student_detail_column.visible = True
        self.mahasiswa_simpan_button.visible = True
        self.mahasiswa_cancle_button.visible = True
        self.notify(f"Data ditemukan: {self.nama_field.value} ({self.nim_field.value})", "#16803C")

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
                # self.pose_labels[index].value = "✓ Foto tersimpan"
                # self.pose_labels[index].color = "#16803C"
                self.pose_status.value = f"Foto {index + 1}/7 tersimpan: {POSES[index][1]}"
                self.page.update()
            except Exception as exc:
                print(f"[UI] Error loading thumbnail: {exc}")

    def cancel_save(self) -> None:
        self.nim_field.value = ""
        self.nama_institusi_field.value = ""
        self.nama_field.value = ""
        self.nama_prodi_field.value = ""
        self.nama_fakultas_field.value = ""
        self.semester_field.value = ""
        self._extra_student_data = {}
        self.student_detail_column.visible = False
        self.mahasiswa_simpan_button.visible = False
        self.mahasiswa_cancle_button.visible = False
        self.clear_all_pose_thumbnails()
        self.page.update()

    def tampilkan_pesan(self,pesan)-> None:
        if self.nim_field.value and self.nim_field.value.strip():
            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Informasi"),
                content=ft.Text(pesan),
                actions=[
                    ft.TextButton(
                        "Ya",
                        on_click=lambda e: (
                            self.page.pop_dialog(),
                            self.cancel_save()
                        )
                    ),
                    ft.TextButton(
                        "Tidak",
                        on_click=lambda e: self.page.pop_dialog()
                    ),
                ],
            )
            self.page.show_dialog(dlg)
        

    def clear_all_pose_thumbnails(self) -> None:
        try:
            for index, image_box in enumerate(self.pose_image_boxes):
                self.pose_image_boxes[index].content = ft.Column(
                controls=[
                    ft.Icon(ft.Icons.PERSON, size=34, color="#6482A8"),
                    # ft.Text("Belum diambil", size=10, color="#64748B"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=3,
            )

            self.page.update()

        except Exception as exc:
            print(f"[UI] Error clearing thumbnails: {exc}")

    def reset_pose_thumbnail(self, index: int) -> None:
        if 0 <= index < len(self.pose_image_boxes):
            self.pose_image_boxes[index].content = ft.Column(
                controls=[
                    ft.Icon(ft.Icons.PERSON, size=34, color="#6482A8"),
                    # ft.Text("Belum diambil", size=10, color="#64748B"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=3,
            )
            # self.pose_labels[index].value = "Belum diambil"
            # self.pose_labels[index].color = "#64748B"
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
                                content=ft.Text(number, color="#FFFFFF", weight=ft.FontWeight.BOLD, size=10),
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
        self.rebuild_pose_cards()

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
                            # ft.Text(
                            #     "gphoto2 • SQLite Config • Live Preview OpenCV • Crop Wajah",
                            #     size=13,
                            #     color="#DCEBFA",
                            # ),
                        ],
                        spacing=2,
                    ),
                    ft.Container(expand=True),
                    ft.FilledButton(
                        "Pengaturan",
                        icon=ft.Icons.SETTINGS,
                        on_click=lambda _: self.config_dialog.open_dialog(),
                        style=ft.ButtonStyle(
                            bgcolor="#1E3A8A",
                            color="#FFFFFF",
                            shape=ft.RoundedRectangleBorder(radius=5),
                        ),
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
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
                            # self.camera_status,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self.tabs,
                    self.camera_status,
                    # ft.Text(
                    #     "Preview berasal dari HDMI capture card via OpenCV; foto asli diambil via gphoto2 USB "
                    #     "dan langsung ditampilkan di tab Hasil Shutter & Crop.",
                    #     size=11,
                    #     color="#52657D",
                    # ),
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
                            ft.Text("Pengambilan Foto Wajah", size=18, weight=ft.FontWeight.BOLD, color="#17365D"),
                        ],
                        spacing=8,
                    ),
                    self.pose_status,
                    self.pose_cards_row,
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
                    self.student_detail_column,
                    ft.Row(
                        controls=[self.mahasiswa_simpan_button,self.mahasiswa_cancle_button,self.mahasiswa_cari_button]
                    ),
                    
                    # ft.Text(
                    #     "Data mahasiswa disimpan ke data_mahasiswa.json beserta 7 foto hasil crop 640x640.",
                    #     size=11,
                    #     color="#64748B",
                    # ),
                ],
                spacing=10,
            ),
        )

        layout = ft.Column(
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
                    controls=[
                        ft.Container(
                            expand=4,
                            content=poses_panel,
                        ),
                    ],
                ),
            ],
            spacing=14,
            expand=True,
        )

        return layout

