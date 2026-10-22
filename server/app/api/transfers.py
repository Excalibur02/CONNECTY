from typing import Dict, Any
from fastapi import APIRouter, Depends, Request, HTTPException, status
from pydantic import BaseModel
from server.app.security.auth import require_role
from server.app.services.transfer_service import (
    init_upload_transfer,
    write_chunk,
    get_status,
    finalize_transfer
)

router = APIRouter(prefix="/api/v1/transfers", tags=["transfers"])

class TransferInitRequest(BaseModel):
    filename: str
    total_size: int
    total_chunks: int
    chunk_size: int
    expected_hash: str
    target_folder_id: str = "default"
    target_subpath: str = ""

@router.post("")
async def create_transfer(
    body: TransferInitRequest,
    current_device: Dict[str, Any] = Depends(require_role("write"))
):
    """Initiate a chunk-based resumable file transfer."""
    record = init_upload_transfer(
        filename=body.filename,
        total_size=body.total_size,
        total_chunks=body.total_chunks,
        chunk_size=body.chunk_size,
        expected_hash=body.expected_hash,
        target_folder_id=body.target_folder_id,
        target_subpath=body.target_subpath
    )
    return record

@router.put("/{transfer_id}/chunks/{chunk_index}")
async def upload_chunk(
    transfer_id: str,
    chunk_index: int,
    request: Request,
    current_device: Dict[str, Any] = Depends(require_role("write"))
):
    """Upload a specific chunk of the file."""
    chunk_bytes = await request.body()
    if not chunk_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chunk body cannot be empty"
        )
    return write_chunk(transfer_id, chunk_index, chunk_bytes)

@router.get("/{transfer_id}")
async def get_transfer_progress(
    transfer_id: str,
    current_device: Dict[str, Any] = Depends(require_role("read"))
):
    """Get the list of successfully received chunks to enable resuming interrupted uploads."""
    return get_status(transfer_id)

@router.post("/{transfer_id}/complete")
async def complete_transfer(
    transfer_id: str,
    current_device: Dict[str, Any] = Depends(require_role("write"))
):
    """
    Finalize transfer: assemble chunks, verify whole-file SHA-256 checksum,
    and atomically move to the target shared directory.
    """
    return finalize_transfer(transfer_id)
