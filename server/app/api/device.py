import io
import base64
import qrcode
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from server.app.config import settings
import logging
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

from server.app.database import (
    get_active_pin,
    verify_pairing_pin,
    register_paired_device,
    list_paired_devices,
    revoke_device,
    generate_pairing_pin,
    get_db,
    set_device_pairing_type,
)
from server.app.security.auth import get_current_device
from server.app.services.discovery import discovery_service

router = APIRouter(prefix="/api/v1", tags=["device"])

class PairingRequest(BaseModel):
    device_id: str
    device_name: str
    platform: str = "android"  # android, tv, web, windows, etc.
    pin_code: str
    requested_role: str = "full"  # 'full' (phone) or 'read-only' (tv)
    pairing_type: str = "temporary"  # 'permanent' survives server restarts; 'temporary' is cleared on restart

class RoleUpdateRequest(BaseModel):
    role: str  # 'full' or 'read-only'

class PairingTypeUpdateRequest(BaseModel):
    pairing_type: str  # 'temporary' or 'permanent'

@router.get("/device")
async def get_device_info():
    """Get this device's public identity and network endpoints."""
    return {
        "device_name": settings.DEVICE_NAME,
        "device_id": settings.DEVICE_ID,
        "device_type": settings.DEVICE_TYPE,
        "protocol_version": settings.PROTOCOL_VERSION,
        "lan_ip": settings.LAN_IP,
        "port": settings.PORT,
        "capabilities": ["browse", "stream", "receive"],
        "connection_url": f"http://{settings.LAN_IP}:{settings.PORT}"
    }

@router.get("/pairing/pin")
async def get_pairing_pin():
    """
    Get current 6-digit pairing code and QR code image (Base64 Data URL)
    for pairing phones / TV devices.
    """
    pin = get_active_pin()
    connection_url = f"http://{settings.LAN_IP}:{settings.PORT}/?pin={pin}"
    
    # Generate QR Code image in-memory
    qr = qrcode.QRCode(
        version=1,
        box_size=8,
        border=2,
    )
    qr.add_data(connection_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    qr_data_url = f"data:image/png;base64,{qr_base64}"
    
    return {
        "pin": pin,
        "connection_url": connection_url,
        "qr_code_data_url": qr_data_url,
        "expires_in_seconds": settings.PAIRING_PIN_EXPIRE_SECONDS
    }

@router.post("/pairing/pin/refresh")
async def refresh_pairing_pin():
    """Force generate a new 6-digit PIN."""
    new_pin = generate_pairing_pin()
    return {"pin": new_pin}

@router.post("/pairing/request")
async def request_pairing(body: PairingRequest):
    """
    Pair a new device by submitting the correct 6-digit PIN.
    On success, issues a revocable device authorization token.
    """
    if not verify_pairing_pin(body.pin_code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired pairing PIN"
        )
        
    role = "read-only" if body.requested_role == "read-only" else "full"
    
    if body.pairing_type not in ("temporary", "permanent"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pairing_type must be 'temporary' or 'permanent'"
        )
    
    token = register_paired_device(
        device_id=body.device_id,
        name=body.device_name,
        platform=body.platform,
        role=role,
        pairing_type=body.pairing_type
    ) 
    logger.info(f"Device full info: {body}")
    logger.info(f"Device name: {body.device_name}")
    return {
        "status": "paired",
        "device_id": body.device_id,
        "device_name": body.device_name,
        "role": role,
        "token": token,
        "pairing_type": body.pairing_type
    }

@router.get("/devices")
async def get_paired_devices(current_device: Dict[str, Any] = Depends(get_current_device)):
    """List all paired devices."""
    devices = list_paired_devices()
    return {"devices": devices}

@router.post("/devices/{device_id}/revoke")
async def revoke_paired_device(
    device_id: str,
    current_device: Dict[str, Any] = Depends(get_current_device)
):
    """Revoke a paired device's access."""
    success = revoke_device(device_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' not found"
        )
    return {"status": "revoked", "device_id": device_id}

@router.post("/devices/{device_id}/role")
async def update_device_role(
    device_id: str,
    body: RoleUpdateRequest,
    current_device: Dict[str, Any] = Depends(get_current_device)
):
    """Change permissions for a device ('full' or 'read-only')."""
    if body.role not in ("full", "read-only"):
        raise HTTPException(status_code=400, detail="Role must be 'full' or 'read-only'")
    conn = get_db()
    with conn:
        cursor = conn.execute("UPDATE paired_devices SET role = ? WHERE device_id = ?", (body.role, device_id))
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Device not found")
    conn.close()
    return {"status": "updated", "device_id": device_id, "role": body.role}

@router.post("/devices/{device_id}/pairing-type")
async def update_device_pairing_type(
    device_id: str,
    body: PairingTypeUpdateRequest,
    current_device: Dict[str, Any] = Depends(get_current_device)
):
    """Change a device's pairing type ('temporary' cleared on restart, 'permanent' persists)."""
    if body.pairing_type not in ("temporary", "permanent"):
        raise HTTPException(status_code=400, detail="pairing_type must be 'temporary' or 'permanent'")
    success = set_device_pairing_type(device_id, body.pairing_type)
    if not success:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")
    return {"status": "updated", "device_id": device_id, "pairing_type": body.pairing_type}

@router.get("/discovery/peers")
async def get_discovered_peers():
    """List any other peers discovered via mDNS on the LAN."""
    peers = discovery_service.get_discovered_peers()
    return {"peers": peers}
