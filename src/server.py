# MIT License
# Copyright (c) 2024 Vortex Contributors
# See LICENSE file for full license text.

"""
HTTP server implementation for Vortex file gateway.

This module provides the core HTTP server functionality including:
- Thread pool-based server for concurrent connection handling
- Request handler with streaming file transfers
- HTTP Range request support for media seeking
- Directory ZIP download capability
- Security hardening (path traversal protection, security headers)
"""

import io
import os
import socket
import zipfile
from concurrent.futures import ThreadPoolExecutor
from email.utils import formatdate
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any, Callable, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from .constants import (
    CHUNK_SIZE,
    CONTENT_TYPE_HTML,
    CONTENT_TYPE_MULTIPART,
    CONTENT_TYPE_ZIP,
    DNS_SERVER,
    ENCODING,
    FALLBACK_IP,
    MAX_WORKERS,
)
from .ui import render_directory_listing
from .upload import UploadResult, extract_boundary, parse_multipart_streaming
from .utils import generate_etag, get_mime_type, is_path_safe, parse_range_header


# =============================================================================
# THREAD POOL SERVER
# =============================================================================


class PooledHTTPServer(HTTPServer):
    """
    HTTP server using a thread pool for controlled concurrency.

    Uses ThreadPoolExecutor to limit maximum concurrent connections,
    preventing resource exhaustion under high load while maintaining
    high throughput for file transfers.

    Attributes:
        executor: Thread pool for handling requests.
        allow_reuse_address: Enables socket reuse to avoid bind errors.
    """

    def __init__(
        self,
        server_address: Tuple[str, int],
        RequestHandlerClass: Callable[..., SimpleHTTPRequestHandler],
        max_workers: int = MAX_WORKERS,
    ) -> None:
        """
        Initialize the pooled HTTP server.

        Args:
            server_address: Tuple of (host, port) to bind to.
            RequestHandlerClass: Handler class for processing requests.
            max_workers: Maximum concurrent connections (default: 100).
        """
        super().__init__(server_address, RequestHandlerClass)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.allow_reuse_address = True
        self._shutdown_flag = False

    def process_request(
        self, request: socket.socket, client_address: Tuple[str, int]
    ) -> None:
        """Submit request to thread pool instead of blocking."""
        if not self._shutdown_flag:
            self.executor.submit(
                self._process_request_thread, request, client_address
            )

    def _process_request_thread(
        self, request: socket.socket, client_address: Tuple[str, int]
    ) -> None:
        """Process a single request in a thread pool worker."""
        try:
            self.finish_request(request, client_address)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
            # Client disconnected - normal behavior, no logging needed
            pass
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)

    def handle_error(
        self, request: socket.socket, client_address: Tuple[str, int]
    ) -> None:
        """Silently handle errors for cleaner output."""
        pass

    def shutdown(self) -> None:
        """Shutdown the server and thread pool."""
        self._shutdown_flag = True
        super().shutdown()

    def server_close(self) -> None:
        """Clean up the thread pool when server closes."""
        self._shutdown_flag = True
        super().server_close()
        self.executor.shutdown(wait=False, cancel_futures=True)


# =============================================================================
# HTTP REQUEST HANDLER
# =============================================================================


