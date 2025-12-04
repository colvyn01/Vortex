"""HTTP server implementation for Vortex file gateway."""

import io
import os
import re
import socket
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from email.utils import formatdate
from hashlib import md5
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any, Generator, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from .ui import render_directory_listing

# Constants
CONTENT_TYPE_HTML = "text/html; charset=utf-8"
CONTENT_TYPE_MULTIPART = "multipart/form-data"
CONTENT_TYPE_OCTET = "application/octet-stream"
CONTENT_TYPE_ZIP = "application/zip"
ENCODING = "utf-8"
FALLBACK_IP = "127.0.0.1"
DNS_SERVER = ("8.8.8.8", 80)

# Streaming upload constants
CHUNK_SIZE = 64 * 1024  # 64KB chunks for streaming
MAX_HEADER_SIZE = 8 * 1024  # 8KB max for multipart headers

# Thread pool settings
MAX_WORKERS = 100  # Maximum concurrent connections

# Comprehensive MIME type mapping for modern media formats
MIME_TYPES = {
    # Video formats
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".mkv": "video/x-matroska",
    ".webm": "video/webm",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    ".wmv": "video/x-ms-wmv",
    ".flv": "video/x-flv",
    ".ogv": "video/ogg",
    ".3gp": "video/3gpp",
    ".3g2": "video/3gpp2",
    ".ts": "video/mp2t",
    ".m2ts": "video/mp2t",
    ".mts": "video/mp2t",
    ".vob": "video/dvd",
    ".mpg": "video/mpeg",
    ".mpeg": "video/mpeg",
    # Audio formats
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".m4b": "audio/mp4",  # iPhone audiobook
    ".m4p": "audio/mp4",  # iTunes protected audio
    ".m4r": "audio/mp4",  # iPhone ringtone
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".oga": "audio/ogg",
    ".opus": "audio/opus",
    ".flac": "audio/flac",
    ".wav": "audio/wav",
    ".wma": "audio/x-ms-wma",
    ".aiff": "audio/aiff",
    ".aif": "audio/aiff",
    ".aifc": "audio/aiff",  # Compressed AIFF (Apple)
    ".caf": "audio/x-caf",  # Core Audio Format (Apple)
    ".mid": "audio/midi",
    ".midi": "audio/midi",
    ".weba": "audio/webm",
    ".mka": "audio/x-matroska",
    # Image formats
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".heic": "image/heic",  # iPhone photo format
    ".heif": "image/heif",  # iPhone photo format
    ".heics": "image/heic-sequence",  # iPhone photo sequence
    ".avif": "image/avif",
    ".raw": "image/raw",
    ".cr2": "image/x-canon-cr2",  # Canon RAW
    ".nef": "image/x-nikon-nef",  # Nikon RAW
    ".arw": "image/x-sony-arw",  # Sony RAW
    ".dng": "image/dng",  # Adobe Digital Negative / iPhone ProRAW
    # Document formats
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".txt": "text/plain",
    ".rtf": "application/rtf",
    ".csv": "text/csv",
    ".json": "application/json",
    ".xml": "application/xml",
    ".html": "text/html",
    ".htm": "text/html",
    ".css": "text/css",
    ".js": "application/javascript",
    ".md": "text/markdown",
    # Archive formats
    ".zip": "application/zip",
    ".rar": "application/vnd.rar",
    ".7z": "application/x-7z-compressed",
    ".tar": "application/x-tar",
    ".gz": "application/gzip",
    ".bz2": "application/x-bzip2",
    ".xz": "application/x-xz",
    # Streaming playlist formats
    ".m3u": "audio/x-mpegurl",
    ".m3u8": "application/vnd.apple.mpegurl",
    ".pls": "audio/x-scpls",
    # Font formats
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".eot": "application/vnd.ms-fontobject",
    # Other common formats
    ".apk": "application/vnd.android.package-archive",
    ".exe": "application/x-msdownload",
    ".dmg": "application/x-apple-diskimage",
    ".iso": "application/x-iso9660-image",
    ".torrent": "application/x-bittorrent",
}

# Windows invalid filename characters: \ / : * ? " < > |
INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')


def _get_mime_type(file_path: str) -> str:
    """Get MIME type for a file based on its extension.
    
    Args:
        file_path: Path to the file.
        
    Returns:
        MIME type string, defaults to application/octet-stream.
    """
    ext = os.path.splitext(file_path)[1].lower()
    return MIME_TYPES.get(ext, CONTENT_TYPE_OCTET)


