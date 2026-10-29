# Aplikasi Pengambilan 7 Foto Wajah Mahasiswa

Aplikasi desktop berbasis **Python 3 + Flet** untuk pengambilan 7 foto wajah mahasiswa dengan pose berbeda, live video preview dari HDMI capture card via OpenCV, shutter kamera Canon/DSLR via USB menggunakan gphoto2, serta fitur **dialog crop manual persegi 640x640 px** dengan kemampuan zoom dan pergeseran kotak sebelum disimpan ke folder mahasiswa.

---

## Fitur Utama
1. **Formulir Data Mahasiswa**: Input NIM, Nama Lengkap, Alamat, Kode/Nama Prodi, Kode/Nama Fakultas, dan Kode/Nama Institusi.
2. **Live Video Preview (OpenCV)**: Streaming video real-time dari HDMI capture card (V4L2) dengan pemulihan otomatis stream jika terputus.
3. **Pengambilan 7 Pose Wajah**:
   - Pose 1: Dengak (dagu sedikit ke atas)
   - Pose 2: Nunduk (dagu sedikit ke bawah)
   - Pose 3: Lurus (hadap ke depan)
   - Pose 4: Ke kiri 20 derajat
   - Pose 5: Ke kiri 30 derajat
   - Pose 6: Ke kanan 20 derajat
   - Pose 7: Ke kanan 30 derajat
4. **Shutter USB via gphoto2**: Mengambil foto resolusi tinggi langsung dari kamera Canon/DSLR.
5. **Dialog Crop Manual (640x640 px)**:
   - Muncul otomatis setelah shutter berhasil.
   - Kotak crop berukuran tetap 640x640 px (dalam piksel foto asli).
   - Tampilan foto dapat diperbesar (Zoom In) atau diperkecil (Zoom Out).
   - Kotak dapat digeser dengan drag mouse, klik pada area wajah, atau menggunakan tombol navigasi panah.
   - Kotak dibatasi agar tidak pernah keluar dari batas foto.
   - Tombol **Crop & Simpan Foto** menyimpan hasil potong ke folder mahasiswa dan memperbarui thumbnail kartu pose.
   - Tombol **Batal / Ulangi** membatalkan proses crop tanpa meninggalkan sampah file.
6. **Penyimpanan Terstruktur**: Data mahasiswa beserta path 7 foto disimpan ke `data_mahasiswa.json` di folder `foto_mahasiswa/<NIM>/`.

---

## Prasyarat Sistem
Aplikasi diuji dan ditargetkan untuk Linux (Ubuntu/Debian) dengan kamera (mis. Canon EOS M50) yang terhubung via USB dan kabel HDMI ke capture card.

1. **Paket Sistem gphoto2**:
   ```bash
   sudo apt update
   sudo apt install gphoto2
   ```

2. **Python 3 (>= 3.10)**:
   Pastikan Python 3 dan venv terpasang:
   ```bash
   sudo apt install python3 python3-pip python3-venv
   ```

---

## Instalasi Dependensi

1. Buat atau aktifkan virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Pasang dependensi dari `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```

   Daftar paket:
   - `flet==1.0.5`
   - `opencv-python==4.10.0.84`
   - `gphoto2==2.6.4`

---

## Struktur Direktori

```
fletProject/
├── main.py              # Entry point aplikasi Flet
├── requirements.txt     # Daftar dependensi Python
├── README.md            # Dokumentasi penggunaan
├── issue.md             # Dokumen planning & spesifikasi
├── app/
│   ├── __init__.py
│   ├── config.py        # Konstanta: daftar pose, index kamera, resolusi, ukuran crop
│   ├── camera_preview.py# Thread OpenCV untuk HDMI capture card
│   ├── shutter.py       # Wrapper gphoto2: deteksi kamera & download foto
│   ├── crop_dialog.py   # Dialog crop manual 640x640 dengan fitur zoom & pan
│   ├── image_utils.py   # Utilitas cropping gambar OpenCV
│   ├── storage.py       # Sanitasi NIM, manajemen folder, & penyimpanan JSON
│   └── ui.py            # Susunan antarmuka Flet
├── foto_mahasiswa/      # Folder output foto per NIM & data_mahasiswa.json
└── temp_captures/       # Folder penampungan sementara sebelum foto di-crop
```

---

## Cara Menjalankan

1. Hubungkan HDMI capture card dan kabel USB kamera.
2. Pastikan kamera terdeteksi oleh gphoto2:
   ```bash
   gphoto2 --auto-detect
   ```
3. Jalankan aplikasi:
   ```bash
   python3 main.py
   ```

---

## Alur Penggunaan
1. Masukkan **NIM** dan data mahasiswa lainnya pada panel kanan.
2. Klik tombol **Camera On** untuk mengaktifkan live preview dari HDMI capture card.
3. Pada panel pose, klik **Ambil foto** pada salah satu pose yang diinginkan.
4. Kamera akan memicu shutter USB dan mengunduh foto asli resolusi penuh.
5. **Dialog Crop Manual** akan terbuka:
   - Gunakan tombol **Zoom In (+)** atau **Zoom Out (-)** untuk menyesuaikan tampilan.
   - Klik atau seret kotak biru 640x640 ke area wajah yang diinginkan.
   - Klik tombol **Crop & Simpan Foto**.
6. Foto hasil crop tersimpan ke folder `foto_mahasiswa/<NIM>/` dan thumbnail pada kartu pose akan terisi tanda centang hijau.
7. Ulangi untuk pose lainnya.
8. Klik tombol **Simpan Data Mahasiswa** untuk menyimpan file `data_mahasiswa.json`.

---

## Troubleshooting

- **Error: "could not claim the USB device"**:
  Sistem operasi (gvfs-gphoto2-volume-monitor) otomatis mengunci kamera saat dicolokkan. Lepaskan kuncian dengan:
  ```bash
  killall gvfs-gphoto2-volume-monitor
  ```
  atau lepaskan mount kamera di File Manager.

- **Preview hitam / tidak muncul**:
  Jika HDMI capture card terbaca di index selain `/dev/video0`, ubah nilai `CAMERA_INDEX` di `app/config.py`:
  ```python
  CAMERA_INDEX = 1  # Sesuaikan dengan index v4l2 capture card Anda
  ```

- **Perintah gphoto2 tidak ditemukan**:
  Jalankan `sudo apt install gphoto2`.

