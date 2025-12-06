# MIT License
# Copyright (c) 2024 Vortex Contributors
# See LICENSE file for full license text.

"""
CSS styles for Vortex web interface.

This module contains the complete stylesheet for the file browser UI.
The design follows a clean, minimal aesthetic with clear visual hierarchy
and responsive behavior for mobile devices.
"""

CSS_STYLESHEET = """
/* Design System & CSS Variables */

:root {
  /* Color Palette */
  --bg-color: #d8d8d8;
  --surface-color: #ffffff;
  --surface-alt: #fafafa;
  --text-main: #111111;
  --text-dim: #555555;

  /* Accent Colors */
  --accent-color: #ff3b00;
  --accent-hover: #e03200;
  --error-color: #cc0000;

  /* Borders */
  --border-color: #000000;
  --border-light: #dddddd;
  --border-width: 2px;

  /* Spacing & Sizing */
  --radius: 4px;

  /* Typography */
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    Helvetica, Arial, sans-serif;
  --font-mono: "Menlo", "Consolas", "Monaco", "Liberation Mono",
    "Courier New", monospace;
}


/* Reset & Base Styles */

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html,
body {
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


/* Layout Container (Device Shell) */

.device-shell {
  background: var(--surface-color);
  border: var(--border-width) solid var(--border-color);
  width: 100%;
  display: grid;
  grid-template-rows: auto auto 1fr auto;
  box-shadow: 10px 10px 0px rgba(0, 0, 0, 0.18);
  min-height: 0;
}

/* Desktop Layout */
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

/* Mobile Layout */
@media (max-width: 600px) {
  body {
    background-size: 16px 16px;
  }

  .app-root {
    padding: max(0.5rem, env(safe-area-inset-top)) max(0.5rem, env(safe-area-inset-right)) max(0.5rem, env(safe-area-inset-bottom)) max(0.5rem, env(safe-area-inset-left));
  }

  .device-shell {
    border-width: 1px;
    box-shadow: none;
  }
}


/* Header */

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
  font-family: var(--font-sans);
}

.device-header p {
  font-size: 0.8rem;
  color: var(--text-dim);
  line-height: 1.4;
  font-family: var(--font-mono);
}


/* Subheader / Path Bar */

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


/* Main Content Area */

.device-main {
  padding: 0.8rem 1rem 0.8rem;
  display: grid;
  grid-template-columns: 1.9fr 1.1fr;
  column-gap: 1rem;
  row-gap: 0.75rem;
  min-height: 0;
}

/* Tablet/Mobile: Stack columns */
@media (max-width: 900px) {
  .device-main {
    grid-template-columns: 1fr;
    grid-auto-rows: auto;
  }

  /* Upload panel appears first on mobile */
  .panel-upload {
    order: -1;
  }
}


/* Panel Component */

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


/* File Input & Upload Controls */

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

/* Custom File Input */

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
  font-size: 16px; /* Prevents iOS zoom on focus */
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

/* Download All Button */

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

/* Mobile Button Adjustments */

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


/* File List Table */

.file-list {
  border-top: 1px solid var(--border-color);
  margin-top: 0.4rem;
  padding-top: 0.4rem;
  overflow: auto;
  min-height: 0;
  max-height: 100%;
  -webkit-overflow-scrolling: touch;
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.file-list::-webkit-scrollbar {
  display: none;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.75rem;
  font-family: var(--font-mono);
  table-layout: fixed;
}

th,
td {
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


/* Links */

a {
  color: var(--accent-color);
  text-decoration: none;
  font-family: var(--font-mono);
  -webkit-tap-highlight-color: transparent;
}

a:hover {
  color: var(--accent-hover);
  text-decoration: underline;
}

a:active {
  color: var(--accent-hover);
  opacity: 0.8;
}

/* Mobile Table Adjustments */

@media (max-width: 600px) {
  table {
    font-size: 0.7rem;
  }

  th,
  td {
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


/* Footer / Status Bar */

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


/* Upload Progress Indicator */

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


/* Error Messages */

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