def _generate_etag(file_path: str, file_stat: os.stat_result) -> str:
    """Generate an ETag for a file based on path, size, and modification time.
    
    Args:
        file_path: Path to the file.
        file_stat: os.stat() result for the file.
        
    Returns:
        ETag string in quotes.
    """
    etag_data = f"{file_path}:{file_stat.st_size}:{file_stat.st_mtime}"
    return f'"{md5(etag_data.encode()).hexdigest()}"'


def _parse_range_header(range_header: str, file_size: int) -> Optional[Tuple[int, int]]:
    """Parse HTTP Range header and return start and end byte positions.
    
    Supports single range requests only (e.g., "bytes=0-1023" or "bytes=500-").
    
    Args:
        range_header: The Range header value (e.g., "bytes=0-1023").
        file_size: Total size of the file in bytes.
        
    Returns:
        Tuple of (start, end) byte positions, or None if invalid.
    """
    if not range_header.startswith("bytes="):
        return None
    
    range_spec = range_header[6:].strip()
    
    # Handle multiple ranges (not supported, return None)
    if "," in range_spec:
        return None
    
    try:
        if range_spec.startswith("-"):
            # Suffix range: "-500" means last 500 bytes
            suffix_length = int(range_spec[1:])
            if suffix_length <= 0:
                return None
            start = max(0, file_size - suffix_length)
            end = file_size - 1
        elif range_spec.endswith("-"):
            # Open-ended range: "500-" means from byte 500 to end
            start = int(range_spec[:-1])
            end = file_size - 1
        else:
            # Explicit range: "0-1023"
            parts = range_spec.split("-")
            if len(parts) != 2:
                return None
            start = int(parts[0])
            end = int(parts[1])
        
        # Validate range
        if start < 0 or end < start or start >= file_size:
            return None
        
        # Clamp end to file size
        end = min(end, file_size - 1)
        
        return (start, end)
    except ValueError:
        return None


def _stream_directory_as_zip(directory_path: Path) -> Generator[bytes, None, None]:
    """Stream a directory's files as a ZIP archive.
    
    Creates a ZIP file in memory and yields chunks for streaming to client.
    Only includes files directly in the directory, not subdirectories.
    
    Args:
        directory_path: Path to the directory to zip.
        
    Yields:
        Chunks of ZIP file data.
    """
    # Create an in-memory buffer for the zip
    zip_buffer = io.BytesIO()
    
    try:
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for entry in directory_path.iterdir():
                try:
                    if entry.is_file():
                        # Add file to zip with just its name (no path)
                        zf.write(entry, entry.name)
                except (OSError, PermissionError):
                    # Skip files we can't read
                    continue
    except Exception:
        # If zip creation fails, yield nothing
        return
    
    # Yield the complete zip content
    zip_buffer.seek(0)
    while True:
        chunk = zip_buffer.read(CHUNK_SIZE)
        if not chunk:
            break
        yield chunk


def _sanitize_filename(filename: str) -> str:
    """Sanitize filename by replacing invalid characters for Windows compatibility.
    
    Args:
        filename: The original filename from the upload.
        
    Returns:
        A sanitized filename safe for Windows filesystems.
    """
    # Replace invalid characters with underscore
    sanitized = INVALID_FILENAME_CHARS.sub('_', filename)
    # Remove leading/trailing spaces and dots (Windows doesn't like these)
    sanitized = sanitized.strip(' .')
    # If filename is empty after sanitization, use a default
    if not sanitized:
        sanitized = "uploaded_file"
    return sanitized


@dataclass
class UploadResult:
    """Result of a file upload operation."""

    success: bool
    error_message: Optional[str] = None


def _extract_boundary(content_type: str) -> Optional[str]:
    """Extract multipart boundary from Content-Type header."""
    match = re.search(r"boundary=(.+)", content_type)
    if not match:
        return None

    boundary = match.group(1).strip()
    # Remove surrounding quotes if present
    if boundary.startswith('"') and boundary.endswith('"'):
        boundary = boundary[1:-1]
    return boundary


