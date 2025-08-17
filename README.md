# Aplikasi Chat AI Multi-Modal dengan Gemini & Multi-Engine TTS

Proyek ini adalah aplikasi AI percakapan full-stack yang canggih, memungkinkan pengguna berinteraksi dengan AI yang didukung Google Gemini melalui obrolan teks, pesan suara, unggahan gambar, dan panggilan suara real-time dupleks penuh.

## Ringkasan Proyek

Aplikasi ini dirancang sebagai platform obrolan kaya fitur yang menggabungkan antarmuka web modern dengan kemampuan interaksi suara dan gambar. Backend berbasis Python (FastAPI) mengatur logika AI, sementara frontend Next.js menyediakan antarmuka pengguna yang responsif.

### Fitur Utama

-   **Obrolan Multi-Modal**: Mendukung input berupa teks, audio, dan gambar.
-   **Panggilan Suara Real-Time**: Memungkinkan percakapan suara dupleks penuh yang lancar dengan AI.
-   **Speech-to-Text (STT) Ringan**: Menggunakan **Web Speech API** bawaan browser (sisi klien) untuk transkripsi real-time, mengurangi beban server secara signifikan.
-   **Multi-Engine & Multi-Bahasa Text-to-Speech (TTS)**:
    -   **Bahasa Indonesia**: Menggunakan model **Coqui TTS** lokal untuk suara yang natural.
    -   **Bahasa Inggris**: Menggunakan **Piper TTS** lokal untuk ucapan yang jernih.
    -   **Bahasa Jepang**: Terintegrasi dengan **VoiceVOX Engine** untuk suara berkualitas tinggi.
-   **Manajemen Sesi & Riwayat Obrolan**: Terintegrasi dengan **Supabase** untuk persistensi data.
-   **Analisis Gambar**: Kemampuan untuk mengunggah gambar dan berdiskusi tentangnya dengan AI.
-   **Komunikasi Hibrida**: Menggunakan WebSocket untuk latensi rendah dalam mode panggilan dan REST API untuk fungsi obrolan lainnya.

## Arsitektur

Proyek ini dibagi menjadi dua komponen utama: `frontend/` (Next.js) dan `python-backend/` (FastAPI).

-   **STT (Speech-to-Text)**: Proses transkripsi terjadi sepenuhnya di sisi klien (browser) menggunakan Web Speech API. Teks yang sudah jadi kemudian dikirim ke backend.
-   **TTS (Text-to-Speech)**: Backend menerima teks dari AI, mendeteksi bahasa, dan memilih engine TTS yang sesuai (Coqui, Piper, atau VoiceVOX) untuk menghasilkan audio, yang kemudian dialirkan kembali ke klien.

## Tumpukan Teknologi

-   **Frontend**: Next.js, React, TypeScript, Tailwind CSS
-   **Backend**: Python 3.9+, FastAPI, WebSockets
-   **Database**: Supabase
-   **AI & ML**:
    -   **LLM**: Google Gemini 2.5 Flash
    -   **STT**: Web Speech API (Browser-based)
    -   **TTS**: Coqui TTS, Piper TTS, VoiceVOX Engine

---

## Panduan Setup Lengkap

Ikuti langkah-langkah ini dengan teliti untuk menjalankan proyek dari awal.

### Prasyarat

