# 🔒 Secure Cloud-Based File Sharing System
### With AES Encryption + AI Summarization + HTTP Client-Server Architecture

---

## 📁 Folder Structure

```
secure-file-share/
├── app.py               ← Flask backend (Person 1)
├── requirements.txt     ← Python dependencies
├── uploads/             ← Raw uploaded files
├── encrypted/           ← AES-encrypted files (.enc)
├── decrypted/           ← Decrypted downloads
├── models/              ← AI model cache + key store + metadata
├── static/
│   ├── style.css        ← Frontend styles (Person 4)
│   └── script.js        ← Frontend JS / HTTP calls (Person 4)
├── templates/
│   └── index.html       ← Main UI (Person 4)
└── utils/
    ├── encryption.py    ← AES-256-CBC module (Person 2)
    └── summarizer.py    ← HuggingFace BART (Person 3)
```

---

## ⚙️ Step-by-Step Setup

### 1. Install Python 3.10+
Download from https://python.org

### 2. Create a virtual environment
```bash
python -m venv venv

# Activate:
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```
> ⏳ First run downloads the HuggingFace BART model (~1.6 GB). Be patient.

### 4. Run the server
```bash
python app.py
```
Expected output:
```
============================================================
  🔒 Secure File Share Server
  📡 Listening on http://0.0.0.0:5000
  🌐 Open browser → http://localhost:5000
============================================================
```

### 5. Open in browser
Visit: **http://localhost:5000**

---

## 🧪 API Testing with Postman

### Import collection or test manually:

#### POST /upload (Upload a file)
- Method: POST
- URL: http://localhost:5000/upload
- Body: form-data
  - Key: `file` (type: File) → select any .txt file
  - Key: `receiver_id` (text) → e.g. `bob`
  - Key: `sender_id` (text) → e.g. `alice`
- Expected response (200 OK):
```json
{
  "status": "success",
  "file_id": "abc12345_test.txt",
  "original_name": "test.txt",
  "receiver_id": "bob",
  "summary": "AI-generated summary here...",
  "file_size_kb": 3.2
}
```

#### GET /files/bob (List files for receiver)
- Method: GET
- URL: http://localhost:5000/files/bob
- Expected: JSON list of files

#### GET /download/<file_id>
- Method: GET
- URL: http://localhost:5000/download/abc12345_test.txt
- Expected: File download (decrypted)

#### GET /summary/<file_id>
- Method: GET
- URL: http://localhost:5000/summary/abc12345_test.txt
- Expected: JSON with AI summary

#### GET /health
- Method: GET
- URL: http://localhost:5000/health
- Expected: `{"status": "ok", ...}`

---

## 🔍 Network Monitoring with Chrome DevTools

1. Open http://localhost:5000
2. Press **F12** → go to **Network** tab
3. Upload a file
4. You'll see:
   - POST /upload → 200 OK
   - Request Headers: Content-Type: multipart/form-data
   - Response Headers: Content-Type: application/json
   - Status codes visible for every request
5. Click any request → see **Timing** tab for TCP connect, TLS, etc.

---

## 🔐 Encryption Explained

```
Plaintext file bytes
     ↓
[PKCS7 Padding to 16-byte blocks]
     ↓
[AES-256-CBC Encryption]  ←── Random 32-byte key + 16-byte IV
     ↓
[IV (16 bytes) + Ciphertext]  → saved as .enc file
     ↓
[Key stored in models/keys.json]
```

---

## 🤖 AI Summarization Flow

```
File saved to uploads/
     ↓
[Extract text content]
     ↓
[Truncate to 3000 chars]
     ↓
[facebook/bart-large-cnn model]
     ↓
[Summary string (40–150 tokens)]
     ↓
[Stored in metadata + returned in JSON response]
```

---

## 🌐 HTTP + TCP/IP Flow

```
Client Browser (Port: random)
    │
    │  HTTP POST /upload (multipart/form-data)
    │  TCP segments over IP
    ▼
Flask Server (Port: 5000)
    │
    ├─→ Save file to uploads/
    ├─→ Encrypt → encrypted/
    ├─→ AI Summarize
    ├─→ Save metadata
    │
    │  HTTP 200 OK (JSON)
    ▼
Client receives response
```

---