def _parse_multipart_streaming(
    rfile, content_length: int, boundary: str, base_directory: str
) -> UploadResult:
    """Parse multipart form data using streaming to handle large files.
    
    Instead of loading the entire request body into memory, this function
    streams the file data directly to disk in chunks.
    """
    boundary_bytes = ("--" + boundary).encode(ENCODING)
    end_boundary_bytes = ("--" + boundary + "--").encode(ENCODING)
    remaining = content_length
    
    # Read until we find the first boundary
    header_buffer = b""
    while remaining > 0 and boundary_bytes not in header_buffer:
        to_read = min(1024, remaining)
        chunk = rfile.read(to_read)
        if not chunk:
            break
        remaining -= len(chunk)
        header_buffer += chunk
        if len(header_buffer) > MAX_HEADER_SIZE:
            return UploadResult(success=False, error_message="Headers too large")
    
    # Find the start of headers after boundary
    boundary_pos = header_buffer.find(boundary_bytes)
    if boundary_pos == -1:
        return UploadResult(success=False, error_message="No boundary found")
    
    # Skip past boundary and CRLF
    header_start = boundary_pos + len(boundary_bytes)
    header_buffer = header_buffer[header_start:].lstrip(b"\r\n")
    
    # Read headers until we hit the double CRLF that separates headers from body
    while b"\r\n\r\n" not in header_buffer and remaining > 0:
        to_read = min(1024, remaining)
        chunk = rfile.read(to_read)
        if not chunk:
            break
        remaining -= len(chunk)
        header_buffer += chunk
        if len(header_buffer) > MAX_HEADER_SIZE:
            return UploadResult(success=False, error_message="Headers too large")
    
    if b"\r\n\r\n" not in header_buffer:
        return UploadResult(success=False, error_message="Malformed multipart data")
    
    headers_block, file_data_start = header_buffer.split(b"\r\n\r\n", 1)
    headers_text = headers_block.decode(ENCODING, "replace")
    
    # Extract filename
    if 'name="file"' not in headers_text:
        return UploadResult(success=False, error_message="No file field found")
    
    filename_match = re.search(r'filename="([^"]+)"', headers_text)
    if not filename_match:
        return UploadResult(success=False, error_message="No filename in upload")
    
    filename = os.path.basename(filename_match.group(1))
    filename = _sanitize_filename(filename)
    if not filename:
        return UploadResult(success=False, error_message="Empty filename")
    
    dest_path = os.path.join(base_directory, filename)
    
    # Use a temporary file first, then move to destination
    # This ensures partial uploads don't corrupt the destination
    temp_fd = None
    temp_path = None
    try:
        temp_fd, temp_path = tempfile.mkstemp(dir=base_directory, prefix=".upload_")
        with os.fdopen(temp_fd, "wb") as temp_file:
            temp_fd = None  # fdopen takes ownership
            
            # Write the data we already read after headers
            # But first check if it contains the end boundary
            boundary_pos = file_data_start.find(boundary_bytes)
            if boundary_pos != -1:
                # Entire file was in the initial buffer
                file_data = file_data_start[:boundary_pos]
                if file_data.endswith(b"\r\n"):
                    file_data = file_data[:-2]
                temp_file.write(file_data)
            else:
                # Need to stream the rest
                # Write initial data (keep potential partial boundary at end)
                boundary_len = len(boundary_bytes)
                if len(file_data_start) > boundary_len + 2:
                    safe_len = len(file_data_start) - boundary_len - 2
                    temp_file.write(file_data_start[:safe_len])
                    buffer = file_data_start[safe_len:]
                else:
                    buffer = file_data_start
                
                # Stream remaining data
                while remaining > 0:
                    to_read = min(CHUNK_SIZE, remaining)
                    chunk = rfile.read(to_read)
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    buffer += chunk
                    
                    # Check for boundary
                    boundary_pos = buffer.find(boundary_bytes)
                    if boundary_pos != -1:
                        # Write everything before boundary
                        data_to_write = buffer[:boundary_pos]
                        if data_to_write.endswith(b"\r\n"):
                            data_to_write = data_to_write[:-2]
                        temp_file.write(data_to_write)
                        break
                    
                    # Write safe portion, keep potential boundary overlap
                    safe_len = len(buffer) - boundary_len - 2
                    if safe_len > 0:
                        temp_file.write(buffer[:safe_len])
                        buffer = buffer[safe_len:]
                else:
                    # No boundary found, write remaining buffer
                    if buffer:
                        if buffer.endswith(b"\r\n"):
                            buffer = buffer[:-2]
                        if buffer.endswith(b"--"):
                            buffer = buffer[:-2]
                        temp_file.write(buffer)
        
        # Move temp file to destination
        # Remove destination if it exists
        if os.path.exists(dest_path):
            os.remove(dest_path)
        os.rename(temp_path, dest_path)
        temp_path = None  # Successfully moved
        
        return UploadResult(success=True)
        
    except OSError as e:
        return UploadResult(success=False, error_message=f"Failed to save file: {e}")
    finally:
        # Clean up temp file if it still exists
        if temp_fd is not None:
            try:
                os.close(temp_fd)
            except OSError:
                pass
        if temp_path is not None:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def _parse_multipart_file(
    body: bytes, boundary: str, base_directory: str
) -> UploadResult:
    """Parse multipart form data and save uploaded file (legacy non-streaming version)."""
    boundary_bytes = ("--" + boundary).encode(ENCODING)
    parts = body.split(boundary_bytes)

    for part in parts:
        if not part or part.startswith(b"--"):
            continue

        part = part.lstrip(b"\r\n")
        if part.startswith(b"--"):
            continue

        if b"\r\n\r\n" not in part:
            continue

        headers_block, file_data = part.split(b"\r\n\r\n", 1)
        headers_text = headers_block.decode(ENCODING, "replace")

        if 'name="file"' not in headers_text:
            continue

        filename_match = re.search(r'filename="([^"]+)"', headers_text)
        if not filename_match:
            return UploadResult(success=False, error_message="No filename in upload")

        filename = os.path.basename(filename_match.group(1))
        filename = _sanitize_filename(filename)

        # Strip trailing boundary markers from file data
        file_data = _strip_trailing_markers(file_data)

        dest_path = os.path.join(base_directory, filename)

        try:
            with open(dest_path, "wb") as f:
                f.write(file_data)
            return UploadResult(success=True)
        except OSError as e:
            return UploadResult(success=False, error_message=f"Failed to save file: {e}")

    return UploadResult(success=False, error_message="No valid file part found")


