"""
app.py — Secure Cloud-Based File Sharing System
================================================
NEW in this version:
  ✅ Login system  — Flask sessions + cookies (POST /login, GET /logout)
  ✅ GET /stats    — server statistics endpoint
  ✅ Network delay — simulate latency (GET /simulate-delay/<ms>)
  ✅ Google Drive  — optional cloud storage toggle (ENABLE_DRIVE flag)
  ✅ HTTPS ready   — run behind ngrok for TLS

NETWORKING CONCEPTS DEMONSTRATED:
  • Client-Server Architecture
  • HTTP Protocol (GET, POST)
  • TCP/IP Model (Application → Transport → Network → Data Link)
  • Sessions & Cookies (stateful HTTP)
  • HTTPS / TLS (via ngrok)
  • Status Codes (200, 400, 401, 403, 404, 500)
  • Request-Response Cycle
  • Cloud Storage (Google Drive API)
  • Network Latency Simulation
"""

import os, json, uuid, time
from datetime import datetime
from flask import (Flask, request, jsonify, send_file,
                   render_template, session, redirect, url_for)
from werkzeug.utils import secure_filename

from utils.encryption import encrypt_file, decrypt_file
from utils.summarizer  import summarize_file

# ── Optional Google Drive integration ─────────────────────────────────────────
ENABLE_DRIVE = False   # Set True + configure credentials to use Google Drive
if ENABLE_DRIVE:
    try:
        from utils.drive import upload_to_drive, download_from_drive
    except ImportError:
        print("[DRIVE] ⚠️  drive.py not found — disabling Google Drive.")
        ENABLE_DRIVE = False

# ── App Configuration ──────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.urandom(24)          # Signs session cookies — change to fixed string in prod
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024   # 50 MB

UPLOAD_FOLDER    = "uploads"
ENCRYPTED_FOLDER = "encrypted"
DECRYPTED_FOLDER = "decrypted"
METADATA_FILE    = "models/metadata.json"
USERS_FILE       = "models/users.json"

for folder in [UPLOAD_FOLDER, ENCRYPTED_FOLDER, DECRYPTED_FOLDER, "models"]:
    os.makedirs(folder, exist_ok=True)

ALLOWED_EXTENSIONS = {
    "txt","pdf","png","jpg","jpeg","gif","docx","xlsx","pptx",
    "csv","py","js","html","json","md","zip","mp4","c","cpp","java"
}

# ── Simulated Network Delay ────────────────────────────────────────────────────
# Demonstrates network latency concept — toggle via UI
_simulate_delay_ms = 0   # 0 = disabled

# ── Helpers ────────────────────────────────────────────────────────────────────
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def load_json(path, default={}):
    if not os.path.exists(path):
        return default.copy()
    with open(path) as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def load_metadata(): return load_json(METADATA_FILE, {})
def save_metadata(d): save_json(METADATA_FILE, d)
def load_users():    return load_json(USERS_FILE, {})
def save_users(d):   save_json(USERS_FILE, d)

def log_req(method, endpoint, status, extra=""):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {method:6s} {endpoint:35s} → HTTP {status}  {extra}")

def apply_delay():
    """Simulate network latency — demonstrates Network Latency concept."""
    if _simulate_delay_ms > 0:
        time.sleep(_simulate_delay_ms / 1000)

