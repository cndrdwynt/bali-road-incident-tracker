# 🚦 Bali Traffic & Incident Monitoring System

Sistem pemantauan lalu lintas dan insiden wilayah Bali secara **real-time** dengan mengekstraksi data dari akun Facebook **Denpasar Viral**. Dibangun menggunakan arsitektur Big Data modern yang mengintegrasikan scraping otomatis, pipeline orkestrasi AI, geocoding lokasi, hingga dashboard analitik interaktif.

---

## 📊 Arsitektur & Alur Sistem

Sistem bekerja secara otomatis ujung-ke-ujung (*end-to-end*) melalui pipeline berikut:

1. **Automated Social Media Scraping (Python, Selenium & Docker Chrome)**
   - `main.py` menggunakan Selenium Webdriver Remote yang terhubung ke kontainer `selenium-vnc` (Standalone Chrome)
   - Login memanfaatkan autentikasi sesi lokal (`cookies.json`) untuk menghindari deteksi bot
   - Melakukan *infinite scroll* yang mensimulasikan perilaku manusia, menyaring kiriman berbasis kata kunci gangguan jalan (*kecelakaan, macet, kebakaran, damkar, laka*)
   - Data disimpan ke MongoDB dengan status `pending_ai` secara **Upsert** (anti-duplikasi)
   - Proses browser dapat dipantau *live* via VNC Viewer di port `7900`

2. **AI-Driven Extraction & Data Cleaning (n8n & Groq Cloud API)**
   - **Schedule Trigger** n8n mengaktifkan alur kerja setiap 6 jam untuk menarik dokumen `pending_ai`
   - Data dikirim ke **Basic LLM Chain** (`llama-3.1-8b-instant` via Groq) untuk mengekstrak: nama jalan (`street_name`), tanggal insiden (`incident_date`), dan jenis insiden (`Kecelakaan` / `Kemacetan` / `Kebakaran`)
   - **Node Code (JavaScript)** memparsing output JSON dari AI, memfilter lokasi tidak jelas (`Unknown`), dan menandai status dokumen menjadi `processed` atau `ignored`

3. **Automated Geolocation (OpenStreetMap Nominatim API)**
   - Data yang lolos filter memicu **HTTP Request** ke Nominatim API untuk mendapatkan koordinat *Latitude* & *Longitude* jalan di wilayah Bali secara akurat

4. **Data Visualization (Metabase BI Dashboard)**
   - Metabase membaca MongoDB untuk menampilkan peta sebaran titik rawan, grafik frekuensi jenis insiden harian, dan tabel kronologis insiden interaktif

5. **Intelligent Telegram Bot (AI Agent)**
   - **Telegram Trigger** menangkap pesan pengguna dan meneruskannya ke **AI Agent** (`llama-3.3-70b-versatile`)
   - Agent dibekali **MongoDB Custom Tool** `DatabaseLaluLintas` — saat pengguna menanyakan kondisi suatu wilayah (contoh: *"Ada macet apa di Bypass Ngurah Rai?"*), AI memformat parameter `[jenis_kejadian]|[lokasi]` dan menggeledah database via query `$and`-`$or`, lalu mengembalikan jawaban langsung ke chat Telegram

---

## 🛠️ Docker Services

| Service | Image | Port | Fungsi |
|---|---|---|---|
| `mongodb_bali` | `mongo:latest` | `27017` | Database NoSQL utama |
| `mongo-express` | `mongo-express:latest` | `8081` | Web GUI manajemen database |
| `selenium-vnc` | `selenium/standalone-chrome:latest` | `4444` / `7900` | Browser Chrome terisolasi + VNC live view |
| `fb_scraper` | Local Build | — | Worker Python scraper Facebook |
| `n8n_bali` | `n8nio/n8n:latest` | `5680` | Mesin orkestrasi pipeline AI |
| `metabase_bali` | `metabase/metabase:latest` | `3001` | Dashboard BI visualisasi data |

---

## 📂 Struktur Direktori