def _strip_trailing_markers(data: bytes) -> bytes:
    """Remove trailing CRLF and boundary markers from file data."""
    if data.endswith(b"\r\n"):
        data = data[:-2]
    if data.endswith(b"--"):
        data = data[:-2]
    return data


class PooledHTTPServer(HTTPServer):
    """HTTP server using a thread pool for controlled concurrency.
    
    Uses ThreadPoolExecutor to limit maximum concurrent connections,
    preventing resource exhaustion under high load while maintaining
    high throughput.
    """
    
    def __init__(self, server_address: Tuple[str, int], RequestHandlerClass, max_workers: int = MAX_WORKERS):
        super().__init__(server_address, RequestHandlerClass)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        # Allow socket reuse to avoid "Address already in use" errors
        self.allow_reuse_address = True
        self._shutdown_flag = False
    
    def process_request(self, request, client_address):
        """Submit request to thread pool instead of blocking."""
        if not self._shutdown_flag:
            self.executor.submit(self._process_request_thread, request, client_address)
    
    def _process_request_thread(self, request, client_address):
        """Process a single request in a thread pool worker."""
        try:
            self.finish_request(request, client_address)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
            # Client disconnected - this is normal, don't log as error
            pass
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)
    
    def handle_error(self, request, client_address):
        """Silently handle errors - don't print stack traces for normal disconnects."""
        pass  # Suppress default error logging for cleaner output
    
    def shutdown(self):
        """Shutdown the server and thread pool immediately."""
        self._shutdown_flag = True
        super().shutdown()
    
    def server_close(self):
        """Clean up the thread pool when server shuts down."""
        self._shutdown_flag = True
        super().server_close()
        # Force immediate shutdown, cancel pending tasks
        self.executor.shutdown(wait=False, cancel_futures=True)