class VortexHandler(SimpleHTTPRequestHandler):
    """
    HTTP request handler for serving files and accepting uploads.

    Features:
        - HTTP Range requests for media seeking and download resumption
        - Chunked file streaming for memory-efficient large transfers
        - Comprehensive MIME type detection
        - Proper caching headers (ETag, Last-Modified, Cache-Control)
        - Security headers (X-Content-Type-Options, X-Frame-Options)
        - Path traversal protection
        - Robust error handling for network and filesystem errors

    Attributes:
        base_directory: Root directory being served (absolute path).
        protocol_version: HTTP/1.1 for persistent connections.
    """

    base_directory: str
    protocol_version = "HTTP/1.1"

    def __init__(
        self,
        *args: Any,
        directory: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the request handler.

        Args:
            directory: Directory to serve. Defaults to current directory.
        """
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
            pass  # Not all systems support these options

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default logging for cleaner output."""
        pass

    # -------------------------------------------------------------------------
    # Security Helpers
    # -------------------------------------------------------------------------

    def _send_security_headers(self) -> None:
        """Send security headers to prevent common attacks."""
        # Prevent MIME type sniffing attacks
        self.send_header("X-Content-Type-Options", "nosniff")
        # Prevent clickjacking by disallowing framing
        self.send_header("X-Frame-Options", "DENY")

    def _is_request_path_safe(self, path: str) -> bool:
        """
        Validate that a request path is safely within base_directory.

        Prevents directory traversal attacks using "../" or symlinks.

        Args:
            path: The filesystem path to validate.

        Returns:
            True if the path is safe, False otherwise.
        """
        return is_path_safe(Path(path), Path(self.base_directory))

    # -------------------------------------------------------------------------
    # Response Helpers
    # -------------------------------------------------------------------------

    def _send_html(self, content: str, status: int = 200) -> None:
        """Send an HTML response with proper headers."""
        encoded = content.encode(ENCODING, "surrogateescape")
        self.send_response(status)
        self.send_header("Content-Type", CONTENT_TYPE_HTML)
        self.send_header("Content-Length", str(len(encoded)))
        self._send_security_headers()
        self.end_headers()
        self.wfile.write(encoded)

    def _send_error_safe(self, code: int, message: str) -> None:
        """Send error response, catching any connection errors."""
        try:
            self.send_error(code, message)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    # -------------------------------------------------------------------------
    # ZIP Download Handler
    # -------------------------------------------------------------------------

    def _handle_zip_download(self, dir_path: str, include_body: bool = True) -> None:
        """
        Handle a request to download directory contents as a ZIP file.

        Creates an in-memory ZIP archive of all files in the directory
        (not recursive) and streams it to the client.

        Args:
            dir_path: Path to the directory to zip.
            include_body: Whether to include body (False for HEAD requests).
        """
        directory = Path(dir_path)
        dir_name = directory.name or "download"
        zip_filename = f"{dir_name}.zip"

        # Build ZIP in memory to determine size for Content-Length
        zip_buffer = io.BytesIO()

        try:
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
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

        # Send response
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPE_ZIP)
        self.send_header("Content-Length", str(zip_size))
        self.send_header(
            "Content-Disposition", f'attachment; filename="{zip_filename}"'
        )
        self.send_header("Cache-Control", "no-cache")
        self._send_security_headers()
        self.end_headers()

        # Stream ZIP content
        if include_body:
            try:
                while True:
                    chunk = zip_buffer.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

    # -------------------------------------------------------------------------
    # File Streaming
    # -------------------------------------------------------------------------

    def _stream_file(self, file_path: str, start: int, end: int) -> bool:
        """
        Stream a file range to the client in chunks.

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
            return False
        except OSError:
            return False

    # -------------------------------------------------------------------------
    # HTTP Method Handlers
    # -------------------------------------------------------------------------

    def do_HEAD(self) -> None:
        """Handle HEAD requests (same as GET but without body)."""
        self._handle_get_or_head(include_body=False)

    def do_GET(self) -> None:
        """
        Handle GET requests for directory listings and file downloads.

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

        # Security: Validate path is within base directory
        if not self._is_request_path_safe(path):
            self._send_error_safe(403, "Access denied")
            return

        # --- Directory Handling ---
        if os.path.isdir(path):
            # ZIP download request
            if query_params.get("download") == ["zip"]:
                self._handle_zip_download(path, include_body)
                return

            # Regular directory listing
            try:
                html_page = render_directory_listing(
                    self.base_directory, path, parsed.path
                )
                self._send_html(html_page)
            except (OSError, PermissionError) as e:
                self._send_error_safe(403, f"Cannot access directory: {e}")
            return

        # --- File Not Found ---
        if not os.path.isfile(path):
            self._send_error_safe(404, "File not found")
            return

        # --- File Handling ---
        try:
            file_stat = os.stat(path)
            file_size = file_stat.st_size
        except OSError as e:
            self._send_error_safe(403, f"Cannot access file: {e}")
            return

        # Generate response headers
        mime_type = get_mime_type(path)
        etag = generate_etag(path, file_stat)
        last_modified = formatdate(file_stat.st_mtime, usegmt=True)
        filename = os.path.basename(path)

        # Check If-None-Match for caching (304 Not Modified)
        if_none_match = self.headers.get("If-None-Match")
        if if_none_match and if_none_match == etag:
            self.send_response(304)
            self.end_headers()
            return

        # --- Range Request Handling ---
        range_header = self.headers.get("Range")

        if range_header:
            byte_range = parse_range_header(range_header, file_size)

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

        # --- Send Headers ---
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(content_length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("ETag", etag)
        self.send_header("Last-Modified", last_modified)
        self.send_header("Cache-Control", "public, max-age=3600")
        self.send_header("Content-Disposition", f'inline; filename="{filename}"')
        self._send_security_headers()
        self.end_headers()

        # Stream file content (skip for HEAD requests)
        if include_body and content_length > 0:
            self._stream_file(path, start, end)

    def do_POST(self) -> None:
        """
        Handle POST requests for file uploads via multipart/form-data.

        Uses streaming to handle large files without loading them entirely
        into memory. This allows uploading files of any size smoothly.
        """
        content_type = self.headers.get("Content-Type", "")

        if CONTENT_TYPE_MULTIPART not in content_type:
            self._send_error_safe(400, "Expected multipart/form-data")
            return

        boundary = extract_boundary(content_type)
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

        # Security: Validate upload path is within base directory
        if not self._is_request_path_safe(self.base_directory):
            self._send_error_safe(403, "Access denied")
            return

        # Stream upload to disk
        try:
            result: UploadResult = parse_multipart_streaming(
                self.rfile, length, boundary, self.base_directory
            )
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
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
            pass


# =============================================================================
# NETWORK UTILITIES
# =============================================================================


def get_local_ip() -> str:
    """
    Detect the local LAN IP address for shareable URLs.

    Uses a UDP socket to determine which local IP would be used
    to reach an external address. This works without actually
    sending any data, just by checking routing.

    Returns:
        The local IP address (e.g., "192.168.1.100"), or "127.0.0.1"
        if detection fails.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(DNS_SERVER)
        return sock.getsockname()[0]
    except OSError:
        return FALLBACK_IP
    finally:
        sock.close()


# =============================================================================
# SERVER ENTRY POINT
# =============================================================================


def run_server(directory: str, port: int, max_parallel: int = 4) -> None:
    """
    Start the Vortex HTTP server.

    Args:
        directory: Path to the directory to serve.
        port: Port number to listen on.
        max_parallel: Max parallel uploads hint for browser (unused server-side).

    The server uses a thread pool to handle multiple concurrent connections
    efficiently, with limits to prevent resource exhaustion.
    """
    resolved_directory = str(Path(directory).resolve())

    def handler_factory(*args: Any, **kwargs: Any) -> VortexHandler:
        return VortexHandler(*args, directory=resolved_directory, **kwargs)

    server_address = ("0.0.0.0", port)
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
