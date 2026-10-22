import pytest
import hashlib
import shutil
from fastapi.testclient import TestClient
from server.app.main import app
from server.app.config import settings
from server.app.database import init_db, get_active_pin, get_shared_folders

@pytest.fixture(autouse=True)
def setup_isolated_test_env(tmp_path, monkeypatch):
    test_base = tmp_path / "connecty_test_data"
    test_base.mkdir(parents=True, exist_ok=True)
    
    monkeypatch.setattr(settings, "BASE_DIR", test_base)
    settings.STAGING_DIR.mkdir(parents=True, exist_ok=True)
    settings.DEFAULT_SHARED_DIR.mkdir(parents=True, exist_ok=True)
    
    init_db()
    yield
    # Cleanup after test
    shutil.rmtree(test_base, ignore_errors=True)

@pytest.fixture
def client():
    return TestClient(app)

def test_device_info(client):
    response = client.get("/api/v1/device")
    assert response.status_code == 200
    data = response.json()
    assert "device_name" in data
    assert "lan_ip" in data
    assert "capabilities" in data
    assert "stream" in data["capabilities"]

def test_pairing_workflow(client):
    # 1. Fetch PIN
    pin_res = client.get("/api/v1/pairing/pin")
    assert pin_res.status_code == 200
    pin_data = pin_res.json()
    assert "pin" in pin_data
    assert "qr_code_data_url" in pin_data
    pin = pin_data["pin"]

    # 2. Try invalid PIN
    bad_pair = client.post("/api/v1/pairing/request", json={
        "device_id": "test_android_phone_bad",
        "device_name": "Pixel 8 Pro",
        "platform": "android",
        "pin_code": "000000",
        "requested_role": "full"
    })
    assert bad_pair.status_code == 401

    # 3. Pair with valid PIN
    good_pair = client.post("/api/v1/pairing/request", json={
        "device_id": "test_android_phone_1",
        "device_name": "Pixel 8 Pro",
        "platform": "android",
        "pin_code": pin,
        "requested_role": "full"
    })
    assert good_pair.status_code == 200
    pair_data = good_pair.json()
    assert "token" in pair_data
    assert pair_data["role"] == "full"
    token = pair_data["token"]

    # 4. Access authorized folders with token
    folders_res = client.get("/api/v1/folders", headers={"X-Device-Token": token})
    assert folders_res.status_code == 200
    assert len(folders_res.json()["folders"]) >= 1

def test_browse_files_and_range_streaming(client):
    # Get active PIN and pair
    pin = get_active_pin()
    pair_res = client.post("/api/v1/pairing/request", json={
        "device_id": "test_android_phone_2",
        "device_name": "Galaxy S24",
        "platform": "android",
        "pin_code": pin,
        "requested_role": "full"
    })
    token = pair_res.json()["token"]

    # Browse default folder
    files_res = client.get("/api/v1/files?folder=default", headers={"X-Device-Token": token})
    assert files_res.status_code == 200
    items = files_res.json()["items"]
    assert len(items) >= 1
    
    welcome_file = next((f for f in items if f["name"] == "welcome.txt"), None)
    assert welcome_file is not None
    file_id = welcome_file["id"]
    total_size = welcome_file["size"]
    assert total_size > 0

    # Test full file download
    full_dl = client.get(f"/api/v1/files/{file_id}", headers={"X-Device-Token": token})
    assert full_dl.status_code == 200
    assert "Welcome to CONNECTY" in full_dl.text

    # Test HTTP 206 Partial Content Range Request (first 10 bytes)
    range_res = client.get(
        f"/api/v1/files/{file_id}",
        headers={"X-Device-Token": token, "Range": "bytes=0-9"}
    )
    assert range_res.status_code == 206
    assert range_res.headers["Content-Range"] == f"bytes 0-9/{total_size}"
    assert range_res.headers["Content-Length"] == "10"
    assert range_res.content == b"Welcome to"

