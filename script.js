/**
 * static/script.js  v2.0
 * ─────────────────────────────────────────────────────────────────
 * NEW: logout, stats panel, delay simulator, session /me demo,
 *      storage badge in file list, login redirect on 401
 */

// ── Panel references ──────────────────────────────────────────────────────────
const senderPanel   = document.getElementById("senderPanel");
const receiverPanel = document.getElementById("receiverPanel");
const statsPanel    = document.getElementById("statsPanel");
const btnSender     = document.getElementById("btnSender");
const btnReceiver   = document.getElementById("btnReceiver");
const btnStats      = document.getElementById("btnStats");

// ── Mode switching ────────────────────────────────────────────────────────────
function setMode(mode) {
  senderPanel.classList.add("d-none");
  receiverPanel.classList.add("d-none");
  statsPanel.classList.add("d-none");
  btnSender.classList.remove("active");
  btnReceiver.classList.remove("active");
  btnStats.classList.remove("active");

  if (mode === "sender")   { senderPanel.classList.remove("d-none");   btnSender.classList.add("active");   logNetwork("INFO","Mode","→","Sender Mode activated"); }
  if (mode === "receiver") { receiverPanel.classList.remove("d-none"); btnReceiver.classList.add("active"); logNetwork("INFO","Mode","→","Receiver Mode activated"); }
  if (mode === "stats")    { statsPanel.classList.remove("d-none");    btnStats.classList.add("active");    logNetwork("INFO","Mode","→","Stats & Tools panel opened"); loadStats(); }
}

// ── Drag-and-Drop ─────────────────────────────────────────────────────────────
const dropZone  = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const fileLabel = document.getElementById("fileLabel");

dropZone.addEventListener("click", () => fileInput.click());
dropZone.addEventListener("dragover",  (e) => { e.preventDefault(); dropZone.classList.add("dragover"); });
dropZone.addEventListener("dragleave", ()  => dropZone.classList.remove("dragover"));
dropZone.addEventListener("drop", (e) => {
  e.preventDefault(); dropZone.classList.remove("dragover");
  const files = e.dataTransfer.files;
  if (files.length > 0) {
    fileInput.files = files;
    fileLabel.textContent = `📄 ${files[0].name} (${formatBytes(files[0].size)})`;
    logNetwork("INFO","File selected","→",`${files[0].name} (${formatBytes(files[0].size)}) via drag-and-drop`);
  }
});
fileInput.addEventListener("change", () => {
  if (fileInput.files.length > 0) {
    const f = fileInput.files[0];
    fileLabel.textContent = `📄 ${f.name} (${formatBytes(f.size)})`;
    logNetwork("INFO","File selected","→",`${f.name} (${formatBytes(f.size)})`);
  }
});

// ── Upload (POST /upload) ─────────────────────────────────────────────────────
const uploadForm   = document.getElementById("uploadForm");
const uploadStatus = document.getElementById("uploadStatus");
const uploadResult = document.getElementById("uploadResult");
const progressWrap = document.getElementById("progressWrap");
const progressBar  = document.getElementById("progressBar");

uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const file       = fileInput.files[0];
  const receiverId = document.getElementById("receiverId").value.trim();
  const senderId   = document.getElementById("senderId").value.trim() || "anonymous";

  logNetwork("INFO","Validating","→","Checking file and receiver ID…");
  if (!file)       { logNetwork("ERROR","Validation","✗","No file selected"); return showAlert(uploadStatus, "Please select a file first.", "danger"); }
  if (!receiverId) { logNetwork("ERROR","Validation","✗","Receiver ID missing"); return showAlert(uploadStatus, "Receiver ID is required.", "danger"); }
  logNetwork("INFO","Validation","✓",`File: ${file.name} | Receiver: ${receiverId} | Sender: ${senderId}`);

  const formData = new FormData();
  formData.append("file", file);
  formData.append("receiver_id", receiverId);
  formData.append("sender_id", senderId);

  progressWrap.classList.remove("d-none");
  uploadResult.classList.add("d-none");
  setProgress(10);
  logNetwork("POST","/upload","pending","Sending HTTP POST with file → server…");

  try {
    setProgress(25);
    const startTime = performance.now();
    const response  = await fetch("/upload", { method: "POST", body: formData });

    setProgress(60);
    logNetwork("INFO","Server","→","Encrypting file with AES-256-CBC…");
    setProgress(75);
    logNetwork("INFO","Server","→","Generating AI summary (BART model)…");
    setProgress(90);
    logNetwork("INFO","Server","→","Saving metadata & session info…");

    const elapsed = Math.round(performance.now() - startTime);
    const data    = await response.json();
    setProgress(100);

    // Handle 401 — redirect to login
    if (response.status === 401) {
      logNetwork("POST","/upload", 401,"Not logged in — redirecting to /login");
      window.location.href = "/login";
      return;
    }

    if (response.ok) {
      logNetwork("POST","/upload", response.status,`${elapsed}ms — HTTP ${response.status} OK`);
      logNetwork("INFO","Encryption","✓",`File encrypted → encrypted/${data.file_id}.enc`);
      logNetwork("INFO","Storage","✓",`Stored: ${data.storage === "google_drive" ? "☁️ Google Drive" : "💾 Local"}`);
      logNetwork("INFO","AI Summary","✓",`Summary generated (${data.summary?.length || 0} chars)`);
      logNetwork("INFO","✅ SENT","→",`${file.name} successfully sent to ${receiverId}`);

      showAlert(uploadStatus, "✅ File uploaded & encrypted successfully!", "success");
      document.getElementById("resFileName").textContent = data.original_name;
      document.getElementById("resFileId").textContent   = data.file_id;
      document.getElementById("resReceiver").textContent = data.receiver_id;
      document.getElementById("resStorage").textContent  = data.storage === "google_drive" ? "☁️ Google Drive" : "💾 Local";
      document.getElementById("resSummary").textContent  = data.summary;
      uploadResult.classList.remove("d-none");
      uploadForm.reset();
      fileLabel.textContent = "Drag & drop or click to choose a file";
    } else {
      logNetwork("POST","/upload", response.status,`❌ ${data.error}`);
      showAlert(uploadStatus, `❌ ${data.error}`, "danger");
    }
  } catch (err) {
    logNetwork("POST","/upload","ERROR",`Network error: ${err.message}`);
    showAlert(uploadStatus, `❌ Network error: ${err.message}`, "danger");
  } finally {
    setTimeout(() => progressWrap.classList.add("d-none"), 1000);
  }
});

// ── Fetch Files (GET /files/<receiver_id>) ────────────────────────────────────
const fetchForm    = document.getElementById("fetchForm");
const fetchStatus  = document.getElementById("fetchStatus");
const fileListWrap = document.getElementById("fileListWrap");
const fileListBody = document.getElementById("fileListBody");
const fileCount    = document.getElementById("fileCount");

fetchForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const rid = document.getElementById("fetchReceiverId").value.trim();
  if (!rid) { logNetwork("ERROR","Validation","✗","Receiver ID empty"); return showAlert(fetchStatus,"Enter a Receiver ID.","danger"); }

  logNetwork("INFO","Receiver ID","→",`Looking up files for: ${rid}`);
  logNetwork("GET",`/files/${rid}`,"pending","Sending HTTP GET with session cookie…");

  try {
    const startTime = performance.now();
    const response  = await fetch(`/files/${encodeURIComponent(rid)}`);
    const elapsed   = Math.round(performance.now() - startTime);
    const data      = await response.json();

    logNetwork("GET",`/files/${rid}`, response.status,`${elapsed}ms — HTTP ${response.status}`);

    if (response.status === 401) { logNetwork("ERROR","Auth","✗","Session expired — redirecting"); window.location.href = "/login"; return; }
    if (response.status === 403) { logNetwork("ERROR","Auth","✗","403 Forbidden — not your files"); return showAlert(fetchStatus,`❌ ${data.error}`,"danger"); }
    if (!response.ok)            { logNetwork("ERROR",`/files/${rid}`,"✗", data.error); return showAlert(fetchStatus,`❌ ${data.error}`,"danger"); }

    logNetwork("INFO","Cookie","✓","Session cookie verified — access granted");
    if (data.count === 0) { logNetwork("INFO","File List","→",`No files found for: ${rid}`); }
    else { logNetwork("INFO","File List","✓",`${data.count} file(s) found for ${rid}`); }

    renderFileList(data.files);
  } catch (err) {
    logNetwork("GET",`/files/${rid}`,"ERROR",err.message);
    showAlert(fetchStatus,`❌ ${err.message}`,"danger");
  }
});

