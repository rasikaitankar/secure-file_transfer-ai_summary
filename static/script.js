/**
 * static/script.js
 * -----------------
 * Person 4 – Frontend UI
 *
 * LIVE NETWORK LOG:
 *  - Sender mode  → logs every step: file selected, validating, uploading,
 *                   encrypting (server), summarizing (server), sent ✅
 *  - Receiver mode → logs: fetching file list, files found, downloading,
 *                    decrypting (server), summary fetched ✅
 */

// ── Panel references ──────────────────────────────────────────────────────────
const senderPanel   = document.getElementById("senderPanel");
const receiverPanel = document.getElementById("receiverPanel");
const btnSender     = document.getElementById("btnSender");
const btnReceiver   = document.getElementById("btnReceiver");

// ── Mode Toggle ───────────────────────────────────────────────────────────────
btnSender.addEventListener("click", () => {
  senderPanel.classList.remove("d-none");
  receiverPanel.classList.add("d-none");
  btnSender.classList.add("active");
  btnReceiver.classList.remove("active");
  logNetwork("INFO", "Mode switched", "→", "Sender Mode activated");
});

btnReceiver.addEventListener("click", () => {
  senderPanel.classList.add("d-none");
  receiverPanel.classList.remove("d-none");
  btnReceiver.classList.add("active");
  btnSender.classList.remove("active");
  logNetwork("INFO", "Mode switched", "→", "Receiver Mode activated");
});

// ── Drag-and-Drop & File Select ───────────────────────────────────────────────
const dropZone  = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const fileLabel = document.getElementById("fileLabel");

dropZone.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("dragover");
  const files = e.dataTransfer.files;
  if (files.length > 0) {
    fileInput.files = files;
    fileLabel.textContent = `📄 ${files[0].name} (${formatBytes(files[0].size)})`;
    logNetwork("INFO", "File selected", "→", `${files[0].name} (${formatBytes(files[0].size)}) via drag-and-drop`);
  }
});