class VortexHandler(SimpleHTTPRequestHandler):
    """HTTP request handler for serving files and accepting uploads.
    
    Features:
    - HTTP Range requests for media seeking and download resumption
    - Chunked file streaming for memory-efficient large file transfers
    - Comprehensive MIME type detection
    - Proper caching headers (ETag, Last-Modified, Cache-Control)
    - Robust error handling for network and filesystem errors
    """

    base_directory: str
    protocol_version = "HTTP/1.1"  # Enable persistent connections

    def __init__(self, *args: Any, directory: Optional[str] = None, **kwargs: Any):
        if directory is None:
            directory = os.getcwd()
        self.base_directory = os.path.abspath(directory)
        super().__init__(*args, directory=directory, **kwargs)
    
    def setup(self) -> None:
        """Set up the connection with optimized socket options."""
        super().setup()
        try:
            # Increase socket buffer sizes for better throughput
            self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 256 * 1024)
            self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 256 * 1024)
            # Disable Nagle's algorithm for lower latency
            self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except (OSError, AttributeError):
            pass  # Not all systems support this
    
    def log_message(self, format: str, *args) -> None:
        """Suppress default logging for cleaner output."""
        pass  # Quiet mode - remove this line to enable logging

    def _send_html(self, content: str, status: int = 200) -> None:
        """Send an HTML response with proper headers."""
        encoded = content.encode(ENCODING, "surrogateescape")
        self.send_response(status)
        self.send_header("Content-Type", CONTENT_TYPE_HTML)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)
    
    def _send_error_safe(self, code: int, message: str) -> None:
        """Send error response, catching any connection errors."""
        try:
            self.send_error(code, message)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass  # Client disconnected, nothing to do
    
    def _handle_zip_download(self, dir_path: str, include_body: bool = True) -> None:
        """Handle a request to download directory contents as a ZIP file.
        
        Args:
            dir_path: Path to the directory to zip.
            include_body: Whether to include the body (False for HEAD requests).
        """
        directory = Path(dir_path)
        dir_name = directory.name or "download"
        zip_filename = f"{dir_name}.zip"
        
        # Collect all files and calculate total size for the zip
        # We need to build the zip in memory to know its size
        zip_buffer = io.BytesIO()
        
        try:
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for entry in directory.iterdir():
                    try:
                        if entry.is_file():
                            zf.write(entry, entry.name)
                    except (OSError, PermissionError):
                        continue
        except Exception as e:
            self._send_error_safe(500, f"Failed to create ZIP: {e}")
            return
        
        zip_size = zip_buffer.tell()
        zip_buffer.seek(0)
        
        if zip_size == 0:
            self._send_error_safe(404, "No files to download")
            return
        
        # Send response headers
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPE_ZIP)
        self.send_header("Content-Length", str(zip_size))
        self.send_header("Content-Disposition", f'attachment; filename="{zip_filename}"')
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        
        # Stream zip content
        if include_body:
            try:
                while True:
                    chunk = zip_buffer.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass  # Client disconnected
    
    def _stream_file(self, file_path: str, start: int, end: int) -> bool:
        """Stream a file range to the client in chunks.
        
        Args:
            file_path: Path to the file to stream.
            start: Starting byte position.
            end: Ending byte position (inclusive).
            
        Returns:
            True if streaming completed successfully, False otherwise.
        """
        bytes_to_send = end - start + 1
        
        try:
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = bytes_to_send
                
                while remaining > 0:
                    chunk_size = min(CHUNK_SIZE, remaining)
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
            
            return True
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # Client disconnected mid-transfer - this is normal
            return False
        except OSError:
            return False

    def do_HEAD(self) -> None:
        """Handle HEAD requests (same as GET but without body)."""
        self._handle_get_or_head(include_body=False)
    
    def do_GET(self) -> None:
        """Handle GET requests for directory listings and file downloads.
        
        Supports HTTP Range requests for media seeking and download resumption.
        Uses chunked streaming for memory-efficient large file transfers.
        """
        self._handle_get_or_head(include_body=True)
    
    def _handle_get_or_head(self, include_body: bool = True) -> None:
        """Common handler for GET and HEAD requests."""
        # Parse URL for query parameters
        parsed = urlparse(self.path)
        query_params = parse_qs(parsed.query)
        path = self.translate_path(parsed.path)
        
        # Directory handling
        if os.path.isdir(path):
            # Check for zip download request
            if query_params.get('download') == ['zip']:
                self._handle_zip_download(path, include_body)
                return
            
            # Regular directory listing
            try:
                html_page = render_directory_listing(self.base_directory, path, parsed.path)
                self._send_html(html_page)
            except (OSError, PermissionError) as e:
                self._send_error_safe(403, f"Cannot access directory: {e}")
            return
        
        # File not found
        if not os.path.isfile(path):
            self._send_error_safe(404, "File not found")
            return
        
        # Get file info
        try:
            file_stat = os.stat(path)
            file_size = file_stat.st_size
        except OSError as e:
            self._send_error_safe(403, f"Cannot access file: {e}")
            return
        
        # Generate headers
        mime_type = _get_mime_type(path)
        etag = _generate_etag(path, file_stat)
        last_modified = formatdate(file_stat.st_mtime, usegmt=True)
        filename = os.path.basename(path)
        
        # Check If-None-Match (ETag validation)
        if_none_match = self.headers.get("If-None-Match")
        if if_none_match and if_none_match == etag:
            self.send_response(304)  # Not Modified
            self.end_headers()
            return
        
        # Check for Range request
        range_header = self.headers.get("Range")
        
        if range_header:
            # Parse range
            byte_range = _parse_range_header(range_header, file_size)
            
            if byte_range is None:
                # Invalid range - send 416 Range Not Satisfiable
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{file_size}")
                self.end_headers()
                return
            
            start, end = byte_range
            content_length = end - start + 1
            
            # Send 206 Partial Content
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        else:
            # Full file request
            start, end = 0, file_size - 1
            content_length = file_size
            self.send_response(200)
        
        # Common headers
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(content_length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("ETag", etag)
        self.send_header("Last-Modified", last_modified)
        self.send_header("Cache-Control", "public, max-age=3600")
        # Content-Disposition for download hint
        self.send_header("Content-Disposition", f'inline; filename="{filename}"')
        # CORS headers for media playback
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        
        # Stream file content (skip for HEAD requests)
        if include_body and content_length > 0:
            self._stream_file(path, start, end)

    def do_POST(self) -> None:
        """Handle POST requests for file uploads via multipart/form-data.
        
        Uses streaming to handle large files without loading them entirely
        into memory. This allows uploading files of any size smoothly.
        """
        content_type = self.headers.get("Content-Type", "")

        if CONTENT_TYPE_MULTIPART not in content_type:
            self._send_error_safe(400, "Expected multipart/form-data")
            return

        boundary = _extract_boundary(content_type)
        if not boundary:
            self._send_error_safe(400, "No multipart boundary found")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_error_safe(400, "Missing or invalid Content-Length")
            return
        
        if length <= 0:
            self._send_error_safe(400, "Invalid Content-Length")
            return

        # Use streaming upload for all files to handle large uploads smoothly
        try:
            result = _parse_multipart_streaming(
                self.rfile, length, boundary, self.base_directory
            )
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # Client disconnected during upload
            return

        if not result.success:
            self._send_error_safe(400, result.error_message or "Upload failed")
            return

        # Redirect back to root after successful upload
        try:
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass  # Client already disconnected


def get_local_ip() -> str:
    """Detect LAN IP address for shareable URL.

    Uses a UDP socket to determine the local IP that would be used
    to reach an external address. Falls back to localhost on failure.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(DNS_SERVER)
        return sock.getsockname()[0]
    except OSError:
        return FALLBACK_IP
    finally:
        sock.close()


def run_server(directory: str, port: int, max_parallel: int = 4) -> None:
    """Start the Vortex HTTP server.

    Args:
        directory: Path to the directory to serve.
        port: Port number to listen on.
        max_parallel: Max parallel uploads hint for browser (unused server-side).
    
    Uses a thread pool server to handle multiple concurrent connections
    efficiently, with limits to prevent resource exhaustion.
    """
    resolved_directory = str(Path(directory).resolve())

    def handler_factory(*args: Any, **kwargs: Any) -> VortexHandler:
        return VortexHandler(*args, directory=resolved_directory, **kwargs)

    server_address = ("0.0.0.0", port)
    # Use PooledHTTPServer for controlled concurrent request handling
    httpd = PooledHTTPServer(server_address, handler_factory, max_workers=MAX_WORKERS)
    
    ip = get_local_ip()
    print("Vortex active")
    print(f"Serving directory: {resolved_directory}")
    print(f"Share this on your Wi-Fi:  http://{ip}:{port}/")
    print(f"Max concurrent connections: {MAX_WORKERS}")
    print("Press Ctrl+C to stop.")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print("\nVortex deactivated.")
        httpd.shutdown()
        httpd.server_close()
