"""Komponen dialog/form pengaturan konfigurasi aplikasi dan manajemen CRUD poses."""

import asyncio
from pathlib import Path
from typing import Callable, Optional
import flet as ft
from app import db
import app.config as config


class ConfigFormDialog:
    """Dialog UI Flet untuk mengelola konfigurasi umum dan CRUD poses berbasis SQLite."""

    def __init__(self, page: ft.Page, on_saved_callback: Optional[Callable[[], None]] = None):
        self.page = page
        self.on_saved_callback = on_saved_callback
        self.dialog: Optional[ft.AlertDialog] = None

        # Input fields untuk General Config
        self.camera_index_field = self.create_text_field("Camera Index")
        self.preview_w_field = self.create_text_field("Preview Width (px)") 
        self.preview_h_field = self.create_text_field("Preview Height (px)")
        self.preview_q_field = self.create_text_field("Preview JPEG Quality (1-100)")

        self.crop_size_field = self.create_text_field("Crop Size (px)")
        self.crop_q_field = self.create_text_field("Crop JPEG Quality (1-100)")
        self.min_crop_field = self.create_text_field("Min Crop Size (px)")
        self.shutter_max_field = self.create_text_field("Shutter Display Max Side (px)")

        self.margin_top_field = self.create_text_field("Margin Top (<=5 ratio / >5 px)")
        self.margin_bottom_field = self.create_text_field("Margin Bottom")
        self.margin_left_field = self.create_text_field("Margin Left")
        self.margin_right_field = self.create_text_field("Margin Right")
        self.face_detect_max_field = self.create_text_field("Face Detect Max Side (px)")

        self.output_dir_field = self.create_text_field("Folder Output", expand=True)

        # Pose inputs (untuk Add / Edit)
        self.editing_pose_id: Optional[int] = None
        self.pose_code_field = ft.TextField(label="Kode", dense=True, width=100)
        self.pose_title_field = ft.TextField(label="Judul Pose", dense=True, expand=True)
        self.pose_desc_field = ft.TextField(label="Deskripsi Instruksi", dense=True, expand=True)

        self.poses_list_column = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO)

    def load_values(self) -> None:
        """Mengisi form dengan data terbaru dari database."""
        configs = db.get_all_configs()
        self.camera_index_field.value = str(configs.get("CAMERA_INDEX", 0))
        self.preview_w_field.value = str(configs.get("PREVIEW_WIDTH", 1280))
        self.preview_h_field.value = str(configs.get("PREVIEW_HEIGHT", 720))
        self.preview_q_field.value = str(configs.get("PREVIEW_JPEG_QUALITY", 75))

        self.crop_size_field.value = str(configs.get("CROP_SIZE", 640))
        self.crop_q_field.value = str(configs.get("CROP_JPEG_QUALITY", 100))
        self.min_crop_field.value = str(configs.get("MIN_CROP_SIZE", 200))
        self.shutter_max_field.value = str(configs.get("SHUTTER_DISPLAY_MAX_SIDE", 2400))

        self.margin_top_field.value = str(configs.get("FACE_MARGIN_TOP", 0.3))
        self.margin_bottom_field.value = str(configs.get("FACE_MARGIN_BOTTOM", 0.4))
        self.margin_left_field.value = str(configs.get("FACE_MARGIN_LEFT", 0.4))
        self.margin_right_field.value = str(configs.get("FACE_MARGIN_RIGHT", 0.4))
        self.face_detect_max_field.value = str(configs.get("FACE_DETECT_MAX_SIDE", 1000))

        self.output_dir_field.value = str(configs.get("OUTPUT_DIR", "foto_mahasiswa"))

        self.refresh_poses_list()

    async def choose_folder(self, _) -> None:
        """Membuka dialog pemilihan folder (kompatibel dengan Flet 1.0.5 Service & Linux zenity)."""
        selected_path: Optional[str] = None
        try:
            selected_path = await ft.FilePicker().get_directory_path(
                dialog_title="Pilih Folder Penyimpanan Foto Mahasiswa"
            )
        except Exception:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "zenity",
                    "--file-selection",
                    "--directory",
                    "--title=Pilih Folder Penyimpanan Foto Mahasiswa",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()
                if proc.returncode == 0 and stdout:
                    selected_path = stdout.decode("utf-8").strip()
            except Exception as exc:
                self.show_snack(f"Gagal membuka dialog folder: {exc}", is_error=True)
                return

        if selected_path:
            self.output_dir_field.value = selected_path
            self.output_dir_field.update()

    def create_text_field(self, label, width=None, expand=False):
        return ft.TextField(
            label=label,
            width=width,
            expand=expand,
            dense=True,
            text_size=17,
            label_style=ft.TextStyle(size=11),
            content_padding=ft.Padding.symmetric(
                horizontal=8,
                vertical=5,
            ),
            border=ft.OutlineInputBorder(
                border_radius=4,
            ),
        )    
        

    def refresh_poses_list(self) -> None:
        """Me-render ulang daftar pose dari database."""

        self.poses_list_column.controls.clear()

        poses = db.get_poses_raw()

        for p in poses:
            pose_id = p["id"]
            code = p["code"]
            title = p["title"]
            desc = p["description"]

            row = ft.Container(
                bgcolor="#F8FAFC",
                border=ft.Border.all(1, "#E2E8F0"),
                border_radius=8,
                padding=8,
                content=ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Text(
                                str(code),
                                weight=ft.FontWeight.BOLD,
                                color="#1E293B",
                            ),
                            width=40,
                            alignment=ft.Alignment.CENTER,
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    title,
                                    weight=ft.FontWeight.W_600,
                                    size=13,
                                    color="#1E293B",
                                ),
                                ft.Text(
                                    desc,
                                    size=11,
                                    color="#64748B",
                                ),
                            ],
                            expand=True,
                            spacing=2,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.EDIT_OUTLINED,
                            icon_size=18,
                            tooltip="Edit Pose",
                            on_click=lambda _, p_id=pose_id, c=code,
                                        t=title, d=desc:
                                self.start_edit_pose(p_id, c, t, d),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_size=18,
                            icon_color="#EF4444",
                            tooltip="Hapus Pose",
                            on_click=lambda _, p_id=pose_id:
                                self.delete_pose(p_id),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )

            self.poses_list_column.controls.append(row)

    def start_edit_pose(self, pose_id: int, code: str, title: str, desc: str) -> None:
        """Mengisi form edit pose dengan data yang dipilih."""
        self.editing_pose_id = pose_id
        self.pose_code_field.value = str(code)
        self.pose_title_field.value = title
        self.pose_desc_field.value = desc

        self.page.update()

    def cancel_edit_pose(self) -> None:
        """Mengosongkan input form pose."""

        self.editing_pose_id = None

        self.pose_code_field.value = ""
        self.pose_title_field.value = ""
        self.pose_desc_field.value = ""

        self.page.update()

    def save_or_update_pose(self) -> None:
        """Menyimpan pose baru atau mengupdate pose yang sedang diedit."""
        code = (self.pose_code_field.value or "").strip()
        title = (self.pose_title_field.value or "").strip()
        desc = (self.pose_desc_field.value or "").strip()

        if not code or not title:
            self.show_snack("Kode dan Judul Pose wajib diisi!", is_error=True)
            return

        if self.editing_pose_id is not None:
            db.update_pose(self.editing_pose_id, code, title, desc)
            self.show_snack("Pose berhasil diperbarui!")
        else:
            db.add_pose(code, title, desc)
            self.show_snack("Pose baru berhasil ditambahkan!")

        self.cancel_edit_pose()
        self.refresh_poses_list()

    def delete_pose(self, pose_id: int) -> None:
        """Menghapus pose berdasarkan ID."""
        db.delete_pose(pose_id)
        self.show_snack("Pose berhasil dihapus!")
        self.refresh_poses_list()

    def save_all_configs(self) -> None:
        """Memvalidasi dan menyimpan seluruh parameter konfigurasi umum ke SQLite."""
        try:
            out_dir_str = (self.output_dir_field.value or "foto_mahasiswa").strip()
            # Buat folder jika belum ada
            Path(out_dir_str).mkdir(parents=True, exist_ok=True)

            configs_to_update = {
                "CAMERA_INDEX": str(int(self.camera_index_field.value or 0)),
                "PREVIEW_WIDTH": str(int(self.preview_w_field.value or 1280)),
                "PREVIEW_HEIGHT": str(int(self.preview_h_field.value or 720)),
                "PREVIEW_JPEG_QUALITY": str(int(self.preview_q_field.value or 75)),
                "CROP_SIZE": str(int(self.crop_size_field.value or 640)),
                "CROP_JPEG_QUALITY": str(int(self.crop_q_field.value or 100)),
                "MIN_CROP_SIZE": str(int(self.min_crop_field.value or 200)),
                "SHUTTER_DISPLAY_MAX_SIDE": str(int(self.shutter_max_field.value or 2400)),
                "FACE_MARGIN_TOP": str(float(self.margin_top_field.value or 0.3)),
                "FACE_MARGIN_BOTTOM": str(float(self.margin_bottom_field.value or 0.4)),
                "FACE_MARGIN_LEFT": str(float(self.margin_left_field.value or 0.4)),
                "FACE_MARGIN_RIGHT": str(float(self.margin_right_field.value or 0.4)),
                "FACE_DETECT_MAX_SIDE": str(int(self.face_detect_max_field.value or 1000)),
                "OUTPUT_DIR": out_dir_str,
            }
            db.update_configs_bulk(configs_to_update)
            config.load_config_from_db()

            self.show_snack("Semua pengaturan berhasil disimpan!")
            if self.on_saved_callback:
                self.on_saved_callback()
            self.close_dialog()
        except ValueError as exc:
            self.show_snack(f"Kesalahan input angka: {exc}", is_error=True)
        except Exception as exc:
            self.show_snack(f"Gagal menyimpan pengaturan: {exc}", is_error=True)

    def handle_reset_default(self) -> None:
        """Mereset semua isi database ke nilai default."""

        db.reset_to_default()
        config.load_config_from_db()

        self.load_values()

        self.show_snack(
            "Konfigurasi dan Pose telah di-reset ke nilai default!"
        )

        if self.on_saved_callback:
            self.on_saved_callback()

    def show_snack(self, message: str, is_error: bool = False) -> None:
        snack = ft.SnackBar(
            content=ft.Text(message, color="#FFFFFF"),
            bgcolor="#EF4444" if is_error else "#16803C",
            open=True,
        )

        self.page.overlay.append(snack)
        self.page.update()

    def open_dialog(self) -> None:
        """Menampilkan dialog form konfigurasi."""
        self.load_values()

        # Layout Tab 1: Pengaturan Umum
        general_tab_content = ft.Container(
            padding=10,
            expand=True,
            content=ft.Column(
                scroll=ft.ScrollMode.AUTO,
                spacing=12,
                controls=[
                    ft.Text("Kamera & Live Preview", weight=ft.FontWeight.BOLD, color="#1E293B", size=14),
                    ft.Row([self.camera_index_field, self.preview_q_field]),
                    ft.Row([self.preview_w_field, self.preview_h_field]),
                    # ft.Divider(height=1),
                    ft.Text("Crop & Display", weight=ft.FontWeight.BOLD, color="#1E293B", size=14),
                    ft.Row([self.crop_size_field, self.crop_q_field]),
                    ft.Row([self.min_crop_field, self.shutter_max_field]),
                    # ft.Divider(height=1),
                    ft.Text("Deteksi Wajah", weight=ft.FontWeight.BOLD, color="#1E293B", size=14),
                    ft.Row([self.margin_top_field, self.margin_bottom_field]),
                    ft.Row([self.margin_left_field, self.margin_right_field]),
                    self.face_detect_max_field,
                    # ft.Divider(height=1),
                    ft.Text("Penyimpanan Foto Mahasiswa", weight=ft.FontWeight.BOLD, color="#1E293B", size=14),
                    ft.Row(
                        controls=[
                            self.output_dir_field,
                            ft.IconButton(
                                icon=ft.Icons.FOLDER_OPEN,
                                tooltip="Pilih Folder...",
                                icon_color="#1E3A8A",
                                on_click=self.choose_folder,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
            ),
        )
            
        # Layout Tab 2: CRUD Pose
        poses_tab_content = ft.Container(
            padding=10,
            expand=True,
            content=ft.Column(
                scroll=ft.ScrollMode.AUTO,
                spacing=10,
                controls=[
                    ft.Text("Form Tambah / Edit Pose", weight=ft.FontWeight.BOLD, color="#1E293B", size=14),
                    ft.Row([self.pose_code_field, self.pose_title_field]),
                    self.pose_desc_field,
                    ft.Row(
                        controls=[
                            ft.FilledButton(
                                "Simpan Pose",
                                icon=ft.Icons.CHECK,
                                on_click=lambda _: self.save_or_update_pose(),
                                style=ft.ButtonStyle(bgcolor="#1677E8", color="#FFFFFF"),
                            ),
                            ft.OutlinedButton(
                                "Batal Edit",
                                icon=ft.Icons.CLEAR,
                                on_click=lambda _: self.cancel_edit_pose(),
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Divider(height=1),
                    ft.Text("Daftar Pose Aktif", weight=ft.FontWeight.BOLD, color="#1E293B", size=14),
                    ft.Container(
                        height=250,
                        content=self.poses_list_column,
                    ),
                ],
            ),
        )

        general_tab_content.visible = True
        poses_tab_content.visible = False

        def on_tab_change(e):
            index = e.control.selected_index
            general_tab_content.visible = index == 0
            poses_tab_content.visible = index == 1

            self.page.update()

        tabs = ft.Tabs(
            length=2,
            selected_index=0,
            on_change=on_tab_change,
            content=ft.Column(
                spacing=10,
                expand=True,
                controls=[
                    ft.TabBar(
                        tabs=[
                            ft.Tab(
                                label="Pengaturan Umum",
                                icon=ft.Icons.TUNE,
                            ),
                            ft.Tab(
                                label="Daftar Pose Wajah",
                                icon=ft.Icons.FACE,
                            ),
                        ],
                    ),
                    poses_tab_content,
                    general_tab_content,
                    
                ],
            ),
            expand=True,
        )

        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.SETTINGS, color="#1677E8"),
                    ft.Text("Konfigurasi Aplikasi & Pose", weight=ft.FontWeight.BOLD, size=18),
                ],
                spacing=8,
            ),
            content=ft.Container(
                width=650,
                height=450,
                content=tabs,
            ),
            actions=[
                ft.TextButton(
                    "Reset ke Default",
                    icon=ft.Icons.RESTORE,
                    icon_color="#DC2626",
                    on_click=lambda _: self.handle_reset_default(),
                ),
                ft.FilledButton(
                    "Simpan Pengaturan",
                    icon=ft.Icons.SAVE,
                    on_click=lambda _: self.save_all_configs(),
                    style=ft.ButtonStyle(bgcolor="#16803C", color="#FFFFFF"),
                ),
                ft.OutlinedButton("Tutup", on_click=lambda _: self.close_dialog()),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.show_dialog(self.dialog)

    def close_dialog(self) -> None:
        if self.dialog is not None:
            self.page.pop_dialog()