fileInput.addEventListener("change", () => {
  if (fileInput.files.length > 0) {
    const f = fileInput.files[0];
    fileLabel.textContent = `📄 ${f.name} (${formatBytes(f.size)})`;
    logNetwork("INFO", "File selected", "→", `${f.name} (${formatBytes(f.size)})`);
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

  // ── Step 1: Validate ──────────────────────────────────────────────────────
  logNetwork("INFO", "Validating", "→", "Checking file and receiver ID…");

  if (!file) {
    logNetwork("ERROR", "Validation", "✗", "No file selected");
    return showAlert(uploadStatus, "Please select a file first.", "danger");
  }
  if (!receiverId) {
    logNetwork("ERROR", "Validation", "✗", "Receiver ID is missing");
    return showAlert(uploadStatus, "Receiver ID is required.", "danger");
  }

  logNetwork("INFO", "Validation", "✓", `File: ${file.name} | Receiver: ${receiverId} | Sender: ${senderId}`);

  // Build multipart/form-data
  const formData = new FormData();
  formData.append("file", file);
  formData.append("receiver_id", receiverId);
  formData.append("sender_id", senderId);

  // ── Step 2: Upload ────────────────────────────────────────────────────────
  progressWrap.classList.remove("d-none");
  uploadResult.classList.add("d-none");
  setProgress(10);

  logNetwork("POST", "/upload", "pending", `Sending HTTP POST with file → server…`);

  try {
    setProgress(25);
    const startTime = performance.now();

    const response = await fetch("/upload", {
      method: "POST",
      body: formData,
    });

    setProgress(60);
    logNetwork("INFO", "Server processing", "→", "Encrypting file with AES-256-CBC…");
    setProgress(75);
    logNetwork("INFO", "Server processing", "→", "Generating AI summary (BART model)…");
    setProgress(90);
    logNetwork("INFO", "Server processing", "→", "Saving metadata to storage…");

    const elapsed = Math.round(performance.now() - startTime);
    const data    = await response.json();
    setProgress(100);

    if (response.ok) {
      // ── Success ────────────────────────────────────────────────────────
      logNetwork("POST", "/upload", response.status, `${elapsed}ms — HTTP ${response.status} OK`);
      logNetwork("INFO", "Encryption", "✓", `File encrypted → encrypted/${data.file_id}.enc`);
      logNetwork("INFO", "AI Summary", "✓", `Summary generated (${data.summary?.length || 0} chars)`);
      logNetwork("INFO", "Storage", "✓", `File mapped to receiver: ${receiverId}`);
      logNetwork("INFO", "SENT", "→", `${file.name} successfully sent to ${receiverId}`);

      showAlert(uploadStatus, "✅ File uploaded & encrypted successfully!", "success");
      displayUploadResult(data);
      uploadForm.reset();
      fileLabel.textContent = "Drag & drop or click to choose a file";
    } else {
      // ── Error ──────────────────────────────────────────────────────────
      logNetwork("POST", "/upload", response.status, `❌ ${data.error || response.statusText}`);
      showAlert(uploadStatus, `❌ Error: ${data.error || "Upload failed"}`, "danger");
    }
  } catch (err) {
    logNetwork("POST", "/upload", "ERROR", `Network error: ${err.message}`);
    showAlert(uploadStatus, `❌ Network error: ${err.message}`, "danger");
  } finally {
    setTimeout(() => progressWrap.classList.add("d-none"), 1000);
  }
});

function displayUploadResult(data) {
  document.getElementById("resFileName").textContent = data.original_name;
  document.getElementById("resFileId").textContent   = data.file_id;
  document.getElementById("resReceiver").textContent = data.receiver_id;
  document.getElementById("resFileSize").textContent = data.file_size_kb + " KB";
  document.getElementById("resSummary").textContent  = data.summary;
  uploadResult.classList.remove("d-none");
}

// ── Fetch Files (GET /files/<receiver_id>) ────────────────────────────────────
const fetchForm    = document.getElementById("fetchForm");
const fetchStatus  = document.getElementById("fetchStatus");
const fileListWrap = document.getElementById("fileListWrap");
const fileListBody = document.getElementById("fileListBody");
const fileCount    = document.getElementById("fileCount");

fetchForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const rid = document.getElementById("fetchReceiverId").value.trim();

  if (!rid) {
    logNetwork("ERROR", "Validation", "✗", "Receiver ID is empty");
    return showAlert(fetchStatus, "Enter a Receiver ID.", "danger");
  }

  logNetwork("INFO", "Receiver ID", "→", `Looking up files for: ${rid}`);
  logNetwork("GET", `/files/${rid}`, "pending", "Sending HTTP GET request to server…");

  try {
    const startTime = performance.now();
    const response  = await fetch(`/files/${encodeURIComponent(rid)}`);
    const elapsed   = Math.round(performance.now() - startTime);
    const data      = await response.json();

    logNetwork("GET", `/files/${rid}`, response.status, `${elapsed}ms — HTTP ${response.status} OK`);

    if (!response.ok) {
      logNetwork("ERROR", `/files/${rid}`, "✗", data.error);
      return showAlert(fetchStatus, `❌ ${data.error}`, "danger");
    }

    if (data.count === 0) {
      logNetwork("INFO", "File List", "→", `No files found for receiver: ${rid}`);
    } else {
      logNetwork("INFO", "File List", "✓", `${data.count} file(s) found for ${rid}`);
      data.files.forEach((f, i) => {
        logNetwork("INFO", `File ${i + 1}`, "→", `${f.original_name} from ${f.sender_id} (${f.file_size_kb} KB)`);
      });
    }

    renderFileList(data.files);
  } catch (err) {
    logNetwork("GET", `/files/${rid}`, "ERROR", `Network error: ${err.message}`);
    showAlert(fetchStatus, `❌ Network error: ${err.message}`, "danger");
  }
});

