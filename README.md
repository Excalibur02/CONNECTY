# CONNECTY: Peer-to-Peer Home File Sharing Network

CONNECTY is a serverless, peer-to-peer home network file sharing and media streaming system. No computer, NAS, or central server needs to stay on permanently. When your laptop is awake, your phone (and soon Google TV) can browse files, stream videos with instant seeking, and transfer large files directly over your local Wi-Fi.

---

## Architecture Overview

```
                      +-----------------------------+
                      |   Home Router / Wi-Fi LAN   |
                      +--------------+--------------+
                                     |
               +---------------------+---------------------+
               |                     |                     |
     +---------v---------+ +---------v---------+ +---------v---------+
     |   Windows Laptop  | |    Android Phone  | |    Google TV      |
     | (FastAPI+Streamlit)| |   (Native Kotlin) | |   (Media3 TV)     |
     +-------------------+ +-------------------+ +-------------------+
     • Python + FastAPI    • Kotlin + Compose    • Android TV + Media3
     • Streamlit Dashboard • NSD Discovery       • Remote UI (Phase 2)
     • mDNS Service        • Chunked Uploads     • Read-Only Role
     • Range Media Stream  • SHA-256 Checksum    • Direct HTTP Range
     • SQLite Device Auth  • Direct Streaming    • No Central NAS
```

---

## Features Implemented (Phase 1 & Laptop <-> Android Connectivity)

1. **Zero Central Server / NAS Requirement**: Direct device-to-device streaming and transfers.
2. **Device Discovery**:
   - Automatic local network mDNS / DNS-SD advertising (`_homesync._tcp.local.`).
   - Fallback via direct local IP (`http://192.168.1.6:8000`) and QR code scanning.
3. **Security & Pairing**:
   - 6-digit PIN verification + QR code scan.
   - Revocable device authorization tokens.
   - Strict path traversal (`../`) and symlink escape defenses.
   - Separate roles (`full` read/write for phone, `read-only` for TV).
4. **Byte-Range Media Streaming (`206 Partial Content`)**:
   - Fast seeking in videos and audio without downloading the entire file.
   - Tested and verified with native HTML5 and Android Media3 ExoPlayer.
5. **Reliable Chunk-Based Resumable Transfers**:
   - 2 MiB chunk uploads with streaming SHA-256 cryptographic verification.
   - Resumable: recovers from dropped Wi-Fi connections by uploading only missing chunks.
6. **Dual Android Access**:
   - **Zero-Install Mobile Web Client**: Open `http://<laptop-ip>:8000` on any phone browser to browse, stream, and upload immediately.
   - **Native Android Client**: Jetpack Compose Kotlin project with NSD discovery, Retrofit client, and Media3 ExoPlayer.

---

## Quick Start: Running the Laptop Hub

### Option A: Double-Click Launcher (Windows)
Double-click `run_server.bat` in the root folder.
This automatically starts:
1. The **FastAPI background service** on `http://192.168.1.6:8000` (mDNS broadcast, byte-range streaming, chunked transfers).
2. The **Streamlit Web Dashboard** on `http://localhost:8501`.

### Option B: Command Line
```powershell
# Run both FastAPI and Streamlit together
server\venv\Scripts\python.exe server\run_laptop.py

# Or run only the background FastAPI service
server\venv\Scripts\python.exe server\run.py
```

The Streamlit dashboard opens automatically at `http://localhost:8501`, displaying:
- **Pairing Hub**: Live 6-digit PIN and QR code to pair your Android device instantly.
- **Shared Folders Manager**: Add or remove any folder on your laptop to share.
- **Browse & Stream**: In-browser video and audio playback (`st.video`, `st.audio`) with byte-range seek support.
- **Connected Devices**: List and revoke access for paired phones and TVs.
- **Transfer Monitor**: Track chunked uploads with SHA-256 integrity verification.

---

## Connecting Your Android Phone

1. **Zero-Install (Instant)**:
   - On your Android phone (connected to the same Wi-Fi router), open Chrome and navigate to `http://192.168.1.6:8000` (or scan the QR code shown on `http://localhost:8000`).
   - Enter the 6-digit PIN displayed on your laptop.
   - You can immediately browse files, stream videos with seeking, and upload photos/files with chunked SHA-256 verification.

2. **Native Android Client**:
   - Located in `android-client/`.
   - Open `android-client/` in Android Studio to build and deploy to your physical phone or emulator.
   - Automatically discovers the laptop via `NsdDiscoveryManager` and pairs with Media3 streaming support.

---

## Running Automated Tests

Run the test suite verifying all 5 core subsystems (device discovery, pairing security, range streaming, chunked uploads, and path traversal protection):

```powershell
server\venv\Scripts\pytest -v
```

---

## Next Steps: Boarding Google TV

1. **Phase 5**: Build the native Android TV client in `android-tv-client/` using Android TV Leanback / Jetpack Compose for TV with directional pad (D-pad) remote navigation.
2. Pair Google TV with the laptop using a `read-only` role.
3. Stream video files directly from laptop to TV using Media3 ExoPlayer over HTTP Byte-Range requests.
