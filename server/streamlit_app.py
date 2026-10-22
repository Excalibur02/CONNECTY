import io
import time
import base64
import qrcode
import requests
from pathlib import Path
from datetime import datetime
import streamlit as st

# Configure Streamlit page
st.set_page_config(
    page_title="CONNECTY - Laptop Sharing Hub",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Backend API Configuration
API_BASE = "http://127.0.0.1:8000/api/v1"

def api_get(endpoint: str, params=None):
    try:
        res = requests.get(f"{API_BASE}/{endpoint.lstrip('/')}", params=params, timeout=3)
        if res.ok:
            return res.json()
    except Exception:
        pass
    return None

def api_post(endpoint: str, data=None):
    try:
        res = requests.post(f"{API_BASE}/{endpoint.lstrip('/')}", json=data, timeout=3)
        if res.ok:
            return res.json()
    except Exception:
        pass
    return None

def api_put(endpoint: str, data=None):
    try:
        res = requests.put(f"{API_BASE}/{endpoint.lstrip('/')}", json=data, timeout=3)
        if res.ok:
            return res.json()
    except Exception:
        pass
    return None

def api_delete(endpoint: str):
    try:
        res = requests.delete(f"{API_BASE}/{endpoint.lstrip('/')}", timeout=3)
        if res.ok:
            return res.json()
    except Exception:
        pass
    return None

# Custom CSS for styling
st.markdown("""
<style>
    .metric-card {
        background: rgba(30, 41, 59, 0.6);
        padding: 16px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .stButton>button {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Fetch Laptop Status from backend
device_info = api_get("device")
health = api_get("health")

# Sidebar navigation & status
with st.sidebar:
    st.title("📡 CONNECTY")
    st.caption("Peer-to-Peer Home File Sharing")
    
    if health and health.get("status") == "healthy":
        st.success("🟢 Laptop Server Active", icon="✅")
    else:
        st.error("🔴 Backend Server Offline\n\nPlease run `run_server.bat`", icon="⚠️")

    st.markdown("---")
    menu = st.radio(
        "Navigation",
        ["📱 Pair Android Phone", "📁 Shared Folders", "🔍 Browse & Stream Files", "👥 Connected Devices", "🔄 Transfer Monitor"],
        index=0
    )

    st.markdown("---")
    st.caption(f"**LAN IP:** `{device_info.get('lan_ip', '127.0.0.1') if device_info else '...'}`")
    st.caption(f"**mDNS:** `_homesync._tcp.local.`")

if not health:
    st.warning("FastAPI service is not detected on port 8000. Start it with `server\\venv\\Scripts\\python.exe server\\run.py`.")
    st.stop()

# -------------------------------------------------------------
# TAB 1: PAIR ANDROID PHONE / TV
# -------------------------------------------------------------
if menu == "📱 Pair Android Phone":
    st.header("Connect Your Android Device")
    st.markdown("Direct local file sharing and streaming over your home Wi-Fi network.")
    pairing_device_name = st.text_input(
                        "Device Name",
                        value=device_info.get("device_name", "My Phone")
                    )
    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("1. Active Pairing Credentials")
        pin_data = api_get("pairing/pin")
        
        if pin_data:
            pin = pin_data.get("pin", "------")
            conn_url = pin_data.get("connection_url", "")
            
            c_a, c_b = st.columns([2, 1])
            with c_a:
                st.metric("Pairing 6-Digit PIN", pin)
            with c_b:
                if st.button("🔄 Generate New PIN"):
                    api_post("pairing/pin/refresh")
                    st.rerun()

            st.info(f"**Android Web/App URL:** `{conn_url}`")
            st.markdown("""
            **How to connect from your Android phone:**
            1. Ensure your phone is connected to the same Wi-Fi router.
            2. Open the **CONNECTY Android App** or open Chrome on your phone to `http://192.168.1.6:8000`.
            3. Enter the 6-digit PIN above or scan the QR code.
            4. Start streaming videos or uploading photos immediately!
            """)

    with col2:
        st.subheader("2. Quick Scan QR Code")
        if pin_data and "qr_code_data_url" in pin_data:
            st.image(pin_data["qr_code_data_url"], caption="Scan with Android camera to pair", width=220)

    st.markdown("---")
    st.subheader("Discovered Peers on Home Network")
    peers_data = api_get("discovery/peers")
    peers = peers_data.get("peers", []) if peers_data else []
    
    if peers:
        for p in peers:
            st.success(f"📡 **{p.get('device_name')}** ({p.get('device_type')}) at `{p.get('addresses', [''])[0]}:{p.get('port')}`")
    else:
        st.caption("No other mDNS peers broadcasting on the network right now.")

# -------------------------------------------------------------
# TAB 2: SHARED FOLDERS MANAGEMENT
# -------------------------------------------------------------
elif menu == "📁 Shared Folders":
    st.header("Shared Folders Manager")
    st.markdown("Configure the directories on your laptop that connected phones and TVs can browse, stream, and access.")

    folders_data = api_get("folders")
    folders = folders_data.get("folders", []) if folders_data else []

    # Find the primary default folder
    default_folder = next((f for f in folders if f["id"] == "default"), None)
    other_folders = [f for f in folders if f["id"] != "default"]

    # ---------------------------------------------------------
    # 1. PRIMARY SHARED RESOURCES FOLDER
    # ---------------------------------------------------------
    st.subheader("🌟 Primary Shared Resources Folder")
    st.caption("This is the main folder your phone opens when it connects. You can change it to any folder on your laptop.")

    if default_folder:
        current_path = default_folder.get("path", "")
        with st.container(border=True):
            st.markdown(f"**Current Path:** `{current_path}`")
            st.markdown(f"**Display Name:** {default_folder.get('name')} • **Permissions:** {'Read / Write (Full)' if default_folder.get('allow_write') else 'Read-Only'}")

            with st.expander("✏️ Change Primary Folder Path", expanded=False):
                st.markdown("Choose a quick folder preset or type a custom path on your laptop:")
                
                # Preset paths
                home = Path.home()
                preset_cols = st.columns(5)
                
                if "custom_default_path" not in st.session_state:
                    st.session_state.custom_default_path = current_path

                if preset_cols[0].button("📥 Downloads"):
                    st.session_state.custom_default_path = str(home / "Downloads")
                    st.rerun()
                if preset_cols[1].button("🎬 Videos"):
                    st.session_state.custom_default_path = str(home / "Videos")
                    st.rerun()
                if preset_cols[2].button("📸 Pictures"):
                    st.session_state.custom_default_path = str(home / "Pictures")
                    st.rerun()
                if preset_cols[3].button("📄 Documents"):
                    st.session_state.custom_default_path = str(home / "Documents")
                    st.rerun()
                if preset_cols[4].button("🔄 App Default"):
                    from server.app.config import settings
                    st.session_state.custom_default_path = str(settings.DEFAULT_SHARED_DIR.resolve())
                    st.rerun()

                with st.form("edit_default_folder_form"):
                    new_path_input = st.text_input(
                        "Laptop Folder Path",
                        value=st.session_state.custom_default_path,
                        help="Enter the absolute path to any folder on this laptop"
                    )
                    new_name_input = st.text_input(
                        "Folder Display Name",
                        value=default_folder.get("name", "Home Share")
                    )
                    new_write_input = st.checkbox(
                        "Allow write / uploads from phone",
                        value=bool(default_folder.get("allow_write", True))
                    )

                    save_btn = st.form_submit_button("Save & Update Primary Folder", type="primary")
                    if save_btn:
                        target_p = Path(new_path_input.strip())
                        if not target_p.exists() or not target_p.is_dir():
                            st.error(f"Directory not found: `{new_path_input}`. Please enter a valid existing folder.")
                        else:
                            res = api_put("folders/default", {
                                "path": str(target_p.resolve()),
                                "name": new_name_input.strip() or "Home Share",
                                "allow_write": new_write_input
                            })
                            if res and res.get("status") == "updated":
                                st.session_state.custom_default_path = str(target_p.resolve())
                                st.success(f"Primary shared folder updated to: `{target_p.resolve()}`")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("Failed to update folder settings.")

    st.markdown("---")

    # ---------------------------------------------------------
    # 2. ADDITIONAL SHARED FOLDERS
    # ---------------------------------------------------------
    st.subheader("📁 Additional Shared Folders")
    st.caption("You can also share other specific folders side-by-side with your primary folder.")

    if other_folders:
        for f in other_folders:
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.markdown(f"📁 **{f['name']}**\n\n`{f.get('path', '')}`")
                c2.markdown(f"Mode: **{'Read / Write' if f['allow_write'] else 'Read-Only'}**")
                if c3.button("Remove", key=f"del_{f['id']}"):
                    api_delete(f"folders/{f['id']}")
                    st.success(f"Removed folder {f['name']}")
                    st.rerun()
    else:
        st.info("No additional shared folders. Use the form below to share another directory.")

    with st.expander("➕ Add Another Shared Folder"):
        with st.form("add_folder_form"):
            new_name = st.text_input("Folder Display Name", placeholder="e.g. Movies, Music, Project Files")
            new_path = st.text_input("Absolute Path on Laptop", placeholder="e.g. D:\\Movies or C:\\Users\\Admin\\Music")
            new_allow_write = st.checkbox("Allow writes / uploads from phone", value=True)
            
            submitted = st.form_submit_button("Add Shared Folder", type="primary")
            if submitted:
                if not new_name.strip() or not new_path.strip():
                    st.error("Please enter both a name and a folder path.")
                else:
                    p = Path(new_path)
                    if not p.exists() or not p.is_dir():
                        st.error(f"Directory path does not exist on this laptop: {new_path}")
                    else:
                        res = api_post("folders", {
                            "name": new_name.strip(),
                            "path": str(p.resolve()),
                            "allow_write": new_allow_write
                        })
                        if res and res.get("status") == "created":
                            st.success(f"Folder '{new_name}' added successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to add folder.")

# -------------------------------------------------------------
# TAB 3: BROWSE & STREAM FILES
# -------------------------------------------------------------
elif menu == "🔍 Browse & Stream Files":
    st.header("Browse Shared Files & Media")
    
    folders_data = api_get("folders")
    folders = folders_data.get("folders", []) if folders_data else []
    
    if not folders:
        st.warning("No folders available to browse.")
        st.stop()
        
    folder_options = {f["id"]: f["name"] for f in folders}
    selected_folder_id = st.selectbox("Select Shared Folder", options=list(folder_options.keys()), format_func=lambda x: folder_options[x])

    if "subpath" not in st.session_state:
        st.session_state.subpath = ""

    # Path navigation
    c_nav1, c_nav2 = st.columns([4, 1])
    c_nav1.markdown(f"**Path:** `/{st.session_state.subpath}`")
    if st.session_state.subpath:
        if c_nav2.button("⬆️ Up Level"):
            parts = st.session_state.subpath.strip("/").split("/")
            parts.pop()
            st.session_state.subpath = "/".join(parts)
            st.rerun()

    contents = api_get("files", params={"folder": selected_folder_id, "subpath": st.session_state.subpath})
    
    if contents and "items" in contents:
        raw_items = contents["items"]
        if not raw_items:
            st.info("This folder is empty.")
        else:
            # Search by name & Sort controls
            c_srch, c_sort = st.columns([3, 2])
            search_query = c_srch.text_input("🔍 Search files by name", placeholder="Type to filter files...", label_visibility="collapsed")
            sort_by = c_sort.selectbox(
                "Sort by",
                [
                    "Name (A-Z)",
                    "Name (Z-A)",
                    "Time (Newest First)",
                    "Time (Oldest First)",
                    "Size (Largest First)",
                    "Size (Smallest First)"
                ],
                label_visibility="collapsed"
            )

            # Apply Search filter
            filtered_items = [
                i for i in raw_items 
                if not search_query.strip() or search_query.strip().lower() in i["name"].lower()
            ]

            # Apply Sorting
            if sort_by == "Name (A-Z)":
                filtered_items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
            elif sort_by == "Name (Z-A)":
                filtered_items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()), reverse=True)
            elif sort_by == "Time (Newest First)":
                filtered_items.sort(key=lambda x: (not x["is_dir"], x.get("modified", 0)), reverse=True)
            elif sort_by == "Time (Oldest First)":
                filtered_items.sort(key=lambda x: (not x["is_dir"], x.get("modified", 0)))
            elif sort_by == "Size (Largest First)":
                filtered_items.sort(key=lambda x: (not x["is_dir"], x.get("size", 0)), reverse=True)
            elif sort_by == "Size (Smallest First)":
                filtered_items.sort(key=lambda x: (not x["is_dir"], x.get("size", 0)))

            if not filtered_items:
                st.info(f"No files matching '{search_query}'.")
            else:
                st.caption(f"Showing {len(filtered_items)} of {len(raw_items)} items")
                for item in filtered_items:
                    with st.container(border=True):
                        col_icon, col_info, col_act = st.columns([1, 4, 2])
                        
                        time_str = datetime.fromtimestamp(item.get("modified", 0)).strftime("%Y-%m-%d %H:%M")
                        if item["is_dir"]:
                            col_icon.markdown("📁")
                            col_info.markdown(f"**{item['name']}** *(Folder)*\n\n🕒 `{time_str}`")
                            if col_act.button("Open", key=f"open_{item['id']}"):
                                st.session_state.subpath = item["relative_path"]
                                st.rerun()
                        else:
                            mime = item["mime_type"]
                            size_mb = item["size"] / (1024 * 1024)
                            icon = "🎬" if mime.startswith("video/") else ("🎵" if mime.startswith("audio/") else "📄")
                            col_icon.markdown(icon)
                            col_info.markdown(f"**{item['name']}**\n\n`{size_mb:.2f} MB` • `{mime}` • 🕒 `{time_str}`")
                            
                            file_stream_url = f"{API_BASE}/files/{item['id']}"
                            
                            # Streaming preview
                            if mime.startswith("video/"):
                                if col_act.button("▶️ Play Video", key=f"play_{item['id']}"):
                                    st.video(file_stream_url)
                            elif mime.startswith("audio/"):
                                if col_act.button("▶️ Play Audio", key=f"play_{item['id']}"):
                                    st.audio(file_stream_url)
                            else:
                                col_act.markdown(f"[⬇️ Download]({file_stream_url}?download=true)")

# -------------------------------------------------------------
# TAB 4: CONNECTED DEVICES & ACCESS CONTROL
# -------------------------------------------------------------
elif menu == "👥 Connected Devices":
    st.header("Connected & Paired Devices")
    st.markdown("Manage authorization and access permissions for phones and TVs.")

    devices_data = api_get("devices")
    devices = devices_data.get("devices", []) if devices_data else []

    if devices:
        for dev in devices:
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 2])
                c1.markdown(f"📱 **{dev['name']}**\n\nID: `{dev['device_id'][:12]}...` • Platform: `{dev.get('platform', 'unknown')}`")
                
                status_color = "🟢" if dev["status"] == "approved" else "🔴"
                c2.markdown(f"Status: **{status_color} {dev['status'].capitalize()}**\n\nRole: **{dev['role']}**")

                if dev["status"] == "approved":
                    if c3.button("Revoke Access", key=f"rev_{dev['device_id']}", type="secondary"):
                        api_post(f"devices/{dev['device_id']}/revoke")
                        st.warning(f"Revoked access for {dev['name']}")
                        st.rerun()
                else:
                    c3.caption("Revoked")
    else:
        st.info("No external devices paired yet. Scan the QR code or enter PIN from an Android device to pair.")

# -------------------------------------------------------------
# TAB 5: TRANSFER MONITOR
# -------------------------------------------------------------
elif menu == "🔄 Transfer Monitor":
    st.header("File Transfer Monitor")
    st.markdown("Track chunked resumable transfers and verify SHA-256 hashes.")

    st.subheader("Upload a File from Laptop (Testing Transfer Engine)")
    uploaded_file = st.file_uploader("Select file to test chunking and SHA-256 verification")
    
    if uploaded_file:
        if st.button("Start Local Chunk Upload Test", type="primary"):
            import hashlib
            data = uploaded_file.read()
            total_size = len(data)
            chunk_size = 2 * 1024 * 1024
            total_chunks = (total_size + chunk_size - 1) // chunk_size if total_size > 0 else 1
            file_hash = hashlib.sha256(data).hexdigest()

            prog = st.progress(0, text="Initiating transfer...")
            
            init_res = api_post("transfers", {
                "filename": uploaded_file.name,
                "total_size": total_size,
                "total_chunks": total_chunks,
                "chunk_size": chunk_size,
                "expected_hash": file_hash,
                "target_folder_id": "default",
                "target_subpath": ""
            })

            if init_res:
                tx_id = init_res["transfer_id"]
                for i in range(total_chunks):
                    chunk_slice = data[i * chunk_size : (i + 1) * chunk_size]
                    requests.put(
                        f"{API_BASE}/transfers/{tx_id}/chunks/{i}",
                        data=chunk_slice,
                        headers={"Content-Type": "application/octet-stream"}
                    )
                    pct = int(((i + 1) / total_chunks) * 100)
                    prog.progress(pct, text=f"Uploading chunk {i + 1} of {total_chunks} ({pct}%)...")

                comp = api_post(f"transfers/{tx_id}/complete")
                if comp and comp.get("status") == "completed":
                    st.success(f"Transfer complete! Verified SHA-256: `{comp['sha256']}`")
                else:
                    st.error("Transfer verification failed.")
            else:
                st.error("Failed to initiate transfer.")
