"""UI rendering module for Vortex file gateway.

This module provides HTML template rendering for the directory listing
and file upload interface.
"""

import html
import os
from pathlib import Path
from typing import List
from urllib.parse import unquote

# Size formatting constants
_SIZE_UNITS = ("B", "KB", "MB", "GB", "TB", "PB")
_SIZE_THRESHOLD = 1024.0


def _format_size(size_bytes: int) -> str:
    """Format a file size in bytes to a human-readable string.

    Args:
        size_bytes: File size in bytes.

    Returns:
        Human-readable size string (e.g., "1.5 MB").
    """
    size = float(size_bytes)
    for unit in _SIZE_UNITS[:-1]:
        if size < _SIZE_THRESHOLD:
            return f"{size:3.1f} {unit}"
        size /= _SIZE_THRESHOLD
    return f"{size:.1f} {_SIZE_UNITS[-1]}"


# CSS Stylesheet - extracted for maintainability
_CSS_STYLESHEET = """
/* --- DESIGN SYSTEM & VARIABLES --- */

:root {
  --bg-color: #d8d8d8;
  --surface-color: #ffffff;
  --surface-alt: #fafafa;
  --text-main: #111111;
  --text-dim: #555555;

  --accent-color: #ff3b00;
  --accent-hover: #e03200;
  --border-color: #000000;
  --border-light: #dddddd;
  --border-width: 2px;

  --error-color: #cc0000;

  --radius: 4px;

  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --font-mono: "SF Mono", "Monaco", "Inconsolata", "Fira Mono", "Droid Sans Mono", monospace;
}

/* --- RESET & BASE --- */

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body {
  height: 100%;
}

html {
  height: -webkit-fill-available;
}

body {
  background-color: var(--bg-color);
  background-image:
    linear-gradient(#cfcfcf 1px, transparent 1px),
    linear-gradient(90deg, #cfcfcf 1px, transparent 1px);
  background-size: 20px 20px;
  color: var(--text-main);
  font-family: var(--font-sans);
  min-height: 100vh;
  min-height: -webkit-fill-available;
  display: flex;
  justify-content: center;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  overscroll-behavior-y: none;
}

.app-root {
  width: 100%;
  max-width: 1200px;
  padding: 0.75rem;
}

/* --- LAYOUT CONTAINER --- */

.device-shell {
  background: var(--surface-color);
  border: var(--border-width) solid var(--border-color);
  width: 100%;
  display: grid;
  grid-template-rows: auto auto 1fr auto;
  box-shadow: 10px 10px 0px rgba(0, 0, 0, 0.18);
  min-height: 0;
}

@media (min-width: 900px) {
  body {
    align-items: center;
  }
  .app-root {
    padding: 1.5rem;
  }
  .device-shell {
    max-height: calc(100vh - 3rem);
  }
}

@media (max-width: 600px) {
  body {
    background-size: 16px 16px;
  }
  .app-root {
    padding: 0;
  }
  .device-shell {
    border-width: 1px;
    box-shadow: none;
  }
}

/* --- HEADER --- */

.device-header {
  padding: 0.9rem 1rem 0.4rem;
  border-bottom: var(--border-width) solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.device-header h1 {
  font-size: 0.95rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-weight: 800;
}

.device-header p {
  font-size: 0.8rem;
  color: var(--text-dim);
  line-height: 1.4;
  font-family: var(--font-mono);
}

/* --- SUBHEADER / PATH BAR --- */

.device-subheader {
  padding: 0.4rem 1rem;
  border-bottom: 1px solid var(--border-color);
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--text-dim);
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
}

.device-subheader span {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* --- MAIN CONTENT: UPLOAD + FILES --- */

.device-main {
  padding: 0.8rem 1rem 0.8rem;
  display: grid;
  grid-template-columns: 1.9fr 1.1fr;
  column-gap: 1rem;
  row-gap: 0.75rem;
  min-height: 0;
}

@media (max-width: 900px) {
  .device-main {
    grid-template-columns: 1fr;
    grid-auto-rows: auto;
  }
  
  /* On mobile: Upload panel comes FIRST */
  .panel-upload {
    order: -1;
  }
}

.panel {
  border: var(--border-width) solid var(--border-color);
  border-radius: var(--radius);
  background: #ffffff;
  padding: 0.75rem 0.9rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 0;
  overflow: hidden;
}

.panel-title {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-weight: 800;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-title span {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--text-dim);
}

.path-label {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--text-dim);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Upload control surface */

.upload-row {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

@media (min-width: 640px) {
  .upload-row {
    flex-direction: row;
    align-items: center;
  }
}

/* Custom file input */

.file-input {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  width: 100%;
}

.file-input input[type="file"] {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
  -webkit-appearance: none;
  font-size: 16px; /* Prevent iOS zoom */
}

.file-button {
  background: var(--accent-color);
  color: #ffffff;
  border: var(--border-width) solid var(--border-color);
  padding: 0.4rem 0.9rem;
  text-transform: uppercase;
  font-weight: 700;
  letter-spacing: 0.5px;
  min-width: 7rem;
  text-align: center;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.file-name {
  flex: 1;
  padding: 0.3rem 0.5rem;
  border: 1px dashed #bbbbbb;
  color: var(--text-dim);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  background: #fafafa;
  min-height: 44px;
  display: flex;
  align-items: center;
}

/* Buttons */

.btn {
  appearance: none;
  -webkit-appearance: none;
  background: #ffffff;
  border: var(--border-width) solid var(--border-color);
  color: var(--text-main);
  padding: 0.4rem 0.9rem;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  text-transform: uppercase;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.08s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 6rem;
  min-height: 44px;
  -webkit-user-select: none;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

.btn:hover {
  background: var(--accent-color);
  color: #ffffff;
  transform: translateY(-1px);
  box-shadow: 2px 2px 0 var(--text-main);
}

.btn:active {
  transform: translateY(0);
  box-shadow: none;
  background: var(--accent-hover);
  color: #ffffff;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* Download All button */
.btn-download {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  text-align: center;
  font-size: 0.7rem;
  padding: 0.35rem 0.6rem;
  min-height: 36px;
}

/* Mobile adjustments */
@media (max-width: 600px) {
  .upload-row {
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .file-input {
    flex-direction: column;
  }
  
  .file-button,
  .file-name,
  .btn {
    width: 100%;
  }
}

/* File list */

.file-list {
  border-top: 1px solid var(--border-color);
  margin-top: 0.4rem;
  padding-top: 0.4rem;
  overflow: auto;
  min-height: 0;
  max-height: 100%;
  -webkit-overflow-scrolling: touch;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.75rem;
  font-family: var(--font-mono);
  table-layout: fixed;
}

th, td {
  padding: 0.25rem 0.3rem;
  border-bottom: 1px solid var(--border-light);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

th {
  text-align: left;
  text-transform: uppercase;
  font-size: 0.6rem;
  letter-spacing: 0.5px;
  color: var(--text-dim);
  font-weight: 600;
}

td a {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
}

a {
  color: var(--accent-color);
  text-decoration: none;
  font-family: var(--font-mono);
  /* Remove iOS tap highlight */
  -webkit-tap-highlight-color: transparent;
}

a:hover {
  color: var(--accent-hover);
  text-decoration: underline;
}

/* Active state for touch */
a:active {
  color: var(--accent-hover);
  opacity: 0.8;
}

/* Mobile table adjustments */
@media (max-width: 600px) {
  table {
    font-size: 0.7rem;
  }
  
  th, td {
    padding: 0.4rem 0.25rem;
  }
  
  th {
    font-size: 0.55rem;
  }
  
  /* Larger touch targets on mobile */
  td a {
    padding: 0.35rem 0;
    min-height: 38px;
    display: flex;
    align-items: center;
  }
}

/* --- FOOTER / STATUS BAR --- */

.device-footer {
  padding: 0.5rem 1.25rem;
  border-top: var(--border-width) solid var(--border-color);
  background: var(--surface-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: var(--font-mono);
  font-size: 0.65rem;
}

.device-footer span.label {
  text-transform: uppercase;
  letter-spacing: 1px;
  font-weight: 700;
  color: var(--text-main);
}

.device-footer span.value {
  color: var(--text-dim);
}

/* --- UPLOAD PROGRESS --- */

.upload-progress {
  display: none;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 0.6rem;
}

.upload-progress.active {
  display: flex;
}

.progress-bar-container {
  width: 100%;
  height: 10px;
  background: var(--surface-alt);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  width: 0%;
  background: var(--accent-color);
  border-radius: var(--radius);
  transition: width 0.15s ease;
}

.progress-text {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--text-secondary);
}

.upload-error {
  color: var(--error-color);
  font-family: var(--font-mono);
  font-size: 0.7rem;
  display: none;
  padding: 0.4rem 0.6rem;
  background: #fef2f2;
  border-radius: var(--radius);
  border: 1px solid var(--error-color);
}

.upload-error.active {
  display: block;
}
"""

