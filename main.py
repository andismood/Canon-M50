"""Entry point aplikasi Pengambilan Foto Mahasiswa Flet."""

import asyncio
from typing import List, Optional

import flet as ft

from app.camera_preview import CameraPreviewManager
from app.config import CAMERA_INDEX, POSES
from app.crop_dialog import ManualCropDialog
from app.shutter import capture_and_download, detect_camera
from app.storage import (
    cleanup_file,
    get_crop_file_path,
    get_student_dir,
    get_temp_file,
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
        page.window.width = 1450
        page.window.height = 940
    except Exception:
        pass

    preview_manager = CameraPreviewManager(camera_index=CAMERA_INDEX)
    captured_paths: List[Optional[str]] = [None] * len(POSES)
    preview_task_handle: Optional[asyncio.Task] = None

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
        if not preview_manager.is_running:
            ui.notify("Aktifkan kamera terlebih dahulu dengan Camera On.", "#B45309")
            return

        nim_val = ui.get_nim()
        safe_nim = sanitize_nim(nim_val)
        if not safe_nim:
            ui.notify("Isi NIM terlebih dahulu sebelum mengambil foto.", "#B45309")
            return

        student_dir = get_student_dir(safe_nim, create=True)
        if not student_dir:
            ui.notify("NIM tidak valid.", "#B45309")
            return

        pose_title = POSES[index][1]
        temp_dest = get_temp_file(safe_nim, index)
        crop_dest = get_crop_file_path(student_dir, index)

        ui.notify(f"Mengambil foto pose {index + 1}: {pose_title}...", "#64748B")

        # Ambil foto asli lewat gphoto2 (non-blocking)
        success, msg = await asyncio.to_thread(capture_and_download, temp_dest, 90)

        # Pulihkan stream capture card OpenCV setelah shutter kamera
        preview_manager.request_reopen()

        if not success or not temp_dest.exists():
            cleanup_file(temp_dest)
            ui.notify(f"Gagal mengambil foto: {msg}", "#B91C1C")
            return

        ui.notify(f"Foto asli pose {index + 1} berhasil diambil. Silakan lakukan crop.", "#16803C")

        # Buka dialog crop manual
        def on_crop_success(saved_crop_path):
            captured_paths[index] = str(saved_crop_path)
            cleanup_file(temp_dest)
            ui.set_pose_thumbnail(index, saved_crop_path)
            ui.notify(
                f"Foto pose {index + 1} ({pose_title}) tersimpan (640x640 px).",
                "#16803C",
            )

        def on_crop_cancel():
            cleanup_file(temp_dest)
            ui.notify(f"Pengambilan foto pose {index + 1} dibatalkan.", "#64748B")

        try:
            crop_dialog = ManualCropDialog(
                page=page,
                source_image_path=temp_dest,
                destination_path=crop_dest,
                pose_title=f"{index + 1}. {pose_title}",
                on_success=on_crop_success,
                on_cancel=on_crop_cancel,
            )
            crop_dialog.show()
        except ValueError as val_err:
            cleanup_file(temp_dest)
            ui.notify(f"Kesalahan dimensi foto: {val_err}", "#B91C1C")
        except Exception as exc:
            cleanup_file(temp_dest)
            ui.notify(f"Gagal membuka dialog crop: {exc}", "#B91C1C")

    def on_save_data():
        nim_val = ui.get_nim()
        safe_nim = sanitize_nim(nim_val)
        if not safe_nim:
            ui.notify("NIM wajib diisi sebelum menyimpan data.", "#B45309")
            return

        student_dir = get_student_dir(safe_nim, create=True)
        form_values = ui.get_form_values()
        photo_dict = {POSES[i][1]: captured_paths[i] for i in range(len(POSES))}

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
    )

    page.add(ui.build_layout())


if __name__ == "__main__":
    ft.run(main)

