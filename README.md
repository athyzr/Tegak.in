# Tegak-in

Aplikasi Windows untuk membantu mengingatkan postur duduk menggunakan webcam.

## Menjalankan aplikasi

Unduh `Tegak-in.exe` dari bagian **Releases**, lalu jalankan di Windows 10/11 64-bit. Python tidak perlu dipasang di komputer pengguna. Izinkan akses kamera jika Windows memintanya.

Jika Windows menampilkan peringatan SmartScreen untuk file yang belum dikenal, pastikan file berasal dari rilis Tegak-in yang tepercaya sebelum memilih untuk menjalankannya.

## Membuat file EXE

Build dilakukan di Windows dan memerlukan Python 3.12 64-bit serta Python Launcher (`py`).

1. Buka folder proyek di Windows.
2. Jalankan `build.bat`.
3. Setelah selesai, file aplikasi ada di `dist\Tegak-in.exe`.

Build pertama memerlukan koneksi internet untuk memasang dependensi. `Tegak-in.exe` adalah build satu-file dan sudah menyertakan dependensi serta model MediaPipe; komputer pengguna tidak perlu memasang Python.

Untuk membagikan aplikasi, unggah `dist\Tegak-in.exe` sebagai aset pada GitHub Release. Perubahan kode atau repo saja tidak otomatis menerbitkan file EXE.

Log error aplikasi tersimpan di `%LOCALAPPDATA%\Tegak-in\error.log`.
