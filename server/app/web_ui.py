def get_embedded_ui_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>CONNECTY - Peer-to-Peer Home Sharing</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    body { background-color: #0b0f19; color: #e2e8f0; font-family: system-ui, -apple-system, sans-serif; }
    .glass { background: rgba(17, 24, 39, 0.75); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }
    .glass-card { background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255, 255, 255, 0.05); }
    .glow-cyan { box-shadow: 0 0 25px -5px rgba(6, 182, 212, 0.3); }
    .progress-bar-fill { transition: width 0.2s ease-in-out; }
  </style>
</head>
<body class="min-h-screen flex flex-col">
  <!-- Top Navigation Bar -->
  <header class="glass sticky top-0 z-50 px-4 py-3 border-b border-slate-800 flex items-center justify-between">
    <div class="flex items-center space-x-3">
      <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-white font-bold shadow-lg">
        <i class="fa-solid fa-network-wired text-lg"></i>
      </div>
      <div>
        <h1 class="text-lg font-bold tracking-tight text-white flex items-center gap-2">
          CONNECTY <span id="device-badge" class="text-xs px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800">P2P LAN</span>
        </h1>
        <p id="sub-header" class="text-xs text-slate-400">Direct Home File Sharing</p>
      </div>
    </div>
    
    <div class="flex items-center space-x-2">
      <span id="auth-status" class="text-xs px-2.5 py-1 rounded-full bg-slate-800 text-slate-400 border border-slate-700 flex items-center gap-1.5">
        <span class="w-2 h-2 rounded-full bg-yellow-500 animate-pulse"></span> Connecting
      </span>
      <button onclick="toggleModal('info-modal')" class="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition">
        <i class="fa-solid fa-qrcode text-lg"></i>
      </button>
    </div>
  </header>

  <!-- Main Container -->
  <main class="flex-1 max-w-5xl w-full mx-auto p-4 sm:p-6 space-y-6">

    <!-- Admin Pairing Banner / QR Code Widget (Visible on Laptop or Unpaired Phones) -->
    <section id="pairing-section" class="glass rounded-2xl p-5 glow-cyan border-cyan-500/20">
      <div class="flex flex-col md:flex-row items-center justify-between gap-6">
        <div class="space-y-2 text-center md:text-left flex-1">
          <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-400 text-xs font-semibold">
            <i class="fa-solid fa-shield-halved"></i> Fast Secure Device Pairing
          </div>
          <h2 class="text-xl sm:text-2xl font-bold text-white">Connect Your Android Phone</h2>
          <p class="text-sm text-slate-300">
            Open your phone's camera to scan the QR code, or open this URL on your phone:
            <span id="lan-url-display" class="font-mono text-cyan-300 bg-slate-900/80 px-2 py-0.5 rounded text-xs select-all">Loading...</span>
          </p>
          <div class="flex flex-wrap items-center justify-center md:justify-start gap-3 pt-2">
            <div class="bg-slate-900 border border-slate-700 px-4 py-2 rounded-xl text-center">
              <span class="text-xs text-slate-400 uppercase tracking-wider block">Pairing PIN</span>
              <span id="pin-display" class="text-2xl font-extrabold tracking-widest text-cyan-400 font-mono">------</span>
            </div>
            <button onclick="refreshPin()" class="px-3 py-2 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl transition flex items-center gap-1.5">
              <i class="fa-solid fa-rotate"></i> New PIN
            </button>
          </div>
        </div>
        
        <div class="flex flex-col items-center p-3 bg-white rounded-2xl shadow-2xl">
          <img id="qr-image" src="" alt="Pairing QR Code" class="w-36 h-36 object-contain">
          <span class="text-[10px] text-slate-700 font-medium mt-1">Scan with Phone Camera</span>
        </div>
      </div>
    </section>

    <!-- Phone Manual Pairing Input (Shows if opened on a phone that needs token) -->
    <section id="phone-pairing-card" class="hidden glass rounded-2xl p-6 border-cyan-500/30">
      <div class="max-w-md mx-auto text-center space-y-4">
        <div class="w-12 h-12 bg-cyan-500/10 text-cyan-400 rounded-2xl flex items-center justify-center mx-auto text-xl">
          <i class="fa-solid fa-key"></i>
        </div>
        <h3 class="text-xl font-bold text-white">Pair with Laptop</h3>
        <p class="text-xs text-slate-400">Enter the 6-digit PIN displayed on your laptop screen to authorize this device.</p>
        <div class="flex gap-2 justify-center">
          <input type="text" id="manual-pin-input" maxlength="6" placeholder="123456" 
                 class="w-48 text-center text-2xl font-mono tracking-widest bg-slate-900 border border-cyan-500/40 rounded-xl px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-cyan-400">
          <input type="text" id="manual-device-name-input" maxlength="100" placeholder="My Device" 
                 class="w-48 text-center text-2xl font-mono tracking-widest bg-slate-900 border border-cyan-500/40 rounded-xl px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-cyan-400">
          <select id="manual-pairing-type-input"
                 class="bg-slate-800 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 border border-slate-700 focus:outline-none">
            <option value="permanent">Permanent</option>
            <option value="temporary">Temporary (cleared on restart)</option>
          </select>
        </div>
        <button onclick="submitPairing()" class="w-full max-w-xs bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold py-2.5 rounded-xl transition shadow-lg shadow-cyan-500/20">
          Pair Device
        </button>
      </div>
    </section>

    <!-- Navigation Tabs -->
    <div class="flex border-b border-slate-800 space-x-2 text-sm font-medium">
      <button onclick="switchTab('files')" id="tab-files" class="tab-btn px-4 py-2.5 border-b-2 border-cyan-400 text-cyan-400 flex items-center gap-2">
        <i class="fa-regular fa-folder-open"></i> Shared Files
      </button>
      <button onclick="switchTab('transfers')" id="tab-transfers" class="tab-btn px-4 py-2.5 border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-2">
        <i class="fa-solid fa-arrow-up-from-bracket"></i> Upload & Transfers
      </button>
      <button onclick="switchTab('devices')" id="tab-devices" class="tab-btn px-4 py-2.5 border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-2">
        <i class="fa-solid fa-laptop-mobile"></i> Network Devices
      </button>
    </div>

    <!-- TAB 1: Shared Files Explorer -->
    <div id="view-files" class="space-y-4">
      <!-- Folder Selector & Breadcrumbs -->
      <div class="flex flex-wrap items-center justify-between gap-3 bg-slate-900/60 p-3 rounded-xl border border-slate-800">
        <div class="flex items-center space-x-2">
          <label class="text-xs text-slate-400">Share:</label>
          <select id="folder-select" onchange="onFolderChange(this.value)" class="bg-slate-800 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 border border-slate-700 focus:outline-none">
            <option value="default">Default Share</option>
          </select>
        </div>
        
        <div class="flex items-center space-x-2">
          <button id="btn-parent" onclick="goUpDirectory()" class="hidden px-2.5 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition flex items-center gap-1">
            <i class="fa-solid fa-level-up-alt"></i> Up
          </button>
          <button onclick="loadCurrentFolder()" class="p-1.5 text-xs text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition">
            <i class="fa-solid fa-rotate-right"></i>
          </button>
        </div>
      </div>

      <!-- Current Path Indicator -->
      <div class="text-xs font-mono text-slate-400 flex items-center justify-between px-1">
        <div class="flex items-center gap-2">
          <i class="fa-solid fa-folder text-cyan-400"></i>
          <span id="current-path-text">/</span>
        </div>
        <span id="file-count-badge" class="text-[11px] text-slate-500"></span>
      </div>

      <!-- Search and Sort Controls -->
      <div class="flex flex-wrap items-center gap-2 pt-1">
        <div class="relative flex-1 min-w-[160px]">
          <i class="fa-solid fa-magnifying-glass absolute left-3 top-2.5 text-xs text-slate-500"></i>
          <input type="text" id="file-search-input" oninput="applyFilterAndSort()" placeholder="Search files by name..." 
                 class="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-900 border border-slate-700 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500">
        </div>
        <div class="flex items-center space-x-1">
          <select id="file-sort-select" onchange="applyFilterAndSort()" class="bg-slate-900 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 border border-slate-700 focus:outline-none">
            <option value="name_asc">Name (A-Z)</option>
            <option value="name_desc">Name (Z-A)</option>
            <option value="time_desc">Time (Newest)</option>
            <option value="time_asc">Time (Oldest)</option>
            <option value="size_desc">Size (Largest)</option>
            <option value="size_asc">Size (Smallest)</option>
          </select>
        </div>
      </div>

      <!-- File List Grid/Table -->
      <div id="file-list-container" class="space-y-2">
        <!-- Rendered dynamically -->
        <div class="text-center py-12 text-slate-500">
          <i class="fa-solid fa-spinner fa-spin text-2xl mb-2 text-cyan-500"></i>
          <p>Loading files...</p>
        </div>
      </div>
    </div>

    <!-- TAB 2: Uploads & Transfers -->
    <div id="view-transfers" class="hidden space-y-6">
      <div class="glass-card rounded-2xl p-6 border border-slate-800 text-center space-y-4">
        <div class="w-16 h-16 rounded-full bg-cyan-500/10 text-cyan-400 flex items-center justify-center mx-auto text-2xl">
          <i class="fa-solid fa-cloud-arrow-up"></i>
        </div>
        <div>
          <h3 class="text-lg font-bold text-white">Upload Files to Laptop</h3>
          <p class="text-xs text-slate-400 mt-1">Chunked resumable transfers with SHA-256 verification</p>
        </div>
        
        <div class="max-w-md mx-auto">
          <input type="file" id="file-input" class="hidden" onchange="handleFileSelect(event)">
          <button onclick="document.getElementById('file-input').click()" class="w-full bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold py-3 px-6 rounded-xl transition shadow-lg shadow-cyan-500/20 flex items-center justify-center gap-2">
            <i class="fa-solid fa-plus"></i> Select File from Phone/Device
          </button>
        </div>
      </div>

      <!-- Active Transfers List -->
      <div class="space-y-3">
        <h4 class="text-sm font-semibold text-slate-300">Active Transfers</h4>
        <div id="transfers-container" class="space-y-3">
          <p class="text-xs text-slate-500 text-center py-6 bg-slate-900/30 rounded-xl border border-slate-800">
            No active uploads. Select a file above to test transfer.
          </p>
        </div>
      </div>
    </div>

    <!-- TAB 3: Network Devices -->
    <div id="view-devices" class="hidden space-y-6">
      <!-- Discovered Peers (mDNS) -->
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <h4 class="text-sm font-semibold text-slate-300 flex items-center gap-2">
            <i class="fa-solid fa-satellite-dish text-cyan-400"></i> Discovered Network Peers (mDNS)
          </h4>
          <button onclick="loadDiscoveredPeers()" class="text-xs text-cyan-400 hover:underline">Refresh</button>
        </div>
        <div id="discovered-peers-container" class="grid sm:grid-cols-2 gap-3">
          <!-- Rendered dynamically -->
        </div>
      </div>

      <!-- Paired Devices (Access Control) -->
      <div class="space-y-3">
        <h4 class="text-sm font-semibold text-slate-300 flex items-center gap-2">
          <i class="fa-solid fa-users text-cyan-400"></i> Paired & Authorized Devices
        </h4>
        <div id="paired-devices-container" class="space-y-2">
          <!-- Rendered dynamically -->
        </div>
      </div>
    </div>
  </main>

  <!-- In-Browser Media Player Modal (Supports Seek Range Requests) -->
  <div id="player-modal" class="fixed inset-0 bg-black/85 backdrop-blur-md z-50 hidden flex flex-col justify-center items-center p-4">
    <div class="w-full max-w-4xl bg-slate-900 rounded-2xl overflow-hidden border border-slate-800 shadow-2xl flex flex-col">
      <div class="px-4 py-3 bg-slate-800/80 flex items-center justify-between border-b border-slate-700">
        <h3 id="player-title" class="text-sm font-semibold text-white truncate max-w-md">Playing Media</h3>
        <button onclick="closePlayer()" class="text-slate-400 hover:text-white p-1">
          <i class="fa-solid fa-xmark text-lg"></i>
        </button>
      </div>
      <div class="bg-black aspect-video flex items-center justify-center">
        <video id="video-element" controls class="w-full h-full max-h-[70vh]"></video>
      </div>
      <div class="p-3 bg-slate-900 text-xs text-slate-400 flex justify-between items-center">
        <span>HTTP Range Streaming Active</span>
        <button id="player-dl-btn" class="text-cyan-400 hover:underline flex items-center gap-1">
          <i class="fa-solid fa-download"></i> Download Full File
        </button>
      </div>
    </div>
  </div>

  <script>
    // State
    let currentFolderId = "default";
    let currentSubpath = "";
    let activeToken = localStorage.getItem("connecty_token") || "";
    let isLocalAdmin = false;
    let deviceId = localStorage.getItem("connecty_device_id") || "device_" + Math.random().toString(36).substring(2, 10);
    localStorage.setItem("connecty_device_id", deviceId);

    // URL Param Pin Check
    const urlParams = new URLSearchParams(window.location.search);
    const pinFromUrl = urlParams.get("pin");
    if (pinFromUrl) {
      document.getElementById("manual-pin-input").value = pinFromUrl;
    }

    // Initialize
    async function init() {
      await checkDeviceIdentity();
      await loadPairingInfo();
      await loadFolders();
      await loadCurrentFolder();
      
      // Auto-refresh peers and pin periodically
      setInterval(loadDiscoveredPeers, 10000);
    }

    // Check device and token
    async function checkDeviceIdentity() {
      try {
        const res = await fetch("/api/v1/device");
        const data = await res.json();
        document.getElementById("lan-url-display").textContent = data.connection_url;
        
        // Test auth by listing devices or folders
        const authRes = await fetch("/api/v1/folders", {
          headers: activeToken ? { "X-Device-Token": activeToken } : {}
        });

        if (authRes.ok) {
          const authData = await authRes.json();
          document.getElementById("auth-status").innerHTML = '<span class="w-2 h-2 rounded-full bg-emerald-500"></span> Connected';
          document.getElementById("phone-pairing-card").classList.add("hidden");
          // Check if we are running as local admin
          if (!activeToken) {
            isLocalAdmin = true;
            document.getElementById("auth-status").innerHTML = '<span class="w-2 h-2 rounded-full bg-emerald-400"></span> Laptop Admin';
          }
        } else {
          document.getElementById("auth-status").innerHTML = '<span class="w-2 h-2 rounded-full bg-amber-500"></span> Pairing Required';
          document.getElementById("phone-pairing-card").classList.remove("hidden");
          if (pinFromUrl) {
            submitPairing();
          }
        }
      } catch (err) {
        console.error(err);
      }
    }

    async function loadPairingInfo() {
      try {
        const res = await fetch("/api/v1/pairing/pin");
        if (res.ok) {
          const data = await res.json();
          document.getElementById("pin-display").textContent = data.pin;
          document.getElementById("qr-image").src = data.qr_code_data_url;
        }
      } catch (e) {}
    }

    async function refreshPin() {
      const res = await fetch("/api/v1/pairing/pin/refresh", { method: "POST" });
      if (res.ok) {
        await loadPairingInfo();
      }
    }

    async function submitPairing() {
      const pin = document.getElementById("manual-pin-input").value.trim();
      const deviceName = document.getElementById("manual-device-name-input").value.trim();
      if (!pin) return alert("Please enter the 6-digit PIN");
      
      try {
        const res = await fetch("/api/v1/pairing/request", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            device_id: deviceId,
            device_name: deviceName,
            platform: "browser",
            pin_code: pin,
            requested_role: "full",
            pairing_type: document.getElementById("manual-pairing-type-input").value
          })
        });
        
        if (res.ok) {
          const data = await res.json();
          activeToken = data.token;
          localStorage.setItem("connecty_token", activeToken);
          document.getElementById("phone-pairing-card").classList.add("hidden");
          document.getElementById("auth-status").innerHTML = '<span class="w-2 h-2 rounded-full bg-emerald-500"></span> Paired (' + data.role + ')';
          loadFolders();
          loadCurrentFolder();
        } else {
          const err = await res.json();
          alert("Pairing failed: " + (err.detail || "Invalid PIN"));
        }
      } catch (err) {
        alert("Connection error: " + err);
      }
    }

    async function loadFolders() {
      try {
        const res = await fetch("/api/v1/folders", {
          headers: activeToken ? { "X-Device-Token": activeToken } : {}
        });
        if (res.ok) {
          const data = await res.json();
          const select = document.getElementById("folder-select");
          select.innerHTML = "";
          data.folders.forEach(f => {
            const opt = document.createElement("option");
            opt.value = f.id;
            opt.textContent = f.name + (f.allow_write ? " (Read/Write)" : " (Read-Only)");
            select.appendChild(opt);
          });
          if (data.folders.length > 0) {
            currentFolderId = data.folders[0].id;
          }
        }
      } catch (e) {}
    }

    function onFolderChange(newFolderId) {
      currentFolderId = newFolderId;
      currentSubpath = "";
      loadCurrentFolder();
    }

    let currentFolderItems = [];

    async function loadCurrentFolder() {
      const container = document.getElementById("file-list-container");
      container.innerHTML = `<div class="text-center py-8 text-slate-500"><i class="fa-solid fa-spinner fa-spin text-xl text-cyan-500"></i></div>`;
      
      try {
        const url = `/api/v1/files?folder=${encodeURIComponent(currentFolderId)}&subpath=${encodeURIComponent(currentSubpath)}`;
        const res = await fetch(url, {
          headers: activeToken ? { "X-Device-Token": activeToken } : {}
        });
        
        if (!res.ok) {
          container.innerHTML = `<div class="text-center py-8 text-rose-400">Failed to load folder contents. Please check pairing.</div>`;
          return;
        }

        const data = await res.json();
        document.getElementById("current-path-text").textContent = "/" + (data.current_path || "");
        
        const btnParent = document.getElementById("btn-parent");
        if (data.has_parent) {
          btnParent.classList.remove("hidden");
          btnParent.onclick = () => {
            const parts = currentSubpath.split("/").filter(Boolean);
            parts.pop();
            currentSubpath = parts.join("/");
            loadCurrentFolder();
          };
        } else {
          btnParent.classList.add("hidden");
        }

        currentFolderItems = data.items || [];
        applyFilterAndSort();
      } catch (err) {
        container.innerHTML = `<div class="text-center py-8 text-rose-400">Error: ${err}</div>`;
      }
    }

    function applyFilterAndSort() {
      const container = document.getElementById("file-list-container");
      const badge = document.getElementById("file-count-badge");
      const searchInput = document.getElementById("file-search-input");
      const sortSelect = document.getElementById("file-sort-select");

      const query = (searchInput?.value || "").toLowerCase().trim();
      const sortMode = sortSelect?.value || "name_asc";

      if (currentFolderItems.length === 0) {
        if (badge) badge.textContent = "0 items";
        container.innerHTML = `
          <div class="text-center py-12 text-slate-500 bg-slate-900/30 rounded-xl border border-slate-800">
            <i class="fa-regular fa-folder-open text-3xl mb-2 text-slate-600"></i>
            <p class="text-sm">This folder is empty.</p>
            <p class="text-xs text-slate-600 mt-1">Upload files using the Upload tab!</p>
          </div>`;
        return;
      }

      // Filter by name
      let items = currentFolderItems.filter(item => !query || item.name.toLowerCase().includes(query));

      // Sort
      items.sort((a, b) => {
        // Keep folders on top
        if (a.is_dir !== b.is_dir) return a.is_dir ? -1 : 1;

        if (sortMode === "name_asc") return a.name.localeCompare(b.name);
        if (sortMode === "name_desc") return b.name.localeCompare(a.name);
        if (sortMode === "time_desc") return (b.modified || 0) - (a.modified || 0);
        if (sortMode === "time_asc") return (a.modified || 0) - (b.modified || 0);
        if (sortMode === "size_desc") return (b.size || 0) - (a.size || 0);
        if (sortMode === "size_asc") return (a.size || 0) - (b.size || 0);
        return 0;
      });

      if (badge) badge.textContent = `${items.length} of ${currentFolderItems.length} items`;

      if (items.length === 0) {
        container.innerHTML = `
          <div class="text-center py-8 text-slate-500 bg-slate-900/30 rounded-xl border border-slate-800">
            <i class="fa-solid fa-magnifying-glass text-2xl mb-2 text-slate-600"></i>
            <p class="text-xs">No files matching "${escapeHtml(query)}"</p>
          </div>`;
        return;
      }

      let html = "";
      items.forEach(item => {
        const isVideo = item.mime_type.startsWith("video/");
        const isAudio = item.mime_type.startsWith("audio/");
        const isMedia = isVideo || isAudio;
        const icon = item.is_dir 
          ? "fa-folder text-amber-400" 
          : (isVideo ? "fa-film text-purple-400" 
          : (isAudio ? "fa-music text-pink-400" 
          : "fa-file text-slate-400"));
        
        const sizeStr = item.is_dir ? "Folder" : formatBytes(item.size);
        const dateStr = new Date(item.modified * 1000).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' });

        html += `
          <div class="glass-card hover:bg-slate-800/60 p-3 sm:p-4 rounded-xl flex items-center justify-between gap-3 transition">
            <div class="flex items-center space-x-3 truncate flex-1 cursor-pointer" onclick="${item.is_dir ? `openSubfolder('${item.relative_path}')` : (isMedia ? `playMedia('${item.id}', '${item.name}', '${item.mime_type}')` : `downloadFile('${item.id}')`)}">
              <i class="fa-solid ${icon} text-xl sm:text-2xl w-7 text-center"></i>
              <div class="truncate">
                <p class="text-sm font-semibold text-slate-200 truncate">${escapeHtml(item.name)}</p>
                <p class="text-[11px] text-slate-400">${sizeStr} • 🕒 ${dateStr}</p>
              </div>
            </div>

            <div class="flex items-center space-x-2">
              ${isMedia ? `
                <button onclick="playMedia('${item.id}', '${item.name}', '${item.mime_type}')" class="px-2.5 py-1.5 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 rounded-lg text-xs font-medium flex items-center gap-1 transition">
                  <i class="fa-solid fa-play"></i> <span class="hidden sm:inline">Stream</span>
                </button>
              ` : ""}
              ${!item.is_dir ? `
                <button onclick="downloadFile('${item.id}')" class="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-700 transition" title="Download">
                  <i class="fa-solid fa-download"></i>
                </button>
              ` : `
                <button onclick="openSubfolder('${item.relative_path}')" class="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-700 transition">
                  <i class="fa-solid fa-chevron-right"></i>
                </button>
              `}
            </div>
          </div>
        `;
      });
      container.innerHTML = html;
    }

    function openSubfolder(relPath) {
      currentSubpath = relPath;
      loadCurrentFolder();
    }

    function playMedia(fileId, filename, mimeType) {
      const modal = document.getElementById("player-modal");
      const video = document.getElementById("video-element");
      document.getElementById("player-title").textContent = filename;
      
      const streamUrl = `/api/v1/files/${fileId}?token=${encodeURIComponent(activeToken)}`;
      video.src = streamUrl;
      video.play().catch(e => console.log("Autoplay blocked:", e));
      
      document.getElementById("player-dl-btn").onclick = () => downloadFile(fileId);
      modal.classList.remove("hidden");
    }

    function closePlayer() {
      const modal = document.getElementById("player-modal");
      const video = document.getElementById("video-element");
      video.pause();
      video.src = "";
      modal.classList.add("hidden");
    }

    function downloadFile(fileId) {
      const dlUrl = `/api/v1/files/${fileId}?download=true&token=${encodeURIComponent(activeToken)}`;
      window.open(dlUrl, "_blank");
    }

    // Chunked File Upload with SHA-256
    async function handleFileSelect(e) {
      const file = e.target.files[0];
      if (!file) return;
      
      const chunkSize = 2 * 1024 * 1024; // 2 MiB chunks
      const totalChunks = Math.ceil(file.size / chunkSize);
      
      const transferId = "tx_" + Date.now();
      const container = document.getElementById("transfers-container");
      
      // Add progress card
      const card = document.createElement("div");
      card.id = transferId;
      card.className = "glass-card p-4 rounded-xl space-y-2 border border-cyan-500/30";
      card.innerHTML = `
        <div class="flex items-center justify-between text-xs">
          <span class="font-semibold text-slate-200 truncate max-w-xs">${escapeHtml(file.name)}</span>
          <span id="${transferId}-status" class="text-cyan-400 font-mono">Hashing SHA-256...</span>
        </div>
        <div class="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-700">
          <div id="${transferId}-bar" class="bg-cyan-500 h-2 progress-bar-fill" style="width: 0%"></div>
        </div>
        <div class="flex justify-between text-[11px] text-slate-400">
          <span id="${transferId}-chunks">0 / ${totalChunks} chunks</span>
          <span id="${transferId}-bytes">0 of ${formatBytes(file.size)}</span>
        </div>
      `;
      
      if (container.children[0]?.tagName === 'P') {
        container.innerHTML = "";
      }
      container.prepend(card);

      try {
        // Step 1: Compute SHA-256 (Web Crypto is only available in HTTPS/localhost; fallback to 'auto' on LAN HTTP)
        let sha256 = "auto";
        if (window.crypto && window.crypto.subtle && typeof window.crypto.subtle.digest === "function") {
          try {
            const buffer = await file.arrayBuffer();
            const hashBuffer = await crypto.subtle.digest("SHA-256", buffer);
            const hashArray = Array.from(new Uint8Array(hashBuffer));
            sha256 = hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
          } catch (e) {
            console.warn("Client hash skipped, using server-side verification:", e);
          }
        }

        document.getElementById(`${transferId}-status`).textContent = "Initiating...";

        // Step 2: Init transfer on server
        const initRes = await fetch("/api/v1/transfers", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Device-Token": activeToken
          },
          body: JSON.stringify({
            filename: file.name,
            total_size: file.size,
            total_chunks: totalChunks,
            chunk_size: chunkSize,
            expected_hash: sha256,
            target_folder_id: currentFolderId,
            target_subpath: currentSubpath
          })
        });

        if (!initRes.ok) {
          const err = await initRes.json();
          throw new Error(err.detail || "Init failed");
        }

        const serverTx = await initRes.json();
        const serverTxId = serverTx.transfer_id;

        // Step 3: Upload each chunk
        for (let i = 0; i < totalChunks; i++) {
          const start = i * chunkSize;
          const end = Math.min(start + chunkSize, file.size);
          const chunkBlob = file.slice(start, end);

          const putRes = await fetch(`/api/v1/transfers/${serverTxId}/chunks/${i}`, {
            method: "PUT",
            headers: {
              "Content-Type": "application/octet-stream",
              "X-Device-Token": activeToken
            },
            body: chunkBlob
          });

          if (!putRes.ok) {
            throw new Error(`Chunk ${i} failed`);
          }

          const pct = Math.round(((i + 1) / totalChunks) * 100);
          document.getElementById(`${transferId}-bar`).style.width = pct + "%";
          document.getElementById(`${transferId}-chunks`).textContent = `${i + 1} / ${totalChunks} chunks`;
          document.getElementById(`${transferId}-bytes`).textContent = `${formatBytes(end)} of ${formatBytes(file.size)}`;
          document.getElementById(`${transferId}-status`).textContent = `${pct}% Uploading`;
        }

        // Step 4: Finalize & verify hash
        document.getElementById(`${transferId}-status`).textContent = "Verifying hash on server...";
        const compRes = await fetch(`/api/v1/transfers/${serverTxId}/complete`, {
          method: "POST",
          headers: { "X-Device-Token": activeToken }
        });

        if (!compRes.ok) {
          const err = await compRes.json();
          throw new Error(err.detail || "Final verification failed");
        }

        document.getElementById(`${transferId}-status`).innerHTML = '<span class="text-emerald-400 font-semibold"><i class="fa-solid fa-circle-check"></i> Complete & Verified</span>';
        document.getElementById(`${transferId}-bar`).className = "bg-emerald-500 h-2 progress-bar-fill";
        loadCurrentFolder();
      } catch (err) {
        document.getElementById(`${transferId}-status`).innerHTML = `<span class="text-rose-400 font-semibold"><i class="fa-solid fa-triangle-exclamation"></i> ${err.message}</span>`;
        document.getElementById(`${transferId}-bar`).className = "bg-rose-500 h-2 progress-bar-fill";
      }
    }

    // Peers and Device Management
    async function loadDiscoveredPeers() {
      try {
        const res = await fetch("/api/v1/discovery/peers");
        if (res.ok) {
          const data = await res.json();
          const container = document.getElementById("discovered-peers-container");
          if (!data.peers || data.peers.length === 0) {
            container.innerHTML = `<p class="col-span-2 text-xs text-slate-500 text-center py-4">No other peers currently advertising on LAN.</p>`;
            return;
          }
          container.innerHTML = data.peers.map(p => `
            <div class="glass-card p-3 rounded-xl flex items-center justify-between">
              <div>
                <p class="text-sm font-semibold text-white">${escapeHtml(p.device_name)}</p>
                <p class="text-xs text-slate-400">${p.addresses[0]}:${p.port} • ${p.device_type}</p>
              </div>
              <span class="text-xs px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">mDNS</span>
            </div>
          `).join("");
        }
      } catch (e) {}
    }

    async function loadPairedDevices() {
      try {
        const res = await fetch("/api/v1/devices", {
          headers: activeToken ? { "X-Device-Token": activeToken } : {}
        });
        if (res.ok) {
          const data = await res.json();
          const container = document.getElementById("paired-devices-container");
          if (!data.devices || data.devices.length === 0) {
            container.innerHTML = `<p class="text-xs text-slate-500 text-center py-4">No devices paired yet.</p>`;
            return;
          }
          container.innerHTML = data.devices.map(d => {
            const isTemp = d.pairing_type === 'temporary';
            return `
            <div class="glass-card p-3 rounded-xl flex items-center justify-between">
              <div>
                <p class="text-sm font-semibold text-white">${escapeHtml(d.name)}</p>
                <p class="text-xs text-slate-400">ID: ${d.device_id.substring(0, 12)}... • Role: <span class="text-cyan-400">${d.role}</span> • Status: ${d.status} • Type: <span class="text-xs font-semibold ${isTemp ? 'text-rose-400' : 'text-emerald-400'}">${isTemp ? 'Temporary' : 'Permanent'}</span></p>
              </div>
              <div class="flex items-center gap-2">
                ${d.status === 'approved' ? `
                  <button onclick="togglePairingType('${d.device_id}', '${isTemp ? 'permanent' : 'temporary'}')" class="px-2.5 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition">
                    ${isTemp ? 'Make Permanent' : 'Make Temporary'}
                  </button>
                  <button onclick="revokeDevice('${d.device_id}')" class="px-2.5 py-1 text-xs bg-rose-950/60 hover:bg-rose-900 text-rose-300 rounded-lg border border-rose-800 transition">
                    Revoke
                  </button>
                ` : `<span class="text-xs text-slate-500">Revoked</span>`}
              </div>
            </div>
          `;
          }).join("");
        }
      } catch (e) {}
    }

    async function revokeDevice(devId) {
      if (!confirm("Revoke access for this device?")) return;
      const res = await fetch(`/api/v1/devices/${devId}/revoke`, {
        method: "POST",
        headers: activeToken ? { "X-Device-Token": activeToken } : {}
      });
      if (res.ok) {
        loadPairedDevices();
      }
    }

    async function togglePairingType(devId, newType) {
      const res = await fetch(`/api/v1/devices/${devId}/pairing-type`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(activeToken ? { "X-Device-Token": activeToken } : {})
        },
        body: JSON.stringify({ pairing_type: newType })
      });
      if (res.ok) {
        loadPairedDevices();
      } else {
        alert("Failed to update pairing type");
      }
    }

    // Tab Switching
    function switchTab(tab) {
      ['files', 'transfers', 'devices'].forEach(t => {
        document.getElementById(`view-${t}`).classList.add('hidden');
        const btn = document.getElementById(`tab-${t}`);
        btn.classList.remove('border-cyan-400', 'text-cyan-400');
        btn.classList.add('border-transparent', 'text-slate-400');
      });
      document.getElementById(`view-${tab}`).classList.remove('hidden');
      const activeBtn = document.getElementById(`tab-${tab}`);
      activeBtn.classList.remove('border-transparent', 'text-slate-400');
      activeBtn.classList.add('border-cyan-400', 'text-cyan-400');

      if (tab === 'devices') {
        loadDiscoveredPeers();
        loadPairedDevices();
      }
    }

    // Utilities
    function formatBytes(bytes) {
      if (bytes === 0) return "0 Bytes";
      const k = 1024;
      const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
    }

    function escapeHtml(text) {
      const div = document.createElement("div");
      div.textContent = text;
      return div.innerHTML;
    }

    window.onload = init;
  </script>
</body>
</html>"""
