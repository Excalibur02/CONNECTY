import os
import mimetypes
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Generator
from fastapi import Request, HTTPException, status
from fastapi.responses import StreamingResponse, Response
from server.app.security.path_validator import encode_file_id, decode_file_id, resolve_safe_path

CHUNK_SIZE = 128 * 1024  # 128 KiB for streaming

def get_mime_type(path: Path) -> str:
    """Guess MIME type with defaults for common media types."""
    mime, _ = mimetypes.guess_type(str(path))
    if not mime:
        ext = path.suffix.lower()
        if ext in (".mkv", ".webm"):
            return "video/webm"
        elif ext in (".mp4", ".m4v"):
            return "video/mp4"
        elif ext in (".mp3", ".flac", ".wav", ".aac"):
            return "audio/mpeg"
        return "application/octet-stream"
    return mime

def list_folder_contents(folder_id: str, subpath: str = "") -> Dict[str, Any]:
    """List directory contents for an authorized folder."""
    target_path, folder = resolve_safe_path(folder_id, subpath)
    
    if not target_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requested path does not exist"
        )
        
    if not target_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested path is a file, not a directory"
        )
        
    entries = []
    root_path = Path(folder["path"]).resolve()
    
    for entry in target_path.iterdir():
        try:
            rel_to_root = entry.relative_to(root_path).as_posix()
            file_id = encode_file_id(folder_id, rel_to_root)
            stat = entry.stat()
            is_dir = entry.is_dir()
            
            entries.append({
                "id": file_id,
                "name": entry.name,
                "is_dir": is_dir,
                "size": stat.st_size if not is_dir else 0,
                "mime_type": "inode/directory" if is_dir else get_mime_type(entry),
                "modified": stat.st_mtime,
                "relative_path": rel_to_root
            })
        except Exception:
            continue

    # Sort directories first, then alphabetical by name
    entries.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
    
    curr_rel = target_path.relative_to(root_path).as_posix()
    parent_rel = ""
    has_parent = False
    parent_id = None
    
    if curr_rel and curr_rel != ".":
        has_parent = True
        parent_path = target_path.parent
        if parent_path != root_path and parent_path.is_relative_to(root_path):
            parent_rel = parent_path.relative_to(root_path).as_posix()
            parent_id = encode_file_id(folder_id, parent_rel)
        else:
            parent_id = encode_file_id(folder_id, "")

    return {
        "folder_id": folder_id,
        "folder_name": folder["name"],
        "allow_write": bool(folder["allow_write"]),
        "current_path": curr_rel if curr_rel != "." else "",
        "has_parent": has_parent,
        "parent_id": parent_id,
        "items": entries
    }

def file_chunk_generator(file_path: Path, start: int, length: int) -> Generator[bytes, None, None]:
    """Read a specific slice of a file in chunks without loading all into memory."""
    with open(file_path, "rb") as f:
        f.seek(start)
        remaining = length
        while remaining > 0:
            bytes_to_read = min(CHUNK_SIZE, remaining)
            data = f.read(bytes_to_read)
            if not data:
                break
            remaining -= len(data)
            yield data

def parse_range_header(range_header: str, file_size: int) -> Tuple[int, int]:
    """
    Parse HTTP Range header: 'bytes=start-end'
    Supports:
      bytes=0-1023
      bytes=1024-
      bytes=-500 (suffix)
    """
    if not range_header.startswith("bytes="):
        raise ValueError("Invalid range unit")
    
    range_spec = range_header[6:].strip()
    if "," in range_spec:
        # Multipart range not needed for standard streaming; take first
        range_spec = range_spec.split(",")[0].strip()
        
    parts = range_spec.split("-")
    if len(parts) != 2:
        raise ValueError("Malformed range")
        
    start_str, end_str = parts[0].strip(), parts[1].strip()
    
    if start_str and end_str:
        start = int(start_str)
        end = int(end_str)
    elif start_str and not end_str:
        start = int(start_str)
        end = file_size - 1
    elif not start_str and end_str:
        suffix = int(end_str)
        start = max(0, file_size - suffix)
        end = file_size - 1
    else:
        raise ValueError("Empty range bounds")
        
    if start < 0 or start >= file_size or end < start:
        raise ValueError("Range out of bounds")
        
    end = min(end, file_size - 1)
    return start, end

def get_file_metadata(file_id: str) -> Dict[str, Any]:
    """Get metadata for a specific file by its opaque ID."""
    folder_id, relative_path = decode_file_id(file_id)
    target_path, folder = resolve_safe_path(folder_id, relative_path)
    
    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
        
    stat = target_path.stat()
    return {
        "id": file_id,
        "name": target_path.name,
        "size": stat.st_size,
        "mime_type": get_mime_type(target_path),
        "modified": stat.st_mtime,
        "path": target_path
    }

def serve_file_stream(request: Request, file_id: str, as_attachment: bool = False) -> Response:
    """
    Serve a file with full HTTP Byte Range support (206 Partial Content),
    essential for video seeking, audio scrubbing, and resumable downloads.
    """
    meta = get_file_metadata(file_id)
    file_path: Path = meta["path"]
    file_size: int = meta["size"]
    mime_type: str = meta["mime_type"]
    filename: str = meta["name"]
    
    range_header = request.headers.get("Range")
    
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Type": mime_type,
    }
    
    if as_attachment:
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    else:
        headers["Content-Disposition"] = f'inline; filename="{filename}"'

    if request.method == "HEAD":
        headers["Content-Length"] = str(file_size)
        return Response(status_code=status.HTTP_200_OK, headers=headers)

    if range_header:
        try:
            start, end = parse_range_header(range_header, file_size)
        except ValueError:
            return Response(
                status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
                headers={"Content-Range": f"bytes */{file_size}"}
            )
            
        content_length = (end - start) + 1
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        headers["Content-Length"] = str(content_length)
        
        return StreamingResponse(
            file_chunk_generator(file_path, start, content_length),
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            headers=headers,
            media_type=mime_type
        )
    else:
        # Full content response
        headers["Content-Length"] = str(file_size)
        return StreamingResponse(
            file_chunk_generator(file_path, 0, file_size),
            status_code=status.HTTP_200_OK,
            headers=headers,
            media_type=mime_type
        )
