import base64
from pathlib import Path
from typing import Tuple, Dict, Any
from fastapi import HTTPException, status
from server.app.database import get_shared_folder_by_id

def encode_file_id(folder_id: str, relative_path: str) -> str:
    """Encode folder_id and relative_path into an opaque, URL-safe string."""
    normalized_rel = relative_path.replace("\\", "/").strip("/")
    raw = f"{folder_id}::{normalized_rel}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8").rstrip("=")

def decode_file_id(file_id: str) -> Tuple[str, str]:
    """Decode an opaque file_id into (folder_id, relative_path)."""
    try:
        # Add padding back if necessary
        padded = file_id + "=" * (-len(file_id) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8")
        parts = decoded.split("::", 1)
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], parts[1]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file identifier format"
        )

def resolve_safe_path(folder_id: str, relative_path: str = "") -> Tuple[Path, Dict[str, Any]]:
    """
    Resolve a folder_id and relative subpath strictly inside the authorized shared folder.
    Prevents directory traversal, symlink escapes, and null byte injection.
    """
    folder = get_shared_folder_by_id(folder_id)
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shared folder '{folder_id}' not found or no longer active"
        )
    
    root_path = Path(folder["path"]).resolve()
    if not root_path.exists() or not root_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Shared folder directory is not accessible on the host device"
        )
    
    # Normalize relative path and remove leading slashes
    clean_rel = relative_path.replace("\\", "/").strip()
    while clean_rel.startswith("/"):
        clean_rel = clean_rel[1:]
    
    target_path = (root_path / clean_rel).resolve()
    
    # Strict boundary check against path traversal and symlink escapes
    try:
        target_path.relative_to(root_path)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Path traversal outside shared directory root"
        )
        
    return target_path, folder