-   Node.js (v18+)
-   Python (v3.9+)
-   Akun [Google AI Studio](https://aistudio.google.com/) untuk mendapatkan **API Key Gemini**.
-   Akun [Supabase](https://supabase.com/) untuk membuat proyek database.
-   Git dan `unzip` (atau utilitas ekstraksi arsip lainnya).

### Langkah 1: Clone Repository

```bash
git clone https://github.com/BxY-try/basicGeminiConversationalViaAPI.git
cd basicGeminiConversationalViaAPI
```

### Langkah 2: Setup Frontend & Supabase

Langkah ini penting untuk dilakukan lebih awal karena kita memerlukan kredensial Supabase untuk backend.

1.  **Buat Proyek Supabase**:
    -   Login ke akun Supabase Anda dan buat proyek baru.
    -   Setelah proyek dibuat, navigasikan ke **Project Settings > API**.
    -   Anda akan memerlukan **Project URL** dan **Project API Keys** (gunakan `anon` `public` key).

2.  **Navigasi ke Direktori Frontend**:
    ```bash
    cd frontend
    ```

3.  **Instal Dependensi Node.js**:
    ```bash
    npm install
    ```

4.  **Konfigurasi Variabel Lingkungan Frontend**:
    -   Buat file `.env.local` dari contoh yang ada:
        ```bash
        cp .env.local.example .env.local
        ```
    -   Buka file `.env.local` dan isi dengan nilai dari proyek Supabase Anda dan URL backend:
        ```env
        NEXT_PUBLIC_WEBSOCKET_URL="ws://localhost:8000/ws/conversation"
        NEXT_PUBLIC_SUPABASE_URL="URL_PROYEK_SUPABASE_ANDA"
        NEXT_PUBLIC_SUPABASE_ANON_KEY="KUNCI_ANON_PUBLIK_SUPABASE_ANDA"
        ```

### Langkah 3: Setup Backend

1.  **Navigasi ke Direktori Backend**:
    ```bash
    cd ../python-backend  # Kembali ke root, lalu masuk ke python-backend
    ```

2.  **Buat dan Aktifkan Lingkungan Virtual**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Di Windows: venv\Scripts\activate
    ```

3.  **Instal Dependensi Python**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Konfigurasi Variabel Lingkungan Backend**:
    -   Buat file `.env` di dalam direktori `python-backend/`.
    -   Isi dengan API key Google Anda dan kredensial Supabase (termasuk **Service Role Key** yang bersifat rahasia dari pengaturan API Supabase):
        ```env
        GOOGLE_API_KEY="API_KEY_GEMINI_ANDA"
        SUPABASE_URL="URL_PROYEK_SUPABASE_ANDA"
        SUPABASE_SERVICE_ROLE_KEY="KUNCI_SERVICE_ROLE_SUPABASE_ANDA"
        ```

### Langkah 4: Unduh Model TTS & VoiceVOX Engine (Langkah Manual)

Folder-folder ini diabaikan oleh Git (`.gitignore`) karena ukurannya yang besar. Anda harus mengunduhnya secara manual.

1.  **VoiceVOX Engine (untuk TTS Bahasa Jepang)**:
    -   Unduh versi CPU untuk Linux dari [halaman rilis VoiceVOX Engine](https://github.com/VOICEVOX/voicevox_engine/releases). Cari file seperti `voicevox_engine-linux-x64-cpu-*.zip`.
    -   Ekstrak isinya ke dalam direktori root proyek sehingga Anda memiliki struktur folder `voicevox_engine/`.

2.  **Model TTS (Indonesia & Inggris)**:
    -   Buat direktori yang diperlukan:
        ```bash
        mkdir -p datasetsANDmodels/indonesian-tts
        mkdir -p datasetsANDmodels/piper-en
        ```
    -   **Model Coqui TTS (Indonesia)**: Unduh file model yang diperlukan dan letakkan di dalam `python-backend/datasetsANDmodels/indonesian-tts/`.
    -   **Model Piper TTS (Inggris)**: Unduh file model `.onnx` dan `.onnx.json` (misalnya, `en_US-lessac-high.onnx`) dan letakkan di dalam `python-backend/datasetsANDmodels/piper-en/`.
    -   *(Catatan: Sediakan link langsung ke model jika memungkinkan untuk mempermudah pengguna)*.

### Langkah 5: Menjalankan Aplikasi

Anda perlu menjalankan 3 proses di terminal yang terpisah.

1.  **Terminal 1: Jalankan VoiceVOX Engine**:
    *   Pastikan Anda berada di direktori root proyek.
    ```bash
    cd voicevox_engine
    ./run
    ```
    Biarkan terminal ini berjalan. Server ini harus aktif agar TTS Bahasa Jepang berfungsi.

2.  **Terminal 2: Jalankan Server Backend FastAPI**:
    *   Pastikan lingkungan virtual Python Anda aktif.
    ```bash
    cd python-backend
    uvicorn main:app --reload --port 8000
    ```
    Server backend akan berjalan di `http://localhost:8000`.

3.  **Terminal 3: Jalankan Server Frontend Next.js**:
    ```bash
    cd frontend
    npm run dev
    ```
    Aplikasi web akan dapat diakses di `http://localhost:3000`.

### Langkah 6: Konfigurasi Persona AI (Opsional)

Anda dapat menyesuaikan kepribadian AI dengan mengedit file prompt sistem.

1.  **Buat direktori `personas` jika belum ada**:
    ```bash
    mkdir -p python-backend/personas
    ```
2.  **Buat file persona**, misalnya `aria.txt`, di dalam `python-backend/personas/`.
3.  **Tulis prompt sistem Anda**. Contoh:
    ```txt
    Anda adalah Aria, asisten AI yang ramah dan membantu.
    ```

Sekarang aplikasi Anda siap digunakan!