def login_required(f):
    """Decorator: redirect to /login if not authenticated."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return jsonify({"error": "401 Unauthorized — Please log in first.", "redirect": "/login"}), 401
        return f(*args, **kwargs)
    return decorated

# ── Seed default users (for demo) ─────────────────────────────────────────────
def seed_users():
    users = load_users()
    changed = False
    for u, p in [("alice", "alice123"), ("bob", "bob123"),
                 ("admin", "admin123"), ("user1", "pass1"), ("user2", "pass2")]:
        if u not in users:
            users[u] = {"password": p, "created": datetime.now().isoformat()}
            changed = True
    if changed:
        save_users(users)
        print("[AUTH] ✅ Demo users seeded: alice, bob, admin, user1, user2")

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html",
                           logged_in="username" in session,
                           username=session.get("username", ""))

# ══════════════════════════════════════════════════════════════════════════════
# AUTH MODULE — Login / Logout (Sessions & Cookies)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/login", methods=["GET", "POST"])
def login():
    """
    GET  /login  → Serve login page
    POST /login  → Validate credentials, create session, set cookie

    NETWORKING CONCEPT — Sessions & Cookies:
      HTTP is stateless — the server forgets each request.
      Sessions solve this: after login, the server stores a session ID
      and sends it to the browser as a Set-Cookie header.
      The browser automatically sends this cookie in every future request.
      The server reads the cookie, looks up the session, and knows who you are.

    Cookie flow:
      POST /login → server validates → session['username'] = 'alice'
                 → Flask sets: Set-Cookie: session=<signed_token>; HttpOnly; Path=/
      Next request → browser sends: Cookie: session=<signed_token>
                 → Flask reads session → username = 'alice'  ✅
    """
    if request.method == "GET":
        return render_template("login.html")

    data     = request.get_json(silent=True) or {}
    username = (data.get("username") or request.form.get("username", "")).strip()
    password = (data.get("password") or request.form.get("password", "")).strip()

    if not username or not password:
        log_req("POST", "/login", 400, "Missing credentials")
        return jsonify({"error": "Username and password required."}), 400

    users = load_users()
    if username not in users or users[username]["password"] != password:
        log_req("POST", "/login", 401, f"Invalid credentials for '{username}'")
        return jsonify({"error": "Invalid username or password."}), 401

    # Create session — Flask signs it with app.secret_key
    session["username"]   = username
    session["login_time"] = datetime.now().isoformat()

    log_req("POST", "/login", 200, f"User '{username}' logged in — session created")
    return jsonify({
        "status":   "success",
        "message":  f"Welcome, {username}!",
        "username": username,
        "note":     "Session cookie set — browser will send it automatically on every future request."
    }), 200


@app.route("/logout", methods=["GET", "POST"])
def logout():
    """
    GET /logout → Clear session, remove cookie
    The browser's session cookie is invalidated.
    """
    username = session.get("username", "unknown")
    session.clear()
    log_req("GET", "/logout", 200, f"User '{username}' logged out — session cleared")
    return jsonify({"status": "success", "message": "Logged out successfully."}), 200


@app.route("/me", methods=["GET"])
def me():
    """
    GET /me → Returns current logged-in user info from session cookie.
    Demonstrates stateful HTTP — server reads session from cookie.
    """
    if "username" not in session:
        return jsonify({"logged_in": False}), 200
    return jsonify({
        "logged_in":  True,
        "username":   session["username"],
        "login_time": session.get("login_time"),
        "note":       "This data came from your session cookie — not from a re-login."
    }), 200


@app.route("/register", methods=["POST"])
def register():
    """POST /register — Create a new user account."""
    data     = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "Username and password required."}), 400
    if len(password) < 4:
        return jsonify({"error": "Password must be at least 4 characters."}), 400

    users = load_users()
    if username in users:
        return jsonify({"error": f"Username '{username}' already taken."}), 400

    users[username] = {"password": password, "created": datetime.now().isoformat()}
    save_users(users)
    log_req("POST", "/register", 200, f"New user registered: '{username}'")
    return jsonify({"status": "success", "message": f"Account '{username}' created. You can now log in."}), 200


# ══════════════════════════════════════════════════════════════════════════════
# UPLOAD — POST /upload  (requires login)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/upload", methods=["POST"])
@login_required
def upload_file():
    """
    POST /upload — Upload, encrypt, summarize, store.
    Requires session cookie (login first).
    sender_id is now taken from session if not provided.
    """
    apply_delay()   # Simulate network latency if enabled

    if "file" not in request.files:
        log_req("POST", "/upload", 400, "No file part")
        return jsonify({"error": "No file part in request."}), 400

    file        = request.files["file"]
    receiver_id = request.form.get("receiver_id", "").strip()
    sender_id   = session.get("username", request.form.get("sender_id", "anonymous"))

    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400
    if not receiver_id:
        return jsonify({"error": "receiver_id is required."}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": f"File type not allowed."}), 400

    original_filename = secure_filename(file.filename)
    unique_id   = str(uuid.uuid4())[:8]
    stored_name = f"{unique_id}_{original_filename}"
    upload_path = os.path.join(UPLOAD_FOLDER, stored_name)
    file.save(upload_path)

    # Encrypt
    encrypted_path = os.path.join(ENCRYPTED_FOLDER, stored_name + ".enc")
    try:
        encrypt_file(upload_path, encrypted_path, stored_name)
    except Exception as e:
        return jsonify({"error": f"Encryption failed: {e}"}), 500

    # Cloud upload (Google Drive) if enabled
    drive_file_id = None
    if ENABLE_DRIVE:
        try:
            drive_file_id = upload_to_drive(encrypted_path, stored_name + ".enc")
            print(f"[DRIVE] ✅ Uploaded to Google Drive: {drive_file_id}")
        except Exception as e:
            print(f"[DRIVE] ⚠️  Drive upload failed: {e}")

    # AI Summary
    try:
        summary = summarize_file(upload_path)
    except Exception as e:
        summary = f"Summary unavailable: {e}"

    # Metadata
    metadata = load_metadata()
    metadata[stored_name] = {
        "original_name":  original_filename,
        "stored_name":    stored_name,
        "sender_id":      sender_id,
        "receiver_id":    receiver_id,
        "upload_time":    datetime.now().isoformat(),
        "summary":        summary,
        "encrypted_path": encrypted_path,
        "file_size_kb":   round(os.path.getsize(upload_path) / 1024, 2),
        "drive_file_id":  drive_file_id,
        "storage":        "google_drive" if drive_file_id else "local",
    }
    save_metadata(metadata)

    log_req("POST", "/upload", 200, f"file={stored_name} receiver={receiver_id} storage={'drive' if drive_file_id else 'local'}")
    return jsonify({
        "status":        "success",
        "file_id":       stored_name,
        "original_name": original_filename,
        "receiver_id":   receiver_id,
        "sender_id":     sender_id,
        "summary":       summary,
        "file_size_kb":  metadata[stored_name]["file_size_kb"],
        "storage":       metadata[stored_name]["storage"],
    }), 200


# ══════════════════════════════════════════════════════════════════════════════
# FILE LIST — GET /files/<receiver_id>
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/files/<receiver_id>", methods=["GET"])
@login_required
def list_files(receiver_id):
    """
    GET /files/<receiver_id>
    Returns all files for this receiver.
    Users can only see their own files (unless they're 'admin').
    """
    apply_delay()
    current_user = session["username"]

    # Authorization: only see your own files (unless admin)
    if current_user != receiver_id and current_user != "admin":
        log_req("GET", f"/files/{receiver_id}", 403, f"'{current_user}' tried to access '{receiver_id}' files")
        return jsonify({"error": "403 Forbidden — You can only access your own files."}), 403

    metadata = load_metadata()
    files = [
        {
            "file_id":       v["stored_name"],
            "original_name": v["original_name"],
            "sender_id":     v["sender_id"],
            "upload_time":   v["upload_time"],
            "summary":       v["summary"],
            "file_size_kb":  v["file_size_kb"],
            "storage":       v.get("storage", "local"),
        }
        for v in metadata.values()
        if v.get("receiver_id") == receiver_id
    ]
    files.sort(key=lambda x: x["upload_time"], reverse=True)
    log_req("GET", f"/files/{receiver_id}", 200, f"{len(files)} files")
    return jsonify({"receiver_id": receiver_id, "files": files, "count": len(files)}), 200


# ══════════════════════════════════════════════════════════════════════════════
# DOWNLOAD — GET /download/<file_id>
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/download/<file_id>", methods=["GET"])
@login_required
def download_file(file_id):
    """GET /download/<file_id> — Decrypt and stream file to receiver."""
    apply_delay()
    metadata = load_metadata()
    if file_id not in metadata:
        return jsonify({"error": "File not found."}), 404

    entry        = metadata[file_id]
    current_user = session["username"]

    # Authorization check
    if current_user != entry["receiver_id"] and current_user != "admin":
        log_req("GET", f"/download/{file_id}", 403, f"'{current_user}' tried to download file for '{entry['receiver_id']}'")
        return jsonify({"error": "403 Forbidden — This file is not addressed to you."}), 403

    encrypted_path = entry["encrypted_path"]

    # If Google Drive storage, download encrypted file first
    if ENABLE_DRIVE and entry.get("drive_file_id"):
        try:
            download_from_drive(entry["drive_file_id"], encrypted_path)
            print(f"[DRIVE] ✅ Downloaded from Google Drive: {entry['drive_file_id']}")
        except Exception as e:
            return jsonify({"error": f"Drive download failed: {e}"}), 500

    if not os.path.exists(encrypted_path):
        return jsonify({"error": "Encrypted file not found on disk."}), 404

    decrypted_path = os.path.join(DECRYPTED_FOLDER, entry["original_name"])
    if not decrypt_file(encrypted_path, decrypted_path, file_id):
        return jsonify({"error": "Decryption failed."}), 500

    log_req("GET", f"/download/{file_id}", 200, f"→ {entry['original_name']}")
    return send_file(decrypted_path, as_attachment=True, download_name=entry["original_name"])


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY — GET /summary/<file_id>
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/summary/<file_id>", methods=["GET"])
@login_required
def get_summary(file_id):
    """GET /summary/<file_id> — Return pre-generated AI summary."""
    metadata = load_metadata()
    if file_id not in metadata:
        return jsonify({"error": "File not found."}), 404
    entry = metadata[file_id]
    log_req("GET", f"/summary/{file_id}", 200)
    return jsonify({
        "file_id":       file_id,
        "original_name": entry["original_name"],
        "summary":       entry["summary"],
        "upload_time":   entry["upload_time"],
        "sender_id":     entry["sender_id"],
    }), 200


# ══════════════════════════════════════════════════════════════════════════════
# STATS — GET /stats  (NEW)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/stats", methods=["GET"])
def get_stats():
    """
    GET /stats — Server statistics endpoint.

    Returns:
      - Total files uploaded
      - Total storage used (KB)
      - Number of unique users (senders + receivers)
      - Number of encrypted files on disk
      - Storage type breakdown (local vs drive)
      - Server uptime info
      - Current delay simulation setting

    NETWORKING NOTE:
      This is a monitoring / observability endpoint.
      In production, tools like Prometheus scrape endpoints like this
      to track server health over time.
    """
    metadata   = load_metadata()
    users      = load_users()
    enc_files  = len([f for f in os.listdir(ENCRYPTED_FOLDER) if f.endswith(".enc")])

    total_size_kb  = sum(v.get("file_size_kb", 0) for v in metadata.values())
    senders        = set(v["sender_id"]   for v in metadata.values())
    receivers      = set(v["receiver_id"] for v in metadata.values())
    local_count    = sum(1 for v in metadata.values() if v.get("storage", "local") == "local")
    drive_count    = sum(1 for v in metadata.values() if v.get("storage") == "google_drive")

    log_req("GET", "/stats", 200, f"{len(metadata)} files | {round(total_size_kb,1)} KB")
    return jsonify({
        "total_files":        len(metadata),
        "total_size_kb":      round(total_size_kb, 2),
        "total_size_mb":      round(total_size_kb / 1024, 3),
        "encrypted_on_disk":  enc_files,
        "registered_users":   len(users),
        "unique_senders":     len(senders),
        "unique_receivers":   len(receivers),
        "storage_local":      local_count,
        "storage_drive":      drive_count,
        "drive_enabled":      ENABLE_DRIVE,
        "delay_simulation_ms": _simulate_delay_ms,
        "server_time":        datetime.now().isoformat(),
    }), 200


# ══════════════════════════════════════════════════════════════════════════════
# NETWORK DELAY SIMULATION — GET /simulate-delay/<ms>  (NEW)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/simulate-delay/<int:ms>", methods=["GET"])
def simulate_delay(ms):
    """
    GET /simulate-delay/<ms>
    Sets a server-side delay (in milliseconds) added to every request.

    NETWORKING CONCEPT — Network Latency:
      Latency = time for a packet to travel from source to destination.
      Affected by: physical distance, router hops, congestion, bandwidth.
      This endpoint lets you simulate high-latency networks during demo.

    Usage:
      GET /simulate-delay/500   → adds 500ms delay to every request
      GET /simulate-delay/0     → disables simulation (reset)

    Useful for showing:
      - How latency affects user experience
      - Why CDNs (Content Delivery Networks) are placed close to users
      - Network quality impact on file upload speed
    """
    global _simulate_delay_ms
    ms = max(0, min(ms, 5000))   # clamp between 0ms and 5000ms
    _simulate_delay_ms = ms
    status = "enabled" if ms > 0 else "disabled"
    log_req("GET", f"/simulate-delay/{ms}", 200, f"Network delay {status} — {ms}ms added to every request")
    return jsonify({
        "status":        "success",
        "delay_ms":      ms,
        "simulation":    status,
        "message":       f"Every request will now have an artificial {ms}ms delay." if ms > 0 else "Delay simulation disabled.",
        "concept":       "Network Latency — simulating slow network conditions"
    }), 200


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH — GET /health
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status":         "ok",
        "server":         "Secure File Share Server",
        "version":        "2.0.0",
        "time":           datetime.now().isoformat(),
        "drive_enabled":  ENABLE_DRIVE,
        "delay_ms":       _simulate_delay_ms,
        "auth_required":  True,
        "https_note":     "Run via ngrok for HTTPS: ngrok http 5000",
    }), 200


# ── Error Handlers ─────────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "404 Not Found"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "405 Method Not Allowed"}), 405

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "413 Payload Too Large — max 50 MB"}), 413

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": f"500 Internal Server Error — {e}"}), 500


# ── Entry Point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    seed_users()
    print("=" * 65)
    print("  🔒 Secure File Share Server v2.0")
    print("  📡 HTTP  → http://localhost:5000")
    print("  🔐 HTTPS → run: ngrok http 5000")
    print("  👤 Demo users: alice/alice123  bob/bob123  admin/admin123")
    print("  ☁️  Google Drive:", "ENABLED" if ENABLE_DRIVE else "DISABLED (local storage)")
    print("=" * 65)
    app.run(host="0.0.0.0", port=8000)
