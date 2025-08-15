# Aplikasi Chat AI Multi-Modal dengan Gemini

Proyek ini adalah aplikasi AI percakapan full-stack yang canggih dan multi-modal. Aplikasi ini memungkinkan pengguna untuk berinteraksi dengan AI yang didukung oleh model Gemini dari Google melalui berbagai cara: obrolan teks, pesan suara, unggahan gambar, dan panggilan suara real-time dupleks penuh.

## Ringkasan Proyek

Aplikasi ini dirancang sebagai platform obrolan yang kaya fitur, menggabungkan antarmuka obrolan tradisional dengan kemampuan interaksi suara dan gambar yang canggih. Backend berbasis Python (FastAPI) mengatur logika AI dan komunikasi, sementara frontend Next.js menyediakan antarmuka pengguna yang responsif dan modern.

### Fitur Utama

-   **Obrolan Multi-Modal**: Mendukung input berupa teks, audio, dan gambar.
-   **Panggilan Suara Real-Time**: Memungkinkan percakapan suara dupleks penuh yang lancar dengan AI, di mana pengguna dan AI dapat saling menyela secara alami.
-   **Pesan Suara**: Pengguna dapat merekam dan mengirim pesan suara dari dalam antarmuka obrolan.
-   **Analisis Gambar**: Kemampuan untuk mengunggah gambar dan mengajukan pertanyaan tentangnya.
-   **Manajemen Sesi & Riwayat Obrolan**: Menyimpan dan memuat riwayat percakapan, terintegrasi dengan Supabase untuk persistensi data.
-   **Generasi Teks AI**: Memanfaatkan model Google Gemini 1.5 Flash untuk respons yang cerdas dan cepat.
-   **Text-to-Speech (TTS)**: Menggunakan model VITS lokal berkualitas tinggi (`datasetsANDmodels/indonesian-tts`) untuk menghasilkan ucapan yang terdengar alami secara real-time.
-   **Speech-to-Text (STT)**: Menggunakan API `SpeechRecognition` bawaan browser untuk transkripsi real-time.
-   **Komunikasi Hibrida**: Menggunakan WebSocket untuk latensi rendah dalam mode panggilan dan REST API untuk fungsi obrolan lainnya.

## Arsitektur

Proyek ini dibagi menjadi dua komponen utama:

1.  **`frontend/`**: Aplikasi Next.js yang menyediakan antarmuka obrolan dan panggilan. Aplikasi ini menangani akses mikrofon, pengenalan ucapan, pemutaran audio, dan interaksi pengguna.
2.  **`python-backend/`**: Server FastAPI yang mengelola logika inti. Ini menangani beberapa endpoint REST untuk obrolan teks/gambar dan endpoint WebSocket khusus untuk percakapan suara real-time.

### Alur Kerja

1.  **Obrolan Teks & Gambar**:
    -   Pengguna mengirim pesan teks atau mengunggah gambar melalui antarmuka obrolan.
    -   Frontend mengirim permintaan ke endpoint REST API yang sesuai di backend (`/api/generateText` atau `/api/processImage`).
    -   Backend memproses input, meneruskannya ke Gemini API (bersama dengan riwayat obrolan), dan mengembalikan respons teks.

2.  **Pesan Suara**:
    -   Pengguna merekam pesan audio di antarmuka obrolan.
    -   Setelah selesai, rekaman dikirim ke endpoint `/api/full-conversation`.
    -   Backend mentranskripsi audio, mengirimkan teks ke Gemini, menghasilkan respons teks dari AI, mengubah respons tersebut menjadi audio menggunakan TTS, dan mengirimkan kembali transkripsi pengguna beserta audio respons AI.

3.  **Panggilan Suara Real-Time**:
    -   Pengguna memulai "panggilan" dari antarmuka.
    -   Koneksi WebSocket dibuat ke endpoint `/ws/conversation`.
    -   Saat pengguna berbicara, teks yang ditranskripsi secara real-time dikirim melalui WebSocket.
    -   Backend mengirimkan teks ini ke Gemini API untuk mendapatkan respons streaming.
    -   Respons teks dari AI dipecah menjadi kalimat, diubah menjadi potongan audio (audio chunks) menggunakan model TTS lokal, dan dialirkan kembali ke frontend melalui WebSocket untuk pemutaran yang berkelanjutan.

