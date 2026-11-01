"""Entry point aplikasi Pengambilan Foto Mahasiswa Flet."""

import asyncio
from pathlib import Path
from typing import List, Optional

import flet as ft

from app.camera_preview import CameraPreviewManager
from app import config
from app.config import CAMERA_INDEX, CROP_SIZE, POSES
from app.shutter import capture_to_memory, detect_camera
from app.storage import (
    get_crop_file_path,
    get_student_dir,
    sanitize_nim,
    save_student_data,
)
from app.ui import AppUI


def main(page: ft.Page):
    page.title = "Aplikasi Pengambilan Foto Mahasiswa"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 18
    page.bgcolor = "#F3F6FB"
    page.scroll = ft.ScrollMode.AUTO

    try:
        page.window.width = 1280
        page.window.height = 940
    except Exception:
        pass

    preview_manager = CameraPreviewManager(camera_index=CAMERA_INDEX)
    captured_paths: List[Optional[str]] = [None] * len(POSES)
    preview_task_handle: Optional[asyncio.Task] = None
    pending_pose: Optional[int] = None  # pose yang fotonya sedang menunggu crop di tab hasil shutter
    capturing = False

    async def preview_loop():
        last_seq = 0
        while preview_manager.is_running:
            try:
                seq, frame_bytes = preview_manager.get_latest_frame()
                if frame_bytes and seq != last_seq:
                    ui.update_preview_frame(frame_bytes)
                    last_seq = seq
            except Exception as exc:
                print(f"[PreviewLoop] Exception: {exc}")
            await asyncio.sleep(0.033)

    async def on_camera_toggle():
        nonlocal preview_task_handle
        if preview_manager.is_running:
            preview_manager.stop()
            ui.set_camera_state(False)
            ui.notify("Preview kamera dihentikan.", "#64748B")
            return

        ui.notify("Memeriksa koneksi kamera gphoto2...", "#64748B")
        detected, msg = await asyncio.to_thread(detect_camera, 15)
        if not detected:
            ui.notify(f"Gagal mengaktifkan kamera: {msg}", "#B91C1C")
            return

        preview_manager.start()
        ui.set_camera_state(True)
        ui.notify("Kamera aktif. Menampilkan live video preview...", "#16803C")
        page.run_task(preview_loop)

    async def on_capture_pose(index: int):
        nonlocal pending_pose, capturing
        if capturing:
            ui.notify("Pengambilan foto sebelumnya masih berjalan.", "#B45309")
            return

        if not preview_manager.is_running:
            ui.notify("Aktifkan kamera terlebih dahulu dengan Camera On.", "#B45309")
            return

        nim_val = ui.get_nim()
        safe_nim = sanitize_nim(nim_val)
        if not safe_nim:
            ui.notify("Isi NIM terlebih dahulu sebelum mengambil foto.", "#B45309")
            return

        # Folder NIM baru dibuat saat foto di-crop & disimpan
        student_dir = get_student_dir(safe_nim, create=False)
        if not student_dir:
            ui.notify("NIM tidak valid.", "#B45309")
            return

        pose_title = POSES[index][1]
        crop_dest = get_crop_file_path(student_dir, index)

        capturing = True
        try:
            ui.notify(f"Mengambil foto pose {index + 1}: {pose_title}...", "#64748B")

            # Ambil foto asli lewat gphoto2 langsung ke memori (non-blocking, tanpa file sementara)
            jpeg_bytes, msg = await asyncio.to_thread(capture_to_memory, 90)

            # Pulihkan stream capture card OpenCV setelah shutter kamera
            preview_manager.request_reopen()

            if jpeg_bytes is None:
                ui.notify(f"Gagal mengambil foto: {msg}", "#B91C1C")
                return

            ui.notify(f"Foto pose {index + 1} diterima. Mendeteksi wajah...", "#64748B")
            pending_pose = index
            try:
                auto_saved = await ui.show_shutter_photo(
                    jpeg_bytes, f"{index + 1}. {pose_title}", crop_dest
                )
            except ValueError as val_err:
                pending_pose = None
                ui.notify(f"Kesalahan foto: {val_err}", "#B91C1C")
                return
            except Exception as exc:
                pending_pose = None
                ui.notify(f"Gagal menampilkan hasil shutter: {exc}", "#B91C1C")
                return

            if auto_saved:
                ui.notify(
                    f"Wajah terdeteksi! Foto pose {index + 1} otomatis di-crop ({CROP_SIZE}x{CROP_SIZE} px), "
                    "disimpan, dan ditampilkan di thumbnail pose sebagai referensi.",
                    "#16803C",
                )
            else:
                ui.notify(
                    f"Wajah tidak terdeteksi pada pose {index + 1}. "
                    "Atur kotak di tab Hasil Shutter & Crop lalu klik Crop & Simpan Foto.",
                    "#B45309",
                )
        finally:
            capturing = False

    def ensure_captured_paths_capacity(min_len: int):
        while len(captured_paths) < min_len:
            captured_paths.append(None)

    def on_crop_saved(saved_path: Path):
        nonlocal pending_pose
        index = pending_pose
        if not ui.crop_panel.has_photo:
            pending_pose = None
        if index is None:
            return
        ensure_captured_paths_capacity(index + 1)
        captured_paths[index] = str(saved_path)
        ui.set_pose_thumbnail(index, saved_path)
        pose_label = config.POSES[index][1] if index < len(config.POSES) else f"Pose {index + 1}"
        ui.notify(
            f"Foto pose {index + 1} ({pose_label}) tersimpan ({config.CROP_SIZE}x{config.CROP_SIZE} px).",
            "#16803C",
        )

    def on_crop_cancel():
        nonlocal pending_pose
        index = pending_pose
        pending_pose = None
        if index is not None:
            existing = captured_paths[index]
            if existing:
                try:
                    Path(existing).unlink(missing_ok=True)
                except Exception:
                    pass
            captured_paths[index] = None
            ui.reset_pose_thumbnail(index)
            ui.notify(f"Pengambilan foto pose {index + 1} dibatalkan.", "#64748B")

    # def on_cancle_save():
    #     ui.tampilkan_pesan("Apakah Anda yakin ingin membatalkan data?")

    def on_save_data():
        nim_val = ui.get_nim()
        safe_nim = sanitize_nim(nim_val)
        if not safe_nim:
            ui.notify("NIM wajib diisi sebelum menyimpan data.", "#B45309")
            return

        student_dir = get_student_dir(safe_nim, create=True)
        form_values = ui.get_form_values()
        photo_dict = {
            config.POSES[i][1]: (captured_paths[i] if i < len(captured_paths) else None)
            for i in range(len(config.POSES))
        }

        try:
            target_json = save_student_data(
                student_dir=student_dir,
                nim=safe_nim,
                form_values=form_values,
                captured_paths=photo_dict,
            )
            ui.notify(f"Data mahasiswa berhasil disimpan di {target_json}", "#16803C")
        except Exception as exc:
            ui.notify(f"Gagal menyimpan data mahasiswa: {exc}", "#B91C1C")

    ui = AppUI(
        page=page,
        on_camera_toggle=lambda: page.run_task(on_camera_toggle),
        on_capture_pose=lambda idx: page.run_task(on_capture_pose, idx),
        on_save_data=on_save_data,
        on_crop_saved=on_crop_saved,
        on_crop_cancel=on_crop_cancel,
        # on_cancle_save = on_cancle_save
    )

    page.add(ui.build_layout())
    ui.rebuild_pose_cards()
    ui._layout_ready = True

if __name__ == "__main__":
    ft.run(main)