```text
bigdata-n8n-bali/
│
├── metabase_data/             # Diabaikan .gitignore (Penyimpanan Internal Metabase)
├── mongo_data/                # Diabaikan .gitignore (Penyimpanan Fisik MongoDB)
├── n8n_data/                  # Diabaikan .gitignore (Konfigurasi Lokal n8n)
│
├── scraper/
│   ├── cookies.json           # Diabaikan .gitignore (Sesi Login Facebook)
│   ├── Dockerfile             # Build image Docker worker scraper
│   ├── main.py                # Skrip utama Python Selenium FB Scraper
│   └── requirements.txt       # Dependensi library Python
│
├── .env                       # Diabaikan .gitignore (Kredensial & API Key)
├── .gitignore                 # Aturan pengabaian pelacakan Git
├── Traffic Bali.json          # Export workflow n8n Data Processing Pipeline
├── chatbot traffic FINAL.json # Export workflow n8n Telegram Bot Agent
├── docker-compose.yml         # Konfigurasi orkestrasi Docker services
├── Metabase - Traffic Bali.pdf# Validasi hasil visualisasi dashboard
├── ngrok.exe                  # Diabaikan .gitignore (Aplikasi tunneling lokal)
└── README.md                  # Dokumentasi utama proyek
```

---

## 🚀 Panduan Setup & Deployment

### 1. Clone Project

```bash
git clone <url-repository-kamu>
cd bigdata-n8n-bali
```

### 2. Konfigurasi Environment

Buat file `.env` di root direktori (sudah dilindungi `.gitignore`, **jangan pernah di-commit**):

```env
MONGO_URL=mongodb://mongodb_bali:27017
SELENIUM_REMOTE_URL=http://selenium-vnc:4444/wd/hub
GROQ_API_KEY=your_groq_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
NGROK_URL=your_ngrok_public_url
```

> ⚠️ Letakkan file `cookies.json` sesi Facebook kamu ke dalam folder `scraper/` sebelum menjalankan Docker.

### 3. Jalankan Infrastruktur Docker

```bash
docker compose up -d --build
```

Flag `--build` memastikan image `fb_scraper` dibangun otomatis. Verifikasi semua kontainer berjalan:

```bash
docker ps
```

### 4. Pantau Live Scraping (Opsional)

Buka browser → `http://localhost:7900`  
Password VNC default: `secret`

Kamu bisa menyaksikan langsung bot Selenium menggerakkan Chrome untuk mendeteksi kata kunci dan menyimpan data ke database.

### 5. Import Workflow Data Processing ke n8n

1. Buka `http://localhost:5680`
2. Buat workflow baru → **Import from File** → pilih `Traffic Bali.json`
3. Hubungkan node **Find documents** & **Update documents** ke MongoDB:
   - Host: `mongodb_bali`, Port: `27017`
4. Masukkan Groq API Key pada node **Groq Chat Model**
5. **Save** → **Set Active**

### 6. Import & Aktivasi Telegram Bot Agent

1. Buka `http://localhost:5680` → buat workflow baru → **Import from File** → pilih `chatbot traffic FINAL.json`
2. Konfigurasi webhook n8n dengan URL Ngrok (sesuai `.env`)
3. Masukkan token bot Telegram pada node **Telegram Trigger** & **Send a text message**
4. Hubungkan kredensial MongoDB pada node tool **DatabaseLaluLintas**
5. **Save** → **Set Active**

Coba kirim pertanyaan ke bot Telegram kamu, contoh: *"Ada insiden apa di Bypass Ngurah Rai hari ini?"*

### 7. Setup Dashboard Metabase

1. Buka `http://localhost:3001`
2. Setup akun baru → tambah koneksi database **MongoDB**
3. Host: `mongodb_bali`, Database: `bali_traffic`
4. Susun visualisasi: peta sebaran titik rawan, grafik top lokasi kerawanan, tabel kronologis insiden

---

## 📈 Kecenderungan Tren Data

Berdasarkan agregasi data berkala yang terekam sistem:

- 🔴 **Dominasi Insiden:** Kasus **Kebakaran** menempati laporan tertinggi, disusul **Kemacetan** di jam sibuk, dan **Kecelakaan** harian
- 📍 **Titik Paling Rawan:** Jalur **Denpasar–Gilimanuk** dan **Bypass Ngurah Rai** tercatat memiliki frekuensi gangguan tertinggi berdasarkan volume laporan masuk

---

## 📄 Lisensi

Proyek ini dikembangkan sebagai media riset analitik lalu lintas berbasis **Social Media Intelligence** yang transparan dan dapat diandalkan.
