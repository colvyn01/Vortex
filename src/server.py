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
- Security hardening (path traversal protection, security headers, HTTPS)
"""

import io
import os
import socket
import ssl
import zipfile
from concurrent.futures import ThreadPoolExecutor
from email.utils import formatdate
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any, Callable, Optional, Tuple, TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

from .constants import (
    CHUNK_SIZE,
    CONTENT_TYPE_HTML,
    CONTENT_TYPE_MULTIPART,
    CONTENT_TYPE_ZIP,
    DNS_SERVERS,
    ENCODING,
    FALLBACK_IP,
    MAX_WORKERS,
)
from .ui import render_directory_listing
from .upload import UploadResult, extract_boundary, parse_multipart_streaming
from .utils import generate_etag, get_mime_type, is_path_safe, parse_range_header

if TYPE_CHECKING:
    from .security import SecurityManager


# Thread Pool Server


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


# HTTP Request Handler


class VortexHandler(SimpleHTTPRequestHandler):
    """
    HTTP request handler for serving files and accepting uploads.

    Features:
        - HTTP Range requests for media seeking and download resumption
        - Chunked file streaming for memory-efficient large transfers
        - Comprehensive MIME type detection
        - Proper caching headers (ETag, Last-Modified, Cache-Control)
        - Security headers (X-Content-Type-Options, X-Frame-Options, CSP)
        - Path traversal protection
        - Rate limiting and optional authentication
        - Robust error handling for network and filesystem errors

    Attributes:
        base_directory: Root directory being served (absolute path).
        protocol_version: HTTP/1.1 for persistent connections.
        security_manager: Optional security manager for auth/rate limiting.
        is_https: Whether connection is using HTTPS.
    """

    base_directory: str
    protocol_version = "HTTP/1.1"
    security_manager: Optional["SecurityManager"] = None
    is_https: bool = False

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

    # Security Helpers

    def _send_security_headers(self) -> None:
        """Send security headers to prevent common attacks."""
        if self.security_manager:
            # Use comprehensive security headers from security manager
            for header, value in self.security_manager.get_security_headers(
                self.is_https
            ).items():
                self.send_header(header, value)
        else:
            # Fallback: basic security headers
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")

    def _validate_security(self) -> bool:
        """
        Validate request against security manager.

        Returns:
            True if request is allowed, False if blocked (error sent).
        """
        if not self.security_manager:
            return True

        # Get token from query string or header
        parsed = urlparse(self.path)
        query_params = parse_qs(parsed.query)
        token = None

        # Check query string first
        if "token" in query_params:
            token = query_params["token"][0]
        # Then check Authorization header
        elif auth_header := self.headers.get("Authorization"):
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]

        # Validate request
        client_ip = self.client_address[0]
        allowed, message, status_code = self.security_manager.validate_request(
            client_ip, token
        )

        if not allowed:
            self._send_error_safe(status_code, message)
            return False

        return True

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

    # Response Helpers

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

    # ZIP Download Handler

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

    # File Streaming

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

    # HTTP Method Handlers

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
        # Security validation (rate limiting and token auth)
        if not self._validate_security():
            return

        # Parse URL for query parameters
        parsed = urlparse(self.path)
        query_params = parse_qs(parsed.query)
        path = self.translate_path(parsed.path)

        # Security: Validate path is within base directory
        if not self._is_request_path_safe(path):
            self._send_error_safe(403, "Access denied")
            return

        # Directory Handling
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

        # File Not Found
        if not os.path.isfile(path):
            self._send_error_safe(404, "File not found")
            return

        # File Handling
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

        # Range Request Handling
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

        # Send Headers
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
        # Security validation (rate limiting and token auth)
        if not self._validate_security():
            return

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


# Network Utilities


def get_local_ip(mode: str = "auto") -> Tuple[str, str]:
    """
    Detect the appropriate server address based on mode.

    Args:
        mode: Address detection mode.
            - 'auto': Intelligent detection (try LAN, fallback to localhost)
            - 'localhost': Force localhost only (127.0.0.1)
            - 'lan': Force LAN detection (fail if no LAN found)

    Returns:
        Tuple of (bind_address, display_address).
        bind_address is always '0.0.0.0' for accepting connections.
        display_address is the user-facing IP for sharing.
    """
    bind_address = "0.0.0.0"

    if mode == "localhost":
        return bind_address, "localhost"

    # Try UDP socket trick with multiple DNS servers
    for dns_server in DNS_SERVERS:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)
            sock.connect(dns_server)
            ip = sock.getsockname()[0]
            sock.close()
            # Skip IPv6 addresses (contain ':')
            if ":" not in ip and not ip.startswith("127."):
                return bind_address, ip
        except OSError:
            continue

    # Fallback: try gethostname + gethostbyname
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if ":" not in ip and not ip.startswith("127."):
            return bind_address, ip
    except OSError:
        pass

    # Final fallback
    if mode == "lan":
        # LAN mode requires a LAN IP - fail if not found
        raise RuntimeError("No LAN IP address found. Check your network connection.")

    return bind_address, FALLBACK_IP


# Server Entry Point


def run_server(
    directory: str,
    port: int,
    max_parallel: int = 4,
    address_mode: str = "auto",
    use_https: bool = False,
    use_token_auth: bool = False,
    regenerate_token: bool = False,
) -> None:
    """
    Start the Vortex HTTP server.

    Args:
        directory: Path to the directory to serve.
        port: Port number to listen on.
        max_parallel: Max parallel uploads hint for browser (unused server-side).
        address_mode: Address detection mode ('auto', 'localhost', 'lan').
        use_https: Enable HTTPS with self-signed certificate.
        use_token_auth: Require token authentication for all requests.
        regenerate_token: Generate a new authentication token.

    The server uses a thread pool to handle multiple concurrent connections
    efficiently, with limits to prevent resource exhaustion.
    """
    resolved_directory = str(Path(directory).resolve())

    # Initialize security manager if any security features are enabled
    security_manager = None
    if use_https or use_token_auth:
        from .security import SecurityManager

        security_manager = SecurityManager(
            enable_auth=use_token_auth,
        )

        # Regenerate token if requested
        if regenerate_token:
            security_manager.regenerate_token()

        # Configure handler class with security settings
        VortexHandler.security_manager = security_manager
        VortexHandler.is_https = use_https

    def handler_factory(*args: Any, **kwargs: Any) -> VortexHandler:
        return VortexHandler(*args, directory=resolved_directory, **kwargs)

    bind_address, display_address = get_local_ip(address_mode)
    server_address = (bind_address, port)
    httpd = PooledHTTPServer(server_address, handler_factory, max_workers=MAX_WORKERS)

    # Wrap socket with SSL if HTTPS is enabled
    if use_https and security_manager:
        ssl_context = security_manager.get_ssl_context()
        if ssl_context:
            httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)
            protocol = "https"
        else:
            print("Warning: Failed to create SSL context, falling back to HTTP")
            protocol = "http"
    else:
        protocol = "http"

    print("Vortex active")
    print(f"Serving directory: {resolved_directory}")
    print(f"Share this on your network: {protocol}://{display_address}:{port}/")
    print(f"Max concurrent connections: {MAX_WORKERS}")

    # Display security information
    if security_manager:
        if use_token_auth:
            token = security_manager.get_token()
            print(f"\n🔐 Token authentication ENABLED")
            print(f"   Access URL: {protocol}://{display_address}:{port}/?token={token}")
            print(f"   Token: {token}")
        if use_https:
            print(f"\n🔒 HTTPS ENABLED (self-signed certificate)")
            print("   Browsers may show a security warning - this is expected.")

    print("\nPress Ctrl+C to stop.")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print("\nVortex deactivated.")
        # Clear class-level security settings
        VortexHandler.security_manager = None
        VortexHandler.is_https = False
        httpd.shutdown()
        httpd.server_close()
