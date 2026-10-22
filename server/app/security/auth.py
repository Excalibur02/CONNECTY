from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status, Header, Query, Depends
from server.app.database import get_device_by_token, update_device_last_seen

async def get_current_device(
    request: Request,
    x_device_token: Optional[str] = Header(None, alias="X-Device-Token"),
    token: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Authenticate a device either via 'X-Device-Token' header or '?token=' query parameter.
    Localhost requests from the host laptop itself are granted admin full access.
    """
    client_host = request.client.host if request.client else ""
    is_localhost = client_host in ("127.0.0.1", "localhost", "::1", "testclient")
    
    auth_token = x_device_token or token
    
    if is_localhost and not auth_token:
        # Local admin on the laptop
        return {
            "device_id": "laptop-local-admin",
            "name": "Laptop (Local Admin)",
            "platform": "windows",
            "role": "full",
            "status": "approved",
            "is_local_admin": True
        }
        
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing device authentication token. Device must pair first."
        )
        
    device = get_device_by_token(auth_token)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked device token."
        )
        
    update_device_last_seen(device["device_id"])
    device["is_local_admin"] = False
    return device

def require_role(min_role: str = "read"):
    """
    Dependency that enforces required permission:
    - 'read': allowed for 'read-only' and 'full'
    - 'write': only allowed for 'full'
    """
    async def role_checker(device: Dict[str, Any] = Depends(get_current_device)) -> Dict[str, Any]:
        if min_role == "write" and device.get("role") == "read-only":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Device has read-only permission. Uploads or modifications are not permitted."
            )
        return device
    return role_checker
