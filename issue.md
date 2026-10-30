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
│   ├── config.py        # konstanta: daftar pose, index kamera, resolusi, margin wajah, folder output
│   ├── camera_preview.py# thread OpenCV: buka capture card, baca frame, buat JPEG
│   ├── shutter.py       # wrapper gphoto2: deteksi kamera & ambil foto langsung ke memori (tanpa file)
│   ├── crop_panel.py    # isi tab "Hasil Shutter & Crop": foto shutter, kotak 640x640, auto-fit wajah, geser/resize/zoom
│   ├── image_utils.py   # decode foto, deteksi wajah (Haar Cascade), hitung kotak crop, crop persegi
│   ├── storage.py       # path folder per NIM, simpan JSON data mahasiswa
│   └── ui.py            # susunan komponen Flet
└── foto_mahasiswa/      # output (jangan di-commit)
```

## Fitur yang Harus Ada
1. **Form data mahasiswa**: NIM, Nama, Alamat, Kode/Nama Prodi, Kode/Nama Fakultas, Kode/Nama Institusi.
2. **Live preview** (tab pertama pada tab panel; tab kedua: Hasil Shutter & Crop, lihat poin 5):
   - Tombol Camera On/Off.
   - Preview berjalan di thread terpisah supaya UI tidak macet.
   - Jika frame gagal dibaca, buka ulang capture card secara otomatis.
3. **7 pose foto** dengan kartu per pose: Dengak, Nunduk, Lurus, Kiri 20°, Kiri 30°, Kanan 20°, Kanan 30°. Setiap kartu punya instruksi singkat, tombol "Ambil foto", dan thumbnail hasil.
4. **Shutter via gphoto2**:
   - Cek apakah gphoto2 terpasang dan kamera terdeteksi sebelum preview dinyalakan.
   - Ambil foto asli **langsung ke memori** (`gphoto2 --capture-image-and-download --stdout`), **tanpa file sementara** di disk dan belum ke folder NIM.
   - Setelah shutter, **buka ulang stream preview**, karena capture card bisa terputus sesaat.
5. **Tab panel "Hasil Shutter & Crop"** (menggantikan dialog crop manual; fungsi dan kodenya dipindahkan menjadi tab pada panel live preview):
   - Panel live preview memakai **tab panel** dengan dua tab: **Live Preview** dan **Hasil Shutter & Crop**.
   - Setelah foto asli diterima dari tombol "Ambil foto", foto **langsung tampil di tab Hasil Shutter & Crop** (tab berpindah otomatis, tanpa dialog). Stream live preview **tidak dihentikan dan tidak digantikan**: tetap berjalan di tab Live Preview.
   - Foto hasil shutter **tidak disimpan sementara** di disk. Foto dipegang di memori sampai di-crop atau dibatalkan.
   - Di atas foto ada **kotak crop (rectangle) persegi** (dalam piksel foto asli, bukan piksel layar) dengan **ukuran default 640x640 px**.
   - **Deteksi wajah otomatis** (OpenCV Haar Cascade, dijalankan di thread terpisah) berjalan begitu foto diterima:
     - **Posisi wajah berada di tengah kotak** dengan memperhitungkan margin atas, bawah, kiri, dan kanan yang diatur lewat konstanta di `app/config.py`: `FACE_MARGIN_TOP`, `FACE_MARGIN_BOTTOM`, `FACE_MARGIN_LEFT`, dan `FACE_MARGIN_RIGHT` (mendukung rasio terhadap ukuran wajah jika `<= 5.0` atau piksel langsung jika `> 5.0`).
     - Kotak **menyesuaikan ukuran dengan area wajah + margin** (`max(lebar_wajah + margin_kiri + margin_kanan, tinggi_wajah + margin_atas + margin_bawah)`). Jika wajah dekat tepi foto, kotak dikunci agar tidak keluar dari batas foto.
     - **Crop & simpan otomatis saat wajah terdeteksi**: jika wajah terdeteksi, sistem langsung melakukan **crop otomatis (640x640 px)**, **menyimpan foto sesuai aturan** ke folder NIM (`foto_mahasiswa/<NIM>/<pose>.jpg`), dan **menampilkan hasilnya pada image thumbnail kartu pose sebagai referensi**. Foto dan kotak crop tetap tampil di tab **Hasil Shutter & Crop** bila user ingin mengoreksi manual.
     - Jika wajah tidak terdeteksi, kotak tetap 640x640 di tengah foto dan tampil pesan agar user mengatur manual.
     - Tombol **Deteksi Wajah** untuk mengulang deteksi dan menyesuaikan kotak kembali tanpa merubah ukuran rectangle jika sebelumnya sudah di perbesar atau di perkecil, sekaligus memperbarui hasil crop otomatis dan thumbnail referensi.
   - Penyesuaian manual tetap tersedia:
     - Geser kotak (drag, klik, atau tombol panah). Kotak tidak boleh keluar dari batas foto.
     - Resize kotak dengan rasio 1:1 (tarik sudut kanan-bawah, tombol +/-, atau "Reset 640px").
     - Foto dapat diperbesar maupun diperkecil (zoom).
   - Tombol **Crop & Simpan Foto**: potong area kotak dari foto asli resolusi penuh, skalakan ke tepat **640x640 px**, simpan/perbarui ke folder NIM, kembali ke tab Live Preview, lalu perbarui thumbnail di kartu pose.
   - Tombol **Batal / Ulangi**: buang foto dari memori (dan hapus file auto-save pose tersebut jika sempat tersimpan otomatis), kembali ke tab Live Preview, kartu pose tetap kosong.
   - Jika resolusi foto asli lebih kecil dari 640x640, tampilkan pesan error dan jangan tampilkan foto di tab.
   - Penggeseran/resize kotak boleh memakai komponen Flet (mis. `GestureDetector` di atas `Stack`), atau cara lain yang lebih sederhana. Yang penting hasil crop tepat sesuai area yang terlihat di kotak.
6. **Simpan data**: tulis `data_mahasiswa.json` di folder NIM (data form, waktu simpan, path ke-7 foto).

## Aturan Penting
- NIM wajib diisi sebelum foto diambil atau data disimpan. Bersihkan NIM agar aman dipakai sebagai nama folder.
- Semua operasi lambat (gphoto2, membaca/menulis gambar) tidak boleh memblokir UI.
- Tampilkan pesan status yang jelas untuk setiap error: gphoto2 tidak ada, kamera tidak terdeteksi, resolusi foto terlalu kecil, timeout.
- Folder NIM **hanya berisi foto yang sudah di-crop**. Foto asli tidak pernah ditulis ke disk, jadi foto yang batal di-crop tidak meninggalkan file apa pun.
- Deteksi wajah dan penyimpanan hasil crop berjalan di thread terpisah (`asyncio.to_thread`) agar UI dan live preview tidak macet.
- Tidak boleh ada dua perintah gphoto2 berjalan bersamaan (pakai lock).

## Hal yang Perlu Diperbaiki dari Referensi
- Referensi memakai crop wajah otomatis (Haar Cascade) dan nama file `_460x460` padahal ukurannya 640. Di project baru hasil crop selalu **640x640** (konstanta `CROP_SIZE` di `config.py`) dan nama file tidak memuat ukuran yang salah. Haar Cascade dipakai untuk mendeteksi wajah pada foto hasil shutter, menyesuaikan kotak crop beserta margin (`FACE_MARGIN_TOP`, `FACE_MARGIN_BOTTOM`, `FACE_MARGIN_LEFT`, `FACE_MARGIN_RIGHT`), melakukan auto-crop dan menyimpannya ke folder NIM serta menampilkannya pada thumbnail pose sebagai referensi; user tetap dapat mengubah kotak secara manual di tab.
- Fungsi `process_preview` (deteksi wajah pada live preview) tidak dipakai. Hapus saja. Deteksi wajah hanya dijalankan pada foto hasil shutter.
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
8. Buat `crop_panel.py` sebagai isi tab "Hasil Shutter & Crop": tampilkan foto dari memori, kotak 640x640 yang bisa digeser/di-resize, auto-fit ke wajah (wajah di tengah kotak dengan margin atas/bawah/kiri/kanan), auto-crop & simpan ke thumbnail referensi, serta tombol Crop dan Batal. Uji dulu dengan foto contoh tanpa kamera.
9. Hubungkan alur lengkap: Camera On → ambil foto per pose (langsung ke memori) → foto tampil di tab Hasil Shutter & Crop dengan kotak auto-fit wajah + auto-crop & thumbnail referensi → koreksi/klik Crop & Simpan Foto → simpan data.
10. Tulis `README.md` (cara instal, cara jalan, troubleshooting).

## Kriteria Selesai
- [x] `pip install -r requirements.txt` berhasil di environment baru dan `opencv-python` bernomor versi `4.10.0.84`.
- [x] `python3 main.py` membuka aplikasi tanpa error.
- [x] Preview live tampil dan tetap pulih setelah mengambil foto.
- [x] Setelah foto diambil, tab **Hasil Shutter & Crop** tampil otomatis berisi foto asli dan kotak crop, tanpa menghentikan live preview.
- [x] Tidak ada file foto asli/sementara yang ditulis ke disk saat shutter (folder `temp_captures/` tidak dipakai).
- [x] Jika wajah terdeteksi, kotak menyesuaikan ukuran dengan wajah + margin (`FACE_MARGIN_TOP`, `FACE_MARGIN_BOTTOM`, `FACE_MARGIN_LEFT`, `FACE_MARGIN_RIGHT`) dengan wajah di tengah kotak, lalu otomatis di-crop (640x640), disimpan ke folder NIM, dan ditampilkan di image thumbnail kartu pose sebagai referensi. Jika tidak terdeteksi, kotak default 640x640 di tengah foto.
- [x] Kotak bisa digeser, di-resize (1:1), dan tidak bisa keluar dari batas foto; tombol **Deteksi Wajah** mempertahankan ukuran kotak jika sebelumnya sudah diubah manual.
- [x] Klik **Crop & Simpan Foto** menghasilkan gambar tepat 640x640 sesuai area kotak, kembali ke tab Live Preview, dan thumbnail pose tampil.
- [x] Klik **Batal / Ulangi** tidak meninggalkan file hasil pose yang dibatalkan di folder NIM dan mengosongkan kembali thumbnail kartu pose.
- [x] Folder `foto_mahasiswa/<NIM>/` berisi 7 foto hasil crop (640x640) dan `data_mahasiswa.json`.
- [x] Semua kondisi error menampilkan pesan yang jelas, dan aplikasi tidak crash.

## Di Luar Cakupan
- Integrasi database (rencana tahap berikutnya).
- Dukungan Windows/macOS.