function renderFileList(files) {
  fileListBody.innerHTML = "";

  if (files.length === 0) {
    fileCount.textContent = "No files found for this receiver.";
    fileListWrap.classList.remove("d-none");
    return;
  }

  fileCount.textContent = `${files.length} file(s) ready for download.`;

  files.forEach((f) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><span class="badge-filename">📄 ${escHtml(f.original_name)}</span></td>
      <td>${escHtml(f.sender_id)}</td>
      <td>${new Date(f.upload_time).toLocaleString()}</td>
      <td>${f.file_size_kb} KB</td>
      <td>
        <button class="btn btn-sm btn-outline-info me-1" onclick="viewSummary('${f.file_id}')">
          📝 Summary
        </button>
        <button class="btn btn-sm btn-success" onclick="downloadFile('${f.file_id}', '${escHtml(f.original_name)}')">
          ⬇ Download
        </button>
      </td>
    `;
    fileListBody.appendChild(tr);
  });

  fileListWrap.classList.remove("d-none");
}

// ── Download (GET /download/<file_id>) ────────────────────────────────────────
async function downloadFile(fileId, originalName) {
  logNetwork("INFO", "Download", "→", `Requested: ${originalName}`);
  logNetwork("GET", `/download/${fileId}`, "pending", "Sending HTTP GET to server…");

  try {
    const startTime = performance.now();
    const response  = await fetch(`/download/${encodeURIComponent(fileId)}`);
    const elapsed   = Math.round(performance.now() - startTime);

    logNetwork("GET", `/download/${fileId}`, response.status, `${elapsed}ms — HTTP ${response.status}`);

    if (!response.ok) {
      const err = await response.json();
      logNetwork("ERROR", "Download", "✗", err.error);
      return alert(`Download failed: ${err.error}`);
    }

    logNetwork("INFO", "Decryption", "→", "Server decrypting AES-256-CBC file…");
    logNetwork("INFO", "Decryption", "✓", `File decrypted → streaming to browser`);

    const blob = await response.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = originalName;
    a.click();
    URL.revokeObjectURL(url);

    logNetwork("INFO", "✅ DOWNLOADED", "→", `${originalName} saved to your device`);
  } catch (err) {
    logNetwork("GET", `/download/${fileId}`, "ERROR", `Network error: ${err.message}`);
    alert(`Network error: ${err.message}`);
  }
}

// ── View Summary (GET /summary/<file_id>) ─────────────────────────────────────
const summaryModal      = new bootstrap.Modal(document.getElementById("summaryModal"));
const summaryModalBody  = document.getElementById("summaryModalBody");
const summaryModalTitle = document.getElementById("summaryModalLabel");

async function viewSummary(fileId) {
  logNetwork("INFO", "Summary", "→", `Requesting AI summary for file ID: ${fileId}`);
  logNetwork("GET", `/summary/${fileId}`, "pending", "Fetching from server…");

  try {
    const startTime = performance.now();
    const response  = await fetch(`/summary/${encodeURIComponent(fileId)}`);
    const elapsed   = Math.round(performance.now() - startTime);
    const data      = await response.json();

    logNetwork("GET", `/summary/${fileId}`, response.status, `${elapsed}ms — HTTP ${response.status}`);

    if (!response.ok) {
      logNetwork("ERROR", "Summary", "✗", data.error);
      return alert(data.error);
    }

    logNetwork("INFO", "AI Summary", "✓", `Summary loaded for: ${data.original_name}`);

    summaryModalTitle.textContent = `📝 AI Summary — ${data.original_name}`;
    summaryModalBody.innerHTML = `
      <p class="text-muted mb-1">
        <small>Uploaded by <strong>${escHtml(data.sender_id)}</strong>
        on ${new Date(data.upload_time).toLocaleString()}</small>
      </p>
      <hr/>
      <p class="summary-text">${escHtml(data.summary)}</p>
    `;
    summaryModal.show();
  } catch (err) {
    logNetwork("GET", `/summary/${fileId}`, "ERROR", `Network error: ${err.message}`);
    alert(`Error: ${err.message}`);
  }
}

// ── Health Check ──────────────────────────────────────────────────────────────
async function checkHealth() {
  logNetwork("GET", "/health", "pending", "Pinging server…");
  try {
    const r = await fetch("/health");
    const d = await r.json();
    logNetwork("GET", "/health", r.status, `Server: ${d.server} | Time: ${d.time}`);
    logNetwork("INFO", "Connection", "✓", "Server is online and responding");
  } catch (e) {
    logNetwork("GET", "/health", "ERROR", `Server unreachable: ${e.message}`);
  }
}

// Auto-ping on page load
window.addEventListener("load", () => {
  logNetwork("INFO", "App loaded", "→", "SecureFileShare ready. Pinging server…");
  checkHealth();
});

// ── Network Log ───────────────────────────────────────────────────────────────
// Writes to correct panel log: #networkLog (sender) or #networkLogReceiver (receiver)
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
    <span class="log-method">${escHtml(method)}</span>
    <span class="log-url">${escHtml(String(endpoint))}</span>
    <span class="log-status">${escHtml(String(status))}</span>
    <span class="log-detail">${escHtml(String(detail))}</span>
  `;

  // Write to whichever panel is currently active
  const senderLog   = document.getElementById("networkLog");
  const receiverLog = document.getElementById("networkLogReceiver");
  const activeLog   = receiverPanel.classList.contains("d-none") ? senderLog : receiverLog;

  if (activeLog) {
    activeLog.appendChild(line);
    activeLog.scrollTop = activeLog.scrollHeight;
  }
}

// ── Utilities ─────────────────────────────────────────────────────────────────
function showAlert(container, message, type) {
  container.innerHTML = `<div class="alert alert-${type} py-2">${message}</div>`;
  container.classList.remove("d-none");
}

function setProgress(pct) {
  progressBar.style.width = pct + "%";
  progressBar.setAttribute("aria-valuenow", pct);
  progressBar.textContent = pct + "%";
}

function formatBytes(bytes) {
  if (bytes < 1024)    return bytes + " B";
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / 1048576).toFixed(1) + " MB";
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}