# Issue: Project Baru Aplikasi Foto Wajah Mahasiswa (Flet + OpenCV + gphoto2)

## Tujuan
Membuat project baru di folder ini dengan **Python 3 + Flet**. Aplikasi desktop (Linux) ini mengambil **7 foto wajah mahasiswa** dengan pose berbeda dan menyimpan data mahasiswa.

- Preview live berasal dari HDMI capture card, dibaca dengan OpenCV.
- Foto asli diambil dengan shutter kamera lewat gphoto2 (USB).

Referensi perilaku: [main_opencv_preview_gphoto2_shutter.py](file:///home/smood/fletProject/main_opencv_preview_gphoto2_shutter.py). File ini hanya **referensi**. Jangan disalin mentah-mentah. Susun ulang kodenya agar lebih rapi.

## Dependency
| Dependency | Keterangan |
|---|---|
| Python 3 | Gunakan virtual environment baru, mis. `.venv` |
| `flet` | UI desktop. Gunakan versi yang sama dengan referensi (1.0.5) |
| `opencv-python==4.10.0.84` | **Versi harus persis ini** |
| `gphoto2` | Program CLI sistem (`sudo apt install gphoto2`), dipanggil lewat paket Python gphoto2 (binding), seperti di referensi |

Catat semua dependency Python di `requirements.txt`. Catat prasyarat sistem (gphoto2) di `README.md`.

## Struktur Project (usulan)
Pisahkan tanggung jawab ke beberapa modul kecil, jangan satu file besar:

```
fletProject/
├── main.py              # entry point Flet
├── requirements.txt
├── README.md
├── app/
│   ├── config.py        # konstanta: daftar pose, index kamera, resolusi, folder output
│   ├── camera_preview.py# thread OpenCV: buka capture card, baca frame, buat JPEG
│   ├── shutter.py       # wrapper gphoto2: deteksi kamera & ambil foto
│   ├── crop_dialog.py   # dialog crop manual (kotak 640x640 yang bisa digeser)
│   ├── image_utils.py   # fungsi crop gambar sesuai koordinat kotak
│   ├── storage.py       # path folder per NIM, simpan JSON data mahasiswa
│   └── ui.py            # susunan komponen Flet
└── foto_mahasiswa/      # output (jangan di-commit)
```

## Fitur yang Harus Ada
1. **Form data mahasiswa**: NIM, Nama, Alamat, Kode/Nama Prodi, Kode/Nama Fakultas, Kode/Nama Institusi.
2. **Live preview**:
   - Tombol Camera On/Off.
   - Preview berjalan di thread terpisah supaya UI tidak macet.
   - Jika frame gagal dibaca, buka ulang capture card secara otomatis.
3. **7 pose foto** dengan kartu per pose: Dengak, Nunduk, Lurus, Kiri 20°, Kiri 30°, Kanan 20°, Kanan 30°. Setiap kartu punya instruksi singkat, tombol "Ambil foto", dan thumbnail hasil.
4. **Shutter via gphoto2**:
   - Cek apakah gphoto2 terpasang dan kamera terdeteksi sebelum preview dinyalakan.
   - Ambil foto asli dan simpan **sementara** (folder temp), belum ke folder NIM.
   - Setelah shutter, **buka ulang stream preview**, karena capture card bisa terputus sesaat.
5. **Dialog crop manual** (muncul otomatis setelah foto asli berhasil diambil):
   - Tampilkan foto asli di dalam dialog.
   - Di atas foto ada **kotak crop (rectangle) berukuran tetap 640x640 px** (dalam piksel foto asli, bukan piksel layar). Ukuran kotak tidak bisa diubah.
   - gambar asli yang ada di dialog dapat di perbesar maupun di perkecil
   - User menggeser kotak untuk memilih area wajah. Kotak tidak boleh keluar dari batas foto.
   - Tombol **Crop**: potong foto sesuai kotak, simpan hasilnya ke folder NIM, tutup dialog, lalu tampilkan thumbnail di kartu pose.
   - Tombol **Batal / Ulangi**: tutup dialog tanpa menyimpan. Foto sementara dibuang dan kartu pose tetap kosong.
   - Jika resolusi foto asli lebih kecil dari 640x640, tampilkan pesan error dan jangan buka dialog.
   - Penggeseran kotak boleh memakai komponen Flet (mis. `GestureDetector` di atas `Stack`), atau cara lain yang lebih sederhana. Yang penting hasil crop tepat sesuai area yang terlihat di kotak.
6. **Simpan data**: tulis `data_mahasiswa.json` di folder NIM (data form, waktu simpan, path ke-7 foto).

## Aturan Penting
- NIM wajib diisi sebelum foto diambil atau data disimpan. Bersihkan NIM agar aman dipakai sebagai nama folder.
- Semua operasi lambat (gphoto2, membaca/menulis gambar) tidak boleh memblokir UI.
- Tampilkan pesan status yang jelas untuk setiap error: gphoto2 tidak ada, kamera tidak terdeteksi, resolusi foto terlalu kecil, timeout.
- Folder NIM **hanya berisi foto yang sudah di-crop**. Foto asli yang batal di-crop tidak boleh tertinggal di folder NIM.
- Tidak boleh ada dua perintah gphoto2 berjalan bersamaan (pakai lock).

## Hal yang Perlu Diperbaiki dari Referensi
- Referensi memakai crop wajah otomatis (Haar Cascade) dan nama file `_460x460` padahal ukurannya 640. Di project baru **crop dilakukan manual** dengan ukuran tetap 640x640, disimpan sebagai konstanta di `config.py`, dan nama file tidak memuat ukuran yang salah.
- Fungsi `process_preview` (deteksi wajah di preview) tidak dipakai. Hapus saja.
- Docstring referensi menyebut `main.py`, sedangkan nama file berbeda. Samakan.
- Hapus kode yang di-comment dan impor yang tidak terpakai.

## Langkah Pengerjaan
1. Buat virtual environment baru, `requirements.txt`, dan kerangka folder.
2. Pasang dependency dan pastikan `import flet` dan `import cv2` berjalan.
3. Buat `config.py` dan `storage.py` (paling sederhana, mudah dites).
4. Buat `shutter.py` dan uji manual dengan kamera: `gphoto2 --auto-detect` lalu ambil 1 foto.
5. Buat `camera_preview.py` dan uji dengan skrip kecil (tampilkan frame di window OpenCV).
6. Buat `image_utils.py` (fungsi crop 640x640 dari koordinat) dan uji dengan 1 foto contoh.
7. Rakit UI di `ui.py` dan `main.py`: form, preview, kartu pose.
8. Buat `crop_dialog.py`: tampilkan foto, kotak 640x640 yang bisa digeser, tombol Crop dan Batal. Uji dulu dengan foto contoh tanpa kamera.
9. Hubungkan alur lengkap: Camera On → ambil foto per pose (file sementara) → dialog crop manual → klik Crop → simpan ke folder NIM → thumbnail → simpan data.
10. Tulis `README.md` (cara instal, cara jalan, troubleshooting).

## Kriteria Selesai
- [x] `pip install -r requirements.txt` berhasil di environment baru dan `opencv-python` bernomor versi `4.10.0.84`.
- [x] `python3 main.py` membuka aplikasi tanpa error.
- [x] Preview live tampil dan tetap pulih setelah mengambil foto.
- [x] Setelah foto diambil, dialog crop muncul dengan foto asli dan kotak 640x640.
- [x] Kotak bisa digeser dan tidak bisa keluar dari batas foto.
- [x] Klik **Crop** menghasilkan gambar tepat 640x640 sesuai area kotak, dan thumbnail pose tampil.
- [x] Klik **Batal** tidak menyimpan apa pun ke folder NIM.
- [x] Folder `foto_mahasiswa/<NIM>/` berisi 7 foto hasil crop (640x640) dan `data_mahasiswa.json`.
- [x] Semua kondisi error menampilkan pesan yang jelas, dan aplikasi tidak crash.

## Di Luar Cakupan
- Integrasi database (rencana tahap berikutnya).
- Dukungan Windows/macOS.

