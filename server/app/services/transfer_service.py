import os
import shutil
import hashlib
import uuid
from pathlib import Path
from typing import Dict, Any, List
from fastapi import HTTPException, status
from server.app.config import settings
from server.app.database import (
    create_transfer_record,
    get_transfer_record,
    update_transfer_chunk,
    update_transfer_status
)
from server.app.security.path_validator import resolve_safe_path, encode_file_id

def init_upload_transfer(
    filename: str,
    total_size: int,
    total_chunks: int,
    chunk_size: int,
    expected_hash: str,
    target_folder_id: str,
    target_subpath: str = ""
) -> Dict[str, Any]:
    """Initiate a chunked upload transfer."""
    # Ensure destination folder exists and allows writing
    dest_path, folder = resolve_safe_path(target_folder_id, target_subpath)
    if not folder.get("allow_write"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Shared folder does not allow write/upload operations"
        )
        
    transfer_id = str(uuid.uuid4())
    staging_dir = settings.STAGING_DIR / transfer_id
    staging_dir.mkdir(parents=True, exist_ok=True)
    
    clean_filename = Path(filename).name  # Prevent path traversal in filename
    
    record = create_transfer_record(
        transfer_id=transfer_id,
        filename=clean_filename,
        total_size=total_size,
        total_chunks=total_chunks,
        chunk_size=chunk_size,
        expected_hash=expected_hash,
        target_folder_id=target_folder_id,
        target_subpath=target_subpath
    )
    return record

def write_chunk(transfer_id: str, chunk_index: int, chunk_bytes: bytes) -> Dict[str, Any]:
    """Store an uploaded chunk in the transfer staging directory."""
    record = get_transfer_record(transfer_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transfer '{transfer_id}' not found"
        )
        
    if chunk_index < 0 or chunk_index >= record["total_chunks"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chunk index {chunk_index} out of range [0, {record['total_chunks'] - 1}]"
        )
        
    staging_dir = settings.STAGING_DIR / transfer_id
    staging_dir.mkdir(parents=True, exist_ok=True)
    chunk_path = staging_dir / f"chunk_{chunk_index:06d}.part"
    
    with open(chunk_path, "wb") as f:
        f.write(chunk_bytes)
        
    update_transfer_chunk(transfer_id, chunk_index)
    return {
        "transfer_id": transfer_id,
        "chunk_index": chunk_index,
        "bytes_received": len(chunk_bytes),
        "status": "received"
    }

def get_status(transfer_id: str) -> Dict[str, Any]:
    """Get the current state and list of received chunks for resumption."""
    record = get_transfer_record(transfer_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transfer '{transfer_id}' not found"
        )
    return record

def finalize_transfer(transfer_id: str) -> Dict[str, Any]:
    """
    Assemble all uploaded chunks, verify SHA-256 hash, and atomically
    move the file to the destination shared folder.
    """
    record = get_transfer_record(transfer_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transfer '{transfer_id}' not found"
        )
        
    staging_dir = settings.STAGING_DIR / transfer_id
    if not staging_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transfer staging directory is missing"
        )
        
    # Check all chunks
    total_chunks = record["total_chunks"]
    missing_chunks = []
    chunk_files = []
    
    for i in range(total_chunks):
        p = staging_dir / f"chunk_{i:06d}.part"
        if not p.exists():
            missing_chunks.append(i)
        else:
            chunk_files.append(p)
            
    if missing_chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transfer incomplete. Missing {len(missing_chunks)} chunks: {missing_chunks[:10]}..."
        )
        
    # Assemble into temporary combined file and compute SHA-256
    assembled_tmp = settings.STAGING_DIR / f"{transfer_id}.assembled"
    sha256 = hashlib.sha256()
    
    try:
        with open(assembled_tmp, "wb") as out_f:
            for chunk_file in chunk_files:
                with open(chunk_file, "rb") as in_f:
                    while True:
                        block = in_f.read(128 * 1024)
                        if not block:
                            break
                        sha256.update(block)
                        out_f.write(block)
                        
        computed_hash = sha256.hexdigest().lower()
        expected = record["expected_hash"].lower()
        
        if expected not in ("", "auto") and computed_hash != expected:
            if assembled_tmp.exists():
                assembled_tmp.unlink()
            update_transfer_status(transfer_id, "hash_mismatch")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File verification failed: computed hash {computed_hash} != expected {expected}"
            )
            
        # Target destination inside shared folder
        dest_dir, folder = resolve_safe_path(record["target_folder_id"], record["target_subpath"])
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        filename = record["filename"]
        target_file = dest_dir / filename
        
        # Avoid accidental overwrite by adding a suffix if exists
        counter = 1
        stem = Path(filename).stem
        ext = Path(filename).suffix
        while target_file.exists():
            target_file = dest_dir / f"{stem}_{counter}{ext}"
            counter += 1
            
        shutil.move(str(assembled_tmp), str(target_file))
        
        # Clean up chunk staging directory
        try:
            shutil.rmtree(str(staging_dir))
        except Exception:
            pass
            
        update_transfer_status(transfer_id, "completed")
        
        # Compute relative path for file_id
        folder_root = Path(folder["path"]).resolve()
        rel_posix = target_file.relative_to(folder_root).as_posix()
        file_id = encode_file_id(record["target_folder_id"], rel_posix)
        
        return {
            "transfer_id": transfer_id,
            "status": "completed",
            "filename": target_file.name,
            "file_id": file_id,
            "size": target_file.stat().st_size,
            "sha256": computed_hash
        }
    except Exception as e:
        if assembled_tmp.exists():
            assembled_tmp.unlink()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to finalize transfer: {str(e)}"
        )
