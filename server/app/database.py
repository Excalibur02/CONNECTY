import sqlite3
import time
import json
import uuid
import secrets
from pathlib import Path
from typing import List, Dict, Any, Optional
from server.app.config import settings

def get_db():
    conn = sqlite3.connect(settings.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shared_folders (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                path TEXT NOT NULL,
                allow_write INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 1,
                created_at REAL
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS paired_devices (
                device_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                platform TEXT DEFAULT 'unknown',
                token TEXT NOT NULL,
                status TEXT DEFAULT 'approved',
                role TEXT DEFAULT 'full',
                last_seen REAL
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pairing_pins (
                pin TEXT PRIMARY KEY,
                created_at REAL,
                expires_at REAL
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transfers (
                transfer_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                total_size INTEGER NOT NULL,
                total_chunks INTEGER NOT NULL,
                chunk_size INTEGER NOT NULL,
                expected_hash TEXT NOT NULL,
                status TEXT DEFAULT 'in_progress',
                target_folder_id TEXT NOT NULL,
                target_subpath TEXT DEFAULT '',
                received_chunks TEXT DEFAULT '[]',
                created_at REAL
            )
        """)
        
        # Ensure a default shared folder exists
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM shared_folders")
        if cursor.fetchone()[0] == 0:
            default_id = "default"
            default_path = str(settings.DEFAULT_SHARED_DIR.resolve())
            cursor.execute("""
                INSERT INTO shared_folders (id, name, path, allow_write, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (default_id, "Home Share", default_path, 1, 1, time.time()))
            
            # Create a sample file in the default shared folder
            sample_file = settings.DEFAULT_SHARED_DIR / "welcome.txt"
            if not sample_file.exists():
                sample_file.write_text(
                    "Welcome to CONNECTY Peer-to-Peer Home Sharing!\n\n"
                    "This file is being served directly from your laptop to your local network.\n"
                    "You can stream videos, download files, and upload photos/documents securely.\n"
                )
    conn.close()

# Shared Folders Helpers
def get_shared_folders(only_active: bool = True) -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT * FROM shared_folders"
    if only_active:
        query += " WHERE is_active = 1"
    cursor.execute(query)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_shared_folder_by_id(folder_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shared_folders WHERE id = ?", (folder_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def add_shared_folder(name: str, path: str, allow_write: bool = True) -> Dict[str, Any]:
    folder_id = str(uuid.uuid4())[:8]
    conn = get_db()
    with conn:
        conn.execute("""
            INSERT INTO shared_folders (id, name, path, allow_write, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (folder_id, name, str(Path(path).resolve()), 1 if allow_write else 0, 1, time.time()))
    conn.close()
    return get_shared_folder_by_id(folder_id)

def update_shared_folder(folder_id: str, name: Optional[str] = None, path: Optional[str] = None, allow_write: Optional[bool] = None) -> Optional[Dict[str, Any]]:
    folder = get_shared_folder_by_id(folder_id)
    if not folder:
        return None
    new_name = name.strip() if (name and name.strip()) else folder["name"]
    new_path = str(Path(path).resolve()) if path else folder["path"]
    new_write = (1 if allow_write else 0) if allow_write is not None else folder["allow_write"]
    
    conn = get_db()
    with conn:
        conn.execute("""
            UPDATE shared_folders
            SET name = ?, path = ?, allow_write = ?
            WHERE id = ?
        """, (new_name, new_path, new_write, folder_id))
    conn.close()
    return get_shared_folder_by_id(folder_id)

def remove_shared_folder(folder_id: str) -> bool:
    conn = get_db()
    with conn:
        cursor = conn.execute("DELETE FROM shared_folders WHERE id = ?", (folder_id,))
        success = cursor.rowcount > 0
    conn.close()
    return success

# Pairing and Device Management Helpers
def generate_pairing_pin() -> str:
    conn = get_db()
    with conn:
        # Clean expired PINs
        now = time.time()
        conn.execute("DELETE FROM pairing_pins WHERE expires_at < ?", (now,))
        
        # Generate 6-digit pin
        pin = f"{secrets.randbelow(900000) + 100000}"
        expires_at = now + settings.PAIRING_PIN_EXPIRE_SECONDS
        conn.execute("INSERT OR REPLACE INTO pairing_pins (pin, created_at, expires_at) VALUES (?, ?, ?)",
                     (pin, now, expires_at))
    conn.close()
    return pin

def get_active_pin() -> Optional[str]:
    conn = get_db()
    cursor = conn.cursor()
    now = time.time()
    cursor.execute("SELECT pin FROM pairing_pins WHERE expires_at > ? ORDER BY created_at DESC LIMIT 1", (now,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row["pin"]
    return generate_pairing_pin()

def verify_pairing_pin(pin: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    now = time.time()
    cursor.execute("SELECT pin FROM pairing_pins WHERE pin = ? AND expires_at > ?", (pin.strip(), now))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def register_paired_device(device_id: str, name: str, platform: str, role: str = "full") -> str:
    token = secrets.token_urlsafe(32)
    conn = get_db()
    with conn:
        conn.execute("""
            INSERT OR REPLACE INTO paired_devices (device_id, name, platform, token, status, role, last_seen)
            VALUES (?, ?, ?, ?, 'approved', ?, ?)
        """, (device_id, name, platform, token, role, time.time()))
    conn.close()
    return token

def get_device_by_token(token: str) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM paired_devices WHERE token = ? AND status = 'approved'", (token,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_device_last_seen(device_id: str):
    conn = get_db()
    with conn:
        conn.execute("UPDATE paired_devices SET last_seen = ? WHERE device_id = ?", (time.time(), device_id))
    conn.close()

def list_paired_devices() -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT device_id, name, platform, status, role, last_seen FROM paired_devices ORDER BY last_seen DESC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def revoke_device(device_id: str) -> bool:
    conn = get_db()
    with conn:
        cursor = conn.execute("DELETE FROM paired_devices WHERE device_id = ?", (device_id,)) 
        success = cursor.rowcount > 0
    conn.close()
    return success

# Transfers Helpers
def create_transfer_record(transfer_id: str, filename: str, total_size: int, total_chunks: int,
                           chunk_size: int, expected_hash: str, target_folder_id: str,
                           target_subpath: str = "") -> Dict[str, Any]:
    conn = get_db()
    with conn:
        conn.execute("""
            INSERT INTO transfers (
                transfer_id, filename, total_size, total_chunks, chunk_size,
                expected_hash, status, target_folder_id, target_subpath, received_chunks, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'in_progress', ?, ?, '[]', ?)
        """, (transfer_id, filename, total_size, total_chunks, chunk_size,
              expected_hash.lower(), target_folder_id, target_subpath, time.time()))
    conn.close()
    return get_transfer_record(transfer_id)

def get_transfer_record(transfer_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transfers WHERE transfer_id = ?", (transfer_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["received_chunks"] = json.loads(d["received_chunks"])
    return d

def update_transfer_chunk(transfer_id: str, chunk_index: int):
    record = get_transfer_record(transfer_id)
    if not record:
        return
    received = set(record["received_chunks"])
    received.add(chunk_index)
    conn = get_db()
    with conn:
        conn.execute("UPDATE transfers SET received_chunks = ? WHERE transfer_id = ?",
                     (json.dumps(sorted(list(received))), transfer_id))
    conn.close()

def update_transfer_status(transfer_id: str, status: str):
    conn = get_db()
    with conn:
        conn.execute("UPDATE transfers SET status = ? WHERE transfer_id = ?", (status, transfer_id))
    conn.close()
