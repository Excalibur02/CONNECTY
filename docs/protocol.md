# CONNECTY Peer-to-Peer Home Sharing Protocol

## 1. Overview
CONNECTY is a peer-to-peer home network file sharing and streaming protocol designed for direct communication between personal devices (laptops, phones, smart TVs) on a local area network (LAN) without requiring permanent central servers, NAS equipment, or external cloud relays.

---

## 2. Discovery: mDNS / DNS-SD
Active devices advertise their availability on the Wi-Fi LAN using Multicast DNS:
- **Service Type**: `_homesync._tcp.local.` (fallback: `_connecty._tcp.local.`)
- **Port**: Assigned dynamically or default `8000`
- **DNS TXT Records**:
  - `device_name`: Human-readable device name (e.g. `Laptop-Admin`)
  - `device_id`: Persistent UUID of the host device
  - `device_type`: `laptop`, `phone`, `tv`
  - `version`: Protocol version (`1.0.0`)
  - `capabilities`: Comma-separated list (`browse,stream,receive`)
  - `lan_ip`: Primary IPv4 address (e.g. `192.168.1.6`)

**Fallback Connection**:
If mDNS multicast packets are dropped due to router AP isolation or multicast filtering, devices can connect directly via `http://<lan_ip>:<port>` or by scanning a dynamic QR code.

---

## 3. Trust & Pairing Model
To protect personal files from unauthorized access on shared home networks, every non-localhost client must pair before browsing or uploading files:
1. The host laptop generates a dynamic 6-digit PIN and displays it on screen along with an encoded QR code.
2. The client submits `POST /api/v1/pairing/request` with `pin_code`, `device_id`, and `requested_role`.
3. If the PIN is verified, the host issues a cryptographically secure revocable `token`.
4. Subsequent client requests include the header:
   ```http
   X-Device-Token: <token>
   ```
   Or query parameter for native HTML5 media and ExoPlayer:
   ```
   ?token=<token>
   ```
5. Roles:
   - `full`: Can browse, download, and upload files (for phones / tablets).
   - `read-only`: Can browse and stream media only (for Google TV).

---

## 4. API Endpoints

### 4.1 Device & Pairing
- **`GET /api/v1/device`**
  - Public device information, network IP, port, and capabilities.
- **`GET /api/v1/pairing/pin`**
  - Generates/fetches current 6-digit PIN and Base64 QR code data URL.
- **`POST /api/v1/pairing/pin/refresh`**
  - Generates a fresh PIN code.
- **`POST /api/v1/pairing/request`**
  - Request body: `{ "device_id", "device_name", "platform", "pin_code", "requested_role" }`
  - Response: `{ "status": "paired", "token": "...", "role": "full" }`
- **`GET /api/v1/devices`**
  - List authorized devices and status (approved, revoked).
- **`POST /api/v1/devices/{device_id}/revoke`**
  - Revokes an authorized device's access.
- **`GET /api/v1/discovery/peers`**
  - Discovered mDNS peers on the LAN.

---

### 4.2 File Browsing & Streaming
Files are addressed using opaque, URL-safe identifiers rather than exposing raw filesystem paths.
- **`GET /api/v1/folders`**
  - Lists approved shared folders.
- **`GET /api/v1/files?folder={folder_id}&subpath={relative_subpath}`**
  - Returns directory listing (directories first, files with MIME type, size, modified timestamp, opaque IDs).
- **`HEAD /api/v1/files/{file_id}`**
  - Checks file size and verifies HTTP Byte Range support.
- **`GET /api/v1/files/{file_id}`**
  - Streams or downloads a file.
  - **HTTP Byte Range Support**:
    - Request header: `Range: bytes=start-end` (e.g. `bytes=1048576-2097151` or `bytes=0-`)
    - Response status: `206 Partial Content`
    - Response headers:
      - `Content-Range: bytes {start}-{end}/{total}`
      - `Accept-Ranges: bytes`
      - `Content-Length: {slice_length}`
      - `Content-Type: video/mp4` (or detected MIME)

---

### 4.3 Chunked Resumable Transfers
For large files (videos, photos, ISOs), files are uploaded in chunks (e.g. 2 MiB):
1. **Initiate Transfer**:
   - `POST /api/v1/transfers`
   - Body:
     ```json
     {
       "filename": "vacation_video.mp4",
       "total_size": 104857600,
       "total_chunks": 50,
       "chunk_size": 2097152,
       "expected_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
       "target_folder_id": "default",
       "target_subpath": ""
     }
     ```
   - Response: `{ "transfer_id": "uuid", "total_chunks": 50, "status": "in_progress" }`
2. **Upload Chunks**:
   - `PUT /api/v1/transfers/{transfer_id}/chunks/{chunk_index}`
   - Body: Raw chunk bytes (`application/octet-stream`).
3. **Resumption Query**:
   - `GET /api/v1/transfers/{transfer_id}`
   - Returns `{ "received_chunks": [0, 1, 2, 3, ...] }`. The client only sends missing chunks after a network drop.
4. **Finalize Transfer**:
   - `POST /api/v1/transfers/{transfer_id}/complete`
   - The server verifies all chunks exist, concatenates them, computes the streaming SHA-256 hash, checks it against `expected_hash`, and atomically moves the assembled file to the destination folder.