def test_chunked_resumable_upload_and_sha256(client):
    pin = get_active_pin()
    pair_res = client.post("/api/v1/pairing/request", json={
        "device_id": "test_android_phone_3",
        "device_name": "OnePlus 12",
        "platform": "android",
        "pin_code": pin,
        "requested_role": "full"
    })
    token = pair_res.json()["token"]

    test_content = b"Connecty P2P Chunk 1 Data" + b"Connecty P2P Chunk 2 Data"
    total_size = len(test_content)
    chunk_1 = b"Connecty P2P Chunk 1 Data"
    chunk_2 = b"Connecty P2P Chunk 2 Data"
    expected_hash = hashlib.sha256(test_content).hexdigest()

    # 1. Initiate transfer
    init_res = client.post("/api/v1/transfers", headers={"X-Device-Token": token}, json={
        "filename": "uploaded_test.txt",
        "total_size": total_size,
        "total_chunks": 2,
        "chunk_size": len(chunk_1),
        "expected_hash": expected_hash,
        "target_folder_id": "default",
        "target_subpath": ""
    })
    assert init_res.status_code == 200
    tx_id = init_res.json()["transfer_id"]

    # 2. Upload Chunk 0
    c0_res = client.put(f"/api/v1/transfers/{tx_id}/chunks/0",
                        headers={"X-Device-Token": token, "Content-Type": "application/octet-stream"},
                        content=chunk_1)
    assert c0_res.status_code == 200

    # 3. Check transfer progress (for resumption)
    prog_res = client.get(f"/api/v1/transfers/{tx_id}", headers={"X-Device-Token": token})
    assert prog_res.status_code == 200
    assert 0 in prog_res.json()["received_chunks"]
    assert 1 not in prog_res.json()["received_chunks"]

    # 4. Upload Chunk 1
    c1_res = client.put(f"/api/v1/transfers/{tx_id}/chunks/1",
                        headers={"X-Device-Token": token, "Content-Type": "application/octet-stream"},
                        content=chunk_2)
    assert c1_res.status_code == 200

    # 5. Finalize and verify SHA-256
    finalize_res = client.post(f"/api/v1/transfers/{tx_id}/complete", headers={"X-Device-Token": token})
    assert finalize_res.status_code == 200
    assert finalize_res.json()["status"] == "completed"
    assert finalize_res.json()["sha256"] == expected_hash

def test_path_traversal_prevention(client):
    from server.app.security.path_validator import encode_file_id
    
    pin = get_active_pin()
    pair_res = client.post("/api/v1/pairing/request", json={
        "device_id": "test_android_phone_4",
        "device_name": "Pixel",
        "platform": "android",
        "pin_code": pin,
        "requested_role": "full"
    })
    token = pair_res.json()["token"]

    # Attempt to encode a path escaping the root directory
    malicious_id = encode_file_id("default", "../../../../../Windows/System32/drivers/etc/hosts")
    escape_res = client.get(f"/api/v1/files/{malicious_id}", headers={"X-Device-Token": token})
    assert escape_res.status_code in (403, 404)

def test_change_shared_folder(client, tmp_path):
    # Create custom directory with a test file
    custom_dir = tmp_path / "custom_shared_dir"
    custom_dir.mkdir(parents=True, exist_ok=True)
    sample_file = custom_dir / "custom_notes.txt"
    sample_file.write_text("Testing changed shared folder!")

    # Update default folder path via PUT /api/v1/folders/default
    update_res = client.put("/api/v1/folders/default", json={
        "name": "My New Custom Share",
        "path": str(custom_dir),
        "allow_write": True
    })
    assert update_res.status_code == 200
    updated_data = update_res.json()["folder"]
    assert updated_data["name"] == "My New Custom Share"
    assert updated_data["path"] == str(custom_dir.resolve())

    # Browse default folder and verify custom_notes.txt is now visible
    browse_res = client.get("/api/v1/files?folder=default")
    assert browse_res.status_code == 200
    items = browse_res.json()["items"]
    names = [f["name"] for f in items]
    assert "custom_notes.txt" in names

    # Verify invalid path is rejected
    bad_res = client.put("/api/v1/folders/default", json={
        "path": "Z:\\This\\Path\\Does\\Not\\Exist"
    })
    assert bad_res.status_code == 400

