"""Manajemen penyimpanan folder mahasiswa dan file JSON."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.config import OUTPUT_DIR, POSES, TEMP_DIR


def sanitize_nim(nim: Optional[str]) -> Optional[str]:
    """Membersihkan NIM agar aman digunakan sebagai nama direktori."""
    if not nim:
        return None
    cleaned = "".join(c for c in nim.strip() if c.isalnum() or c in "-_")
    return cleaned if cleaned else None


def get_student_dir(nim: Optional[str], create: bool = True) -> Optional[Path]:
    """Mengembalikan direktori output mahasiswa berdasarkan NIM."""
    safe_nim = sanitize_nim(nim)
    if not safe_nim:
        return None
    folder = OUTPUT_DIR / safe_nim
    if create:
        folder.mkdir(parents=True, exist_ok=True)
    return folder


def get_temp_file(safe_nim: str, pose_index: int) -> Path:
    """Mengembalikan path file sementara untuk foto asli sebelum di-crop."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    title = POSES[pose_index][1].lower().replace(" ", "_")
    return TEMP_DIR / f"temp_{safe_nim}_{pose_index + 1:02d}_{title}.jpg"


def get_crop_file_path(student_dir: Path, pose_index: int) -> Path:
    """Mengembalikan path tujuan file crop 640x640 di dalam folder mahasiswa."""
    title = POSES[pose_index][1].lower().replace(" ", "_")
    return student_dir / f"{pose_index + 1:02d}_{title}.jpg"


def cleanup_file(path: Optional[Path]) -> None:
    """Menghapus file sementara jika ada."""
    if path and path.exists():
        try:
            path.unlink()
        except OSError:
            pass


def save_student_data(
    student_dir: Path,
    nim: str,
    form_values: Dict[str, str],
    captured_paths: Dict[str, Optional[str]],
) -> Path:
    """Menyimpan data_mahasiswa.json ke folder mahasiswa."""
    data: Dict[str, Any] = {
        "nim": nim.strip(),
        "nama": form_values.get("nama", "").strip(),
        "alamat": form_values.get("alamat", "").strip(),
        "kode_prodi": form_values.get("kode_prodi", "").strip(),
        "nama_prodi": form_values.get("nama_prodi", "").strip(),
        "kode_fakultas": form_values.get("kode_fakultas", "").strip(),
        "nama_fakultas": form_values.get("nama_fakultas", "").strip(),
        "kode_institusi": form_values.get("kode_institusi", "").strip(),
        "nama_institusi": form_values.get("nama_institusi", "").strip(),
        "waktu_simpan": datetime.now().isoformat(timespec="seconds"),
        "foto": captured_paths,
    }

    target_json = student_dir / "data_mahasiswa.json"
    with open(target_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return target_json