## Tumpukan Teknologi

-   **Frontend**: Next.js, React, TypeScript, Tailwind CSS
-   **Backend**: Python 3.9+, FastAPI, WebSockets
-   **Database**: Supabase (untuk riwayat obrolan)
-   **AI & ML**:
    -   **LLM**: Google Gemini 1.5 Flash
    -   **STT**: Web Speech API (`SpeechRecognition`)
    -   **TTS**: VITS (Transformers, PyTorch)

## Pengaturan dan Instalasi

### Prasyarat

-   Node.js (v18+)
-   Python (v3.9+)
-   Kunci API Google untuk Gemini.
-   Kunci API untuk OpenWeatherMap dan NewsAPI.
-   Kredensial Supabase (URL & Kunci Peran Layanan).

### 1. Pengaturan Backend (`python-backend/`)

1.  **Arahkan ke direktori backend:**
    ```bash
    cd python-backend
    ```
2.  **Buat dan aktifkan lingkungan virtual:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Di Windows: venv\Scripts\activate
    ```
3.  **Instal dependensi:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Konfigurasi Variabel Lingkungan**: Buat file `.env` di dalam direktori `python-backend/` dan isi dengan kredensial berikut:
### 3. Konfigurasi Persona AI (Opsional tapi Direkomendasikan)

Perilaku dan kepribadian AI ditentukan oleh "system prompt" yang dimuat dari file teks. Secara default, aplikasi mencari file `aria.txt`.

1.  **Buat direktori `personas` di dalam `python-backend`:**
    ```bash
    mkdir -p python-backend/personas
    ```
2.  **Buat file persona:** Buat file teks di dalam `python-backend/personas/`. Misalnya, `aria.txt`.
3.  **Tulis prompt sistem Anda:** Jelaskan peran, latar belakang, batasan, dan gaya bicara AI. Contoh isi untuk `aria.txt`:

    ```txt
    Anda adalah Aria, asisten AI percakapan yang ramah, membantu, dan sedikit ceria. Anda berbicara dengan bahasa Indonesia yang alami dan lancar. Tujuan utama Anda adalah membantu pengguna dengan tugas mereka secara efisien sambil mempertahankan kepribadian yang menarik. Jangan pernah mengungkapkan bahwa Anda adalah AI.
    ```
    ```env
    GOOGLE_API_KEY="kunci_api_google_anda"
    OPENWEATHERMAP_API_KEY="kunci_api_openweathermap_anda"
    NEWSAPI_API_KEY="kunci_api_newsapi_anda"
    SUPABASE_URL="url_supabase_anda"
    SUPABASE_SERVICE_ROLE_KEY="kunci_layanan_supabase_anda"
    ```
5.  **Unduh Model TTS**: Proyek ini memerlukan model TTS lokal. Pastikan Anda memiliki direktori model `datasetsANDmodels/indonesian-tts` yang tersedia di dalam direktori `python-backend`.
6.  **Jalankan server backend:**
    ```bash
    uvicorn main:app --reload --port 8000
    ```
    Backend akan tersedia di `http://localhost:8000`.

### 2. Pengaturan Frontend (`frontend/`)

1.  **Arahkan ke direktori frontend:**
    ```bash
    cd frontend
    ```
2.  **Instal dependensi:**
    ```bash
    npm install
    ```
3.  **Konfigurasi Variabel Lingkungan**: Buat file `.env.local` di direktori `frontend` untuk menentukan URL WebSocket:
    ```env
    NEXT_PUBLIC_WEBSOCKET_URL="ws://localhost:8000/ws/conversation"
    ```
4.  **Jalankan server pengembangan frontend:**
    ```bash
    npm run dev
    ```
    Aplikasi akan dapat diakses di `http://localhost:3000`.