# Portal Aplikasi Analisis & Penilaian Kinerja (Demo Sistem)

Proyek ini adalah sebuah portal aplikasi berbasis **Streamlit** yang mengintegrasikan tiga modul utama untuk analisis data dan penilaian kinerja SDM. Sistem ini memanfaatkan teknologi **Generative AI** (LLM) untuk query database (NL2SQL) dan analisis kualitatif (RAG), serta menyediakan antarmuka interaktif untuk penilaian kinerja 360 derajat.

Proyek ini dikembangkan menggunakan **Python 3.11+** dan dikelola menggunakan **uv**.

## 📋 Deskripsi Modul

Aplikasi ini terdiri dari tiga modul utama yang dapat diakses melalui navigasi sidebar:

### 1. 🤖 BPOM Chatbot (Query Data)

_Lokasi: `app/query/app.py`_
Modul ini berfungsi sebagai asisten cerdas yang mengubah pertanyaan bahasa alami (Natural Language) menjadi query SQL (NL2SQL).

- **Fungsi Utama**: Memungkinkan pengguna untuk bertanya tentang data operasional atau SDM tanpa perlu menulis SQL manual.
- **Teknologi**: OpenAI API / Grok Model, SQLAlchemy, Pandas.

### 2. 📊 Penilaian 360

_Lokasi: `app/three_sixty/app.py`_
Aplikasi formulir penilaian kinerja metode 360 derajat.

- **Fungsi Utama**: Input penilaian perilaku dan hasil kerja karyawan dari berbagai perspektif (atasan, rekan sejawat, bawahan).
- **Fitur**: Tabulasi data utama, penilaian hasil kerja, dan penilaian perilaku.

### 3. 🧭 Penilaian Kualitatif (RAG System)

_Lokasi: `app/kualitatif/app.py`_
Sistem analisis kualitatif menggunakan metode Retrieval-Augmented Generation (RAG).

- **Fungsi Utama**: Menganalisis dokumen regulasi (PDF) dan standar kompetensi (JSON) untuk memberikan penilaian atau jawaban berbasis konteks dokumen.
- **Teknologi**: LangChain, PostgreSQL (PGVector), OpenAI Embeddings.

---

## 🛠️ Prasyarat

Sebelum menjalankan aplikasi, pastikan Anda telah menginstal:

1.  **Python** (versi 3.11 atau lebih baru)
2.  **uv** (Python package manager yang cepat) - [Instalasi uv](https://github.com/astral-sh/uv)
3.  **PostgreSQL** (Database)
    - Pastikan ekstensi `pgvector` telah diaktifkan untuk fitur RAG.

## 📦 Instalasi

1.  **Clone repositori ini:**

    ```bash
    git clone https://github.com/username/repo-anda.git
    cd demo-sistem
    ```

2.  **Install dependensi menggunakan `uv`:**
    ```bash
    uv sync
    ```
    _Jika Anda tidak menggunakan `uv`, Anda bisa melihat `pyproject.toml` untuk daftar library yang dibutuhkan._

## ⚙️ Konfigurasi

1.  **Buat file `.env`:**
    Salin file `.env.example` menjadi `.env`:

    ```bash
    cp .env.example .env
    ```

2.  **Isi variabel lingkungan di `.env`:**
    Buka file `.env` dan sesuaikan konfigurasinya:

    ```ini
    # API Key untuk LLM (OpenAI / OpenRouter / Grok)
    API_KEY="sk-..."
    BASE_URL="https://api.openai.com/v1" # Atau endpoint lain seperti OpenRouter

    # Koneksi Database Utama (untuk data karyawan/transaksi)
    DATABASE_URL="postgresql+psycopg2://user:password@localhost:5432/nama_db"

    # Koneksi Database Vector (untuk RAG / LangChain)
    # Bisa sama dengan DATABASE_URL jika menggunakan satu DB
    VECTOR_DB_URL="postgresql+psycopg2://user:password@localhost:5432/nama_db_vector"
    ```

## 🚀 Penggunaan

Jalankan aplikasi utama menggunakan perintah berikut:

```bash
uv run streamlit run main.py
```

Atau jika environment sudah aktif:

```bash
streamlit run main.py
```

Akses aplikasi melalui browser di alamat yang muncul di terminal (biasanya `http://localhost:8501`).

## 📂 Struktur Folder

```text
demo-sistem/
├── app/
│   ├── kualitatif/   # Modul RAG & Analisis Kualitatif
│   ├── query/        # Modul Chatbot NL2SQL
│   └── three_sixty/  # Modul Penilaian 360
├── data/             # (Opsional) Folder penyimpanan dokumen sumber
├── main.py           # Entry point aplikasi (Streamlit Navigation)
├── pyproject.toml    # Definisi dependensi proyek
├── uv.lock           # Lockfile dependensi
└── .env              # File konfigurasi sensitif (jangan dicommit)
```

## 🤝 Kontribusi

Kontribusi selalu diterima! Jika Anda ingin berkontribusi:

1.  Fork repositori ini.
2.  Buat branch fitur baru (`git checkout -b fitur-keren`).
3.  Commit perubahan Anda (`git commit -m 'Menambahkan fitur keren'`).
4.  Push ke branch tersebut (`git push origin fitur-keren`).
5.  Buat Pull Request.

## 📄 Lisensi

[Tambahkan informasi lisensi di sini, misal: MIT, Apache 2.0, atau Private]
