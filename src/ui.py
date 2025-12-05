# MIT License
# Copyright (c) 2024 Vortex Contributors
# See LICENSE file for full license text.

"""
UI rendering module for Vortex file gateway.

This module provides HTML template rendering for the directory listing
and file upload interface. It generates a responsive, mobile-friendly
web UI for browsing and uploading files.
"""

import html
import os
from pathlib import Path
from typing import List
from urllib.parse import unquote

from .scripts import JS_UPLOAD_HANDLER
from .styles import CSS_STYLESHEET


# Size Formatting

# Units for human-readable file sizes
_SIZE_UNITS = ("B", "KB", "MB", "GB", "TB", "PB")
_SIZE_THRESHOLD = 1024.0


def format_size(size_bytes: int) -> str:
    """
    Format a file size in bytes to a human-readable string.

    Args:
        size_bytes: File size in bytes.

    Returns:
        Human-readable size string (e.g., "1.5 MB", "256 KB").
    """
    size = float(size_bytes)
    for unit in _SIZE_UNITS[:-1]:
        if size < _SIZE_THRESHOLD:
            return f"{size:3.1f} {unit}"
        size /= _SIZE_THRESHOLD
    return f"{size:.1f} {_SIZE_UNITS[-1]}"


# HTML Layout


def render_layout(title: str, body_html: str) -> str:
    """
    Render the main HTML layout with header, body content, and footer.

    This is the outer shell of the web interface, providing consistent
    styling and structure across all pages.

    Args:
        title: Page title for the browser tab.
        body_html: HTML content to insert into the main body area.

    Returns:
        Complete HTML document as a string.
    """
    escaped_title = html.escape(title)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover, user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="format-detection" content="telephone=no">
<meta name="theme-color" content="#e8e4e0">
<title>{escaped_title}</title>
<style>{CSS_STYLESHEET}</style>
</head>
<body>
  <div class="app-root">
    <div class="device-shell">
      <header class="device-header">
        <h1>Vortex</h1>
        <p>Local file gateway</p>
      </header>
      {body_html}
      <footer class="device-footer">
        <span class="label">Status</span>
        <span class="value">Listening...</span>
      </footer>
    </div>
  </div>
<script>{JS_UPLOAD_HANDLER}</script>
</body>
</html>
"""


# Directory Listing


def _build_file_table_rows(real_path: Path, base_directory: str) -> List[str]:
    """
    Build HTML table rows for directory entries.

    Creates a table row for each file and subdirectory, including
    a parent directory link ("..") when not at the root.

    Args:
        real_path: Path to the directory being listed.
        base_directory: Root directory being served.

    Returns:
        List of HTML table row strings.
    """
    rows: List[str] = []

    # Add parent directory link if not at root
    rel = os.path.relpath(real_path, base_directory)
    if rel != ".":
        rows.append('<tr><td><a href="../">[..]</a></td><td></td></tr>')

    # Sort entries case-insensitively
    try:
        entries = sorted(real_path.iterdir(), key=lambda p: p.name.lower())
    except (OSError, PermissionError):
        # Cannot read directory - return what we have
        return rows

    for entry in entries:
        try:
            is_dir = entry.is_dir()
            name = entry.name + ("/" if is_dir else "")
            escaped_name = html.escape(name)

            if is_dir:
                size = "-"
            else:
                try:
                    size = format_size(entry.stat().st_size)
                except (OSError, PermissionError):
                    size = "?"  # Cannot stat file

            rows.append(
                f'<tr><td><a href="{escaped_name}">{escaped_name}</a></td>'
                f"<td>{size}</td></tr>"
            )
        except (OSError, PermissionError):
            # Skip entries we cannot access
            continue

    return rows


def render_directory_listing(
    base_directory: str,
    fs_path: str,
    request_path: str,
) -> str:
    """
    Build the complete HTML page for a directory listing.

    Includes the upload panel and file table with all entries
    in the specified directory.

    Args:
        base_directory: Root directory being served.
        fs_path: Filesystem path to the current directory.
        request_path: URL path from the HTTP request.

    Returns:
        Complete HTML page for the directory listing.
    """
    real_path = Path(fs_path)
    display_path = html.escape(unquote(request_path))
    base_name = html.escape(os.path.basename(base_directory) or "/")

    # Build file table rows
    rows = _build_file_table_rows(real_path, base_directory)

    # Count files (not directories) for Download All button
    file_count = 0
    try:
        for entry in real_path.iterdir():
            try:
                if entry.is_file():
                    file_count += 1
            except (OSError, PermissionError):
                continue
    except (OSError, PermissionError):
        pass

    # Build the file table HTML
    table_html = (
        "<table>"
        "<thead><tr><th>Name</th><th>Size</th></tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody></table>"
    )

    # Download All button (only shown if there are files)
    download_btn = ""
    if file_count > 0:
        download_btn = (
            f'<a class="btn btn-download" href="?download=zip">'
            f"Download All ({file_count})</a>"
        )

    # Subheader shows current path and base directory
    subheader = f"""
      <div class="device-subheader">
        <span>Serving: {html.escape(str(base_directory))}</span>
        <span>{display_path}</span>
      </div>
    """

    # Main content with upload panel and file list
    main_content = f"""
    <main class="device-main">
      <section class="panel panel-files">
        <div class="panel-title">
          <span>Files</span>
          <span>{display_path}</span>
        </div>
        {download_btn}
        <div class="file-list">
          {table_html}
        </div>
      </section>
      <section class="panel panel-upload">
        <div class="panel-title">
          <span>Upload</span>
          <span>{base_name}</span>
        </div>
        <p class="path-label">Select files to upload (no size limit)</p>
        <form method="post" enctype="multipart/form-data">
          <div class="upload-row">
            <label class="file-input">
              <input type="file" name="file" multiple required>
              <span class="file-button">Choose files</span>
              <span class="file-name">No files selected</span>
            </label>
            <button class="btn" type="submit">Send</button>
          </div>
          <div class="upload-progress">
            <div class="progress-bar-container">
              <div class="progress-bar"></div>
            </div>
            <span class="progress-text">Uploading...</span>
          </div>
          <div class="upload-error"></div>
        </form>
      </section>
    </main>
    """

    return render_layout("Vortex", subheader + main_content)