# JavaScript for file input and parallel multi-file upload
_JS_FILE_INPUT = """
document.addEventListener('DOMContentLoaded', function() {
  var MAX_PARALLEL = 4;
  
  // Update file name display on selection
  var fileInputs = document.querySelectorAll('.file-input input[type="file"]');
  fileInputs.forEach(function(input) {
    input.addEventListener('change', function() {
      var label = input.closest('.file-input');
      if (!label) return;
      var nameSpan = label.querySelector('.file-name');
      if (!nameSpan) return;
      if (input.files && input.files.length > 0) {
        if (input.files.length === 1) {
          nameSpan.textContent = input.files[0].name;
        } else {
          nameSpan.textContent = input.files.length + ' files selected';
        }
      } else {
        nameSpan.textContent = 'No file selected';
      }
    });
  });
  
  // Parallel multi-file upload with aggregate progress
  var uploadForm = document.querySelector('form[enctype="multipart/form-data"]');
  if (uploadForm) {
    uploadForm.addEventListener('submit', function(e) {
      e.preventDefault();
      
      var fileInput = uploadForm.querySelector('input[type="file"]');
      if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
        return;
      }
      
      var files = Array.from(fileInput.files);
      var totalFiles = files.length;
      var totalBytes = files.reduce(function(sum, f) { return sum + f.size; }, 0);
      var uploadedBytes = 0;
      var completedFiles = 0;
      var failedFiles = [];
      var activeUploads = 0;
      var fileIndex = 0;
      
      var progressContainer = document.querySelector('.upload-progress');
      var progressBar = document.querySelector('.progress-bar');
      var progressText = document.querySelector('.progress-text');
      var uploadError = document.querySelector('.upload-error');
      var submitBtn = uploadForm.querySelector('button[type="submit"]');
      
      if (progressContainer) progressContainer.classList.add('active');
      if (uploadError) {
        uploadError.classList.remove('active');
        uploadError.textContent = '';
      }
      if (submitBtn) submitBtn.disabled = true;
      
      // Track bytes per file for progress calculation
      var fileProgress = {};
      
      function updateProgress() {
        var currentUploaded = uploadedBytes;
        for (var key in fileProgress) {
          currentUploaded += fileProgress[key];
        }
        var percent = totalBytes > 0 ? Math.round((currentUploaded / totalBytes) * 100) : 0;
        if (progressBar) progressBar.style.width = percent + '%';
        if (progressText) {
          progressText.textContent = formatSize(currentUploaded) + ' / ' + formatSize(totalBytes) + 
            ' (' + percent + '%) - ' + completedFiles + '/' + totalFiles + ' files';
        }
      }
      
      function uploadNext() {
        while (activeUploads < MAX_PARALLEL && fileIndex < files.length) {
          uploadFile(files[fileIndex], fileIndex);
          fileIndex++;
        }
      }
      
      function uploadFile(file, idx) {
        activeUploads++;
        fileProgress[idx] = 0;
        
        var formData = new FormData();
        formData.append('file', file);
        
        var xhr = new XMLHttpRequest();
        
        xhr.upload.addEventListener('progress', function(e) {
          if (e.lengthComputable) {
            fileProgress[idx] = e.loaded;
            updateProgress();
          }
        });
        
        xhr.addEventListener('load', function() {
          activeUploads--;
          delete fileProgress[idx];
          
          if (xhr.status >= 200 && xhr.status < 400) {
            completedFiles++;
            uploadedBytes += file.size;
          } else {
            failedFiles.push(file.name);
          }
          
          updateProgress();
          
          if (fileIndex < files.length) {
            uploadNext();
          } else if (activeUploads === 0) {
            // All done
            if (failedFiles.length === 0) {
              window.location.reload();
            } else {
              if (uploadError) {
                uploadError.textContent = 'Failed: ' + failedFiles.join(', ');
                uploadError.classList.add('active');
              }
              if (completedFiles > 0) {
                setTimeout(function() { window.location.reload(); }, 2000);
              } else {
                if (progressContainer) progressContainer.classList.remove('active');
                if (submitBtn) submitBtn.disabled = false;
              }
            }
          }
        });
        
        xhr.addEventListener('error', function() {
          activeUploads--;
          delete fileProgress[idx];
          failedFiles.push(file.name);
          
          if (fileIndex < files.length) {
            uploadNext();
          } else if (activeUploads === 0) {
            if (uploadError) {
              uploadError.textContent = 'Failed: ' + failedFiles.join(', ');
              uploadError.classList.add('active');
            }
            if (completedFiles > 0) {
              setTimeout(function() { window.location.reload(); }, 2000);
            } else {
              if (progressContainer) progressContainer.classList.remove('active');
              if (submitBtn) submitBtn.disabled = false;
            }
          }
        });
        
        xhr.open('POST', window.location.pathname, true);
        xhr.send(formData);
      }
      
      // Start parallel uploads
      uploadNext();
    });
  }
  
  function formatSize(bytes) {
    var units = ['B', 'KB', 'MB', 'GB', 'TB'];
    var i = 0;
    while (bytes >= 1024 && i < units.length - 1) {
      bytes /= 1024;
      i++;
    }
    return bytes.toFixed(1) + ' ' + units[i];
  }
});
"""


