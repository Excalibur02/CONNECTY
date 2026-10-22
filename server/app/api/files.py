from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, Request, HTTPException, status
from pydantic import BaseModel
from server.app.database import get_shared_folders, add_shared_folder, remove_shared_folder, update_shared_folder
from server.app.security.auth import require_role
from server.app.services.file_service import list_folder_contents, serve_file_stream, get_file_metadata
from server.app.security.path_validator import decode_file_id

router = APIRouter(prefix="/api/v1", tags=["files"])

class AddFolderRequest(BaseModel):
    name: str
    path: str
    allow_write: bool = True

class UpdateFolderRequest(BaseModel):
    name: Optional[str] = None
    path: Optional[str] = None
    allow_write: Optional[bool] = None

@router.get("/folders")
async def list_folders(current_device: Dict[str, Any] = Depends(require_role("read"))):
    """List approved shared folders available on this laptop."""
    folders = get_shared_folders(only_active=True)
    safe_folders = []
    for f in folders:
        safe_folders.append({
            "id": f["id"],
            "name": f["name"],
            "path": f["path"],
            "allow_write": bool(f["allow_write"]),
            "is_active": bool(f["is_active"])
        })
    return {"folders": safe_folders}

@router.put("/folders/{folder_id}")
async def edit_shared_folder(
    folder_id: str,
    body: UpdateFolderRequest,
    current_device: Dict[str, Any] = Depends(require_role("write"))
):
    """Update an existing shared folder (e.g. change the default shared resources folder path)."""
    if body.path is not None:
        folder_path = Path(body.path)
        if not folder_path.exists() or not folder_path.is_dir():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path '{body.path}' does not exist or is not a directory on the host"
            )
    updated = update_shared_folder(
        folder_id=folder_id,
        name=body.name,
        path=body.path,
        allow_write=body.allow_write
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Shared folder not found")
    return {"status": "updated", "folder": updated}

@router.post("/folders")
async def create_shared_folder(
    body: AddFolderRequest,
    current_device: Dict[str, Any] = Depends(require_role("write"))
):
    """Add a new directory on the laptop to share."""
    folder_path = Path(body.path)
    if not folder_path.exists() or not folder_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path '{body.path}' does not exist or is not a directory on the host"
        )
    folder = add_shared_folder(name=body.name, path=body.path, allow_write=body.allow_write)
    return {"status": "created", "folder": folder}

@router.delete("/folders/{folder_id}")
async def delete_shared_folder(
    folder_id: str,
    current_device: Dict[str, Any] = Depends(require_role("write"))
):
    """Remove a shared folder from sharing."""
    success = remove_shared_folder(folder_id)
    if not success:
        raise HTTPException(status_code=404, detail="Shared folder not found")
    return {"status": "deleted", "folder_id": folder_id}

@router.get("/files")
async def browse_files(
    folder: str = Query("default", description="Folder ID or 'default'"),
    subpath: str = Query("", description="Relative subpath inside the folder"),
    current_device: Dict[str, Any] = Depends(require_role("read"))
):
    """
    List files and directories inside an authorized shared folder.
    Use opaque file IDs to navigate and stream.
    """
    return list_folder_contents(folder_id=folder, subpath=subpath)

@router.head("/files/{file_id}")
async def check_file(
    file_id: str,
    request: Request,
    current_device: Dict[str, Any] = Depends(require_role("read"))
):
    """Check file size and range capabilities."""
    return serve_file_stream(request, file_id, as_attachment=False)

@router.get("/files/{file_id}")
async def get_or_stream_file(
    file_id: str,
    request: Request,
    download: bool = Query(False, description="Set true to force browser download attachment"),
    current_device: Dict[str, Any] = Depends(require_role("read"))
):
    """
    Stream media or download file.
    Supports HTTP 206 Partial Content and byte-range requests for video seeking and resumption.
    """
    return serve_file_stream(request, file_id, as_attachment=download)