function renderFileList(files) {
  fileListBody.innerHTML = "";
  if (files.length === 0) { fileCount.textContent = "No files found."; fileListWrap.classList.remove("d-none"); return; }
  fileCount.textContent = `${files.length} file(s) ready.`;
  files.forEach((f) => {
    const storageIcon = f.storage === "google_drive" ? "☁️ Drive" : "💾 Local";
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><span class="badge-filename">📄 ${escHtml(f.original_name)}</span></td>
      <td>${escHtml(f.sender_id)}</td>
      <td style="font-size:0.8rem;">${new Date(f.upload_time).toLocaleString()}</td>
      <td>${f.file_size_kb} KB</td>
      <td style="font-size:0.78rem;">${storageIcon}</td>
      <td>
        <button class="btn btn-sm btn-outline-info me-1" onclick="viewSummary('${f.file_id}')">📝</button>
        <button class="btn btn-sm btn-success" onclick="downloadFile('${f.file_id}','${escHtml(f.original_name)}')">⬇</button>
      </td>`;
    fileListBody.appendChild(tr);
  });
  fileListWrap.classList.remove("d-none");
}

// ── Download ──────────────────────────────────────────────────────────────────
async function downloadFile(fileId, originalName) {
  logNetwork("INFO","Download","→",`Requested: ${originalName}`);
  logNetwork("GET",`/download/${fileId}`,"pending","Sending HTTP GET with session cookie…");
  try {
    const startTime = performance.now();
    const response  = await fetch(`/download/${encodeURIComponent(fileId)}`);
    const elapsed   = Math.round(performance.now() - startTime);
    logNetwork("GET",`/download/${fileId}`, response.status,`${elapsed}ms`);

    if (response.status === 401) { window.location.href = "/login"; return; }
    if (response.status === 403) { const e = await response.json(); logNetwork("ERROR","Auth","✗",e.error); return alert(e.error); }
    if (!response.ok)            { const e = await response.json(); logNetwork("ERROR","Download","✗",e.error); return alert(e.error); }

    logNetwork("INFO","Decryption","→","Server decrypting AES-256-CBC file…");
    const blob = await response.blob();
    logNetwork("INFO","Decryption","✓","File decrypted → streaming to browser");
    const url = URL.createObjectURL(blob);
    const a   = document.createElement("a");
    a.href = url; a.download = originalName; a.click();
    URL.revokeObjectURL(url);
    logNetwork("INFO","✅ DOWNLOADED","→",`${originalName} saved to your device`);
  } catch (err) {
    logNetwork("GET",`/download/${fileId}`,"ERROR",err.message);
    alert(err.message);
  }
}

// ── View Summary ──────────────────────────────────────────────────────────────
const summaryModal      = new bootstrap.Modal(document.getElementById("summaryModal"));
const summaryModalBody  = document.getElementById("summaryModalBody");
const summaryModalTitle = document.getElementById("summaryModalLabel");

async function viewSummary(fileId) {
  logNetwork("GET",`/summary/${fileId}`,"pending","Fetching AI summary…");
  try {
    const response = await fetch(`/summary/${encodeURIComponent(fileId)}`);
    const data     = await response.json();
    logNetwork("GET",`/summary/${fileId}`, response.status, response.statusText);
    if (!response.ok) return alert(data.error);
    logNetwork("INFO","AI Summary","✓",`Loaded for: ${data.original_name}`);
    summaryModalTitle.textContent = `📝 AI Summary — ${data.original_name}`;
    summaryModalBody.innerHTML = `
      <p class="text-muted mb-1"><small>From <strong>${escHtml(data.sender_id)}</strong> on ${new Date(data.upload_time).toLocaleString()}</small></p>
      <hr/><p class="summary-text">${escHtml(data.summary)}</p>`;
    summaryModal.show();
  } catch (err) { alert(err.message); }
}

// ── Stats (GET /stats) ────────────────────────────────────────────────────────
async function loadStats() {
  logNetwork("GET","/stats","pending","Fetching server statistics…");
  try {
    const response = await fetch("/stats");
    const data     = await response.json();
    logNetwork("GET","/stats", response.status,`${data.total_files} files | ${data.total_size_kb} KB`);

    const grid = document.getElementById("statsGrid");
    grid.innerHTML = `
      <div class="col-6 col-md-4">${statCard("Total Files",     data.total_files)}</div>
      <div class="col-6 col-md-4">${statCard("Storage Used",    data.total_size_kb + " KB")}</div>
      <div class="col-6 col-md-4">${statCard("Encrypted on Disk", data.encrypted_on_disk)}</div>
      <div class="col-6 col-md-4">${statCard("Registered Users",  data.registered_users)}</div>
      <div class="col-6 col-md-4">${statCard("Unique Senders",    data.unique_senders)}</div>
      <div class="col-6 col-md-4">${statCard("Unique Receivers",  data.unique_receivers)}</div>
      <div class="col-6 col-md-4">${statCard("Local Storage",     data.storage_local)}</div>
      <div class="col-6 col-md-4">${statCard("Drive Storage",     data.storage_drive)}</div>
      <div class="col-6 col-md-4">${statCard("Delay (ms)",        data.delay_simulation_ms)}</div>
      <div class="col-12">
        <div style="font-size:0.72rem;color:var(--text-muted);font-family:var(--mono);text-align:center;margin-top:6px;">
          Server time: ${data.server_time} | Drive: ${data.drive_enabled ? "✅ Enabled" : "❌ Disabled"}
        </div>
      </div>
    `;
  } catch (err) {
    logNetwork("GET","/stats","ERROR",err.message);
  }
}

function statCard(label, value) {
  return `<div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:12px 10px;text-align:center;">
    <div style="font-size:1.3rem;font-weight:700;color:var(--accent);font-family:var(--mono);">${value}</div>
    <div style="font-size:0.7rem;color:var(--text-muted);margin-top:2px;">${label}</div>
  </div>`;
}

// ── Delay Simulator ───────────────────────────────────────────────────────────
async function setDelay(ms) {
  logNetwork("GET",`/simulate-delay/${ms}`,"pending",`Setting network delay to ${ms}ms…`);
  try {
    const response = await fetch(`/simulate-delay/${ms}`);
    const data     = await response.json();
    logNetwork("GET",`/simulate-delay/${ms}`, response.status, data.message);

    const el = document.getElementById("delayStatus");
    el.classList.remove("d-none");
    el.innerHTML = ms > 0
      ? `<div style="color:var(--accent3);font-size:0.85rem;">⏱️ ${data.message}</div>`
      : `<div style="color:var(--accent2);font-size:0.85rem;">✅ ${data.message}</div>`;

    // Highlight active button
    document.querySelectorAll(".delay-btn").forEach(b => b.classList.remove("btn-warning","btn-outline-secondary"));
    event.target.classList.add(ms > 0 ? "btn-warning" : "btn-outline-secondary");
  } catch (err) {
    logNetwork("GET",`/simulate-delay/${ms}`,"ERROR",err.message);
  }
}

// ── Session /me demo ──────────────────────────────────────────────────────────
async function showMe() {
  logNetwork("GET","/me","pending","Reading session cookie → asking server who I am…");
  try {
    const response = await fetch("/me");
    const data     = await response.json();
    logNetwork("GET","/me", response.status,`logged_in=${data.logged_in} user=${data.username || "none"}`);

    const el = document.getElementById("meResult");
    if (data.logged_in) {
      el.innerHTML = `<div class="result-box mt-2">
        <div class="result-label">Username from cookie</div>
        <div class="result-value">${escHtml(data.username)}</div>
        <div class="result-label mt-2">Login time</div>
        <div class="result-value">${data.login_time}</div>
        <div style="font-size:0.72rem;color:var(--accent2);margin-top:8px;">✅ Server read your session cookie — no password needed!</div>
      </div>`;
    } else {
      el.innerHTML = `<div class="result-box mt-2" style="border-left-color:var(--danger);">
        <div style="color:var(--danger);font-size:0.85rem;">❌ Not logged in — no session cookie found</div>
      </div>`;
    }
  } catch (err) {
    logNetwork("GET","/me","ERROR",err.message);
  }
}

// ── Logout ────────────────────────────────────────────────────────────────────
async function doLogout() {
  logNetwork("GET","/logout","pending","Clearing session cookie…");
  const r = await fetch("/logout", { method: "POST" });
  const d = await r.json();
  logNetwork("GET","/logout", r.status,"Session cleared — redirecting to /login");
  window.location.href = "/login";
}

// ── Health Check ──────────────────────────────────────────────────────────────
async function checkHealth() {
  logNetwork("GET","/health","pending","Pinging server…");
  try {
    const r = await fetch("/health");
    const d = await r.json();
    logNetwork("GET","/health", r.status,`Server: ${d.server} | v${d.version} | delay=${d.delay_ms}ms`);
    logNetwork("INFO","Connection","✓","Server is online and responding");
  } catch (e) {
    logNetwork("GET","/health","ERROR",`Server unreachable: ${e.message}`);
  }
}

// ── Network Log ───────────────────────────────────────────────────────────────
function logNetwork(method, endpoint, status, detail) {
  const isError   = method === "ERROR" || status === "ERROR" || (typeof status === "number" && status >= 400);
  const isPending = status === "pending";
  const isInfo    = method === "INFO";
  const color     = isError ? "log-error" : isPending ? "log-pending" : isInfo ? "log-info" : "log-ok";

  const ts   = new Date().toLocaleTimeString();
  const line = document.createElement("div");
  line.className = `log-line ${color}`;
  line.innerHTML = `
    <span class="log-time">${ts}</span>
    <span class="log-method">${escHtml(String(method))}</span>
    <span class="log-url">${escHtml(String(endpoint))}</span>
    <span class="log-status">${escHtml(String(status))}</span>
    <span class="log-detail">${escHtml(String(detail || ""))}</span>`;

  const senderLog   = document.getElementById("networkLog");
  const receiverLog = document.getElementById("networkLogReceiver");

  // Write to active panel log; stats panel writes to sender log
  const useReceiver = receiverPanel && !receiverPanel.classList.contains("d-none");
  const activeLog   = useReceiver ? receiverLog : senderLog;

  if (activeLog) { activeLog.appendChild(line); activeLog.scrollTop = activeLog.scrollHeight; }
}

// ── Auto-init ─────────────────────────────────────────────────────────────────
window.addEventListener("load", () => {
  logNetwork("INFO","App loaded","→","SecureFileShare v2.0 ready");
  checkHealth();
});

// ── Utilities ─────────────────────────────────────────────────────────────────
function showAlert(el, msg, type) {
  el.innerHTML = `<div class="alert alert-${type} py-2">${msg}</div>`;
  el.classList.remove("d-none");
}
function setProgress(pct) {
  progressBar.style.width = pct + "%";
  progressBar.setAttribute("aria-valuenow", pct);
  progressBar.textContent = pct + "%";
}
function formatBytes(b) {
  if (b < 1024) return b + " B";
  if (b < 1048576) return (b/1024).toFixed(1) + " KB";
  return (b/1048576).toFixed(1) + " MB";
}
function escHtml(s) {
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