def render_layout(title: str, body_html: str) -> str:
    """Render the main HTML layout with header, body content, and footer.

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
<style>{_CSS_STYLESHEET}</style>
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
<script>{_JS_FILE_INPUT}</script>
</body>
</html>
"""


def _build_file_table_rows(real_path: Path, base_directory: str) -> List[str]:
    """Build HTML table rows for directory entries.

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

    # Sort entries case-insensitively, handling errors gracefully
    try:
        entries = sorted(real_path.iterdir(), key=lambda p: p.name.lower())
    except (OSError, PermissionError):
        # Cannot read directory - return empty list
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
                    size = _format_size(entry.stat().st_size)
                except (OSError, PermissionError):
                    size = "?"  # Cannot stat file
            
            rows.append(
                f'<tr><td><a href="{escaped_name}">{escaped_name}</a></td>'
                f'<td>{size}</td></tr>'
            )
        except (OSError, PermissionError):
            # Skip entries we cannot access
            continue

    return rows


def render_directory_listing(base_directory: str, fs_path: str, request_path: str) -> str:
    """Build the upload panel and file table HTML for a directory.

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

    # Build file table and count files (not directories)
    rows = _build_file_table_rows(real_path, base_directory)
    
    # Count actual files for Download All button
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
    
    table_html = (
        "<table>"
        "<thead><tr><th>Name</th><th>Size</th></tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody></table>"
    )
    
    # Download All button (only show if there are files)
    download_btn = ""
    if file_count > 0:
        download_btn = f'<a class="btn btn-download" href="?download=zip">Download All ({file_count})</a>'

    # Subheader shows current path and base directory
    subheader = f"""
      <div class="device-subheader">
        <span>Serving: {html.escape(str(base_directory))}</span>
        <span>{display_path}</span>
      </div>
    """

    # Main content with upload and file panels
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
