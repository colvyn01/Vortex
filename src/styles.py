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
  /* Color Palette - Science-Backed (Low Visual Fatigue) */
  --bg-color: #E8F4F1;          /* Soft sage - desaturated, minimal eye strain */
  --surface-color: #FFFBF7;      /* Warm off-white - reduces glare vs pure white */
  --surface-alt: #F5F3F0;        /* Warm neutral for secondary surfaces */
  --text-main: #212121;          /* Dark grey - softer than pure black, 4.5:1+ contrast */
  --text-dim: #666666;           /* Mid-grey for secondary text */

  /* Accent Colors - Vibrant but Safe */
  --accent-color: #00796B;       /* Teal - lowest visual fatigue (NIH study) */
  --accent-hover: #004D40;       /* Deep teal for hover states */
  --secondary-accent: #D84315;   /* Burnt orange - use sparingly (10% UI) */
  --error-color: #C62828;        /* Deep red - reserved for errors only */

  /* Borders - Industrial Definition */
  --border-color: #3E3E3E;       /* Charcoal - maintains sharpness without harshness */
  --border-light: #D0D0D0;       /* Softer border for secondary elements */
  --border-width: 2px;

  /* Spacing & Sizing */
  --radius: 4px;

  /* Typography */
  /* Unified font stack for consistent Teenage Engineering-inspired industrial aesthetic.
     IBM Plex Mono provides a clean, technical feel; falls back to system monospace fonts. */
  --font-ui: "IBM Plex Mono", "SF Mono", "Menlo", "Consolas", "Monaco", monospace;
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
    linear-gradient(rgba(0, 0, 0, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 0, 0, 0.04) 1px, transparent 1px);
  background-size: 20px 20px;
  color: var(--text-main);
  font-family: var(--font-ui);
  min-height: 100vh;
  min-height: -webkit-fill-available;
  display: flex;
  justify-content: center;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  overscroll-behavior-y: none;
  overflow-x: hidden;
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
  font-family: var(--font-ui);
}

.device-header p {
  font-size: 0.8rem;
  color: var(--text-dim);
  line-height: 1.4;
  font-family: var(--font-ui);
}


/* Subheader / Path Bar */

.device-subheader {
  padding: 0.4rem 1rem;
  border-bottom: 1px solid var(--border-color);
  font-family: var(--font-ui);
  font-size: 0.7rem;
  color: var(--text-dim);
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  min-width: 0;
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
  grid-template-columns: 2fr 1fr 1fr;
  grid-template-areas: "files upload chat";
  column-gap: 1rem;
  row-gap: 0.75rem;
  min-height: 0;
}

.panel-files {
  grid-area: files;
  min-width: 0;
}

.panel-upload {
  grid-area: upload;
  min-width: 0;
}

.panel-chat {
  grid-area: chat;
  min-width: 0;
}

/* Medium screens: Adjust proportions */
@media (max-width: 1200px) and (min-width: 901px) {
  .device-main {
    grid-template-columns: 1.5fr 1fr 1fr;
  }
}

/* Tablet/Mobile: Stack columns */
@media (max-width: 900px) {
  .device-main {
    grid-template-columns: 1fr;
    grid-template-areas: "files" "upload" "chat";
    grid-auto-rows: auto;
  }

  /* Upload panel appears first on mobile */
  .panel-upload {
    order: -1;
    grid-area: upload;
  }
  
  .panel-files {
    order: 0;
    grid-area: files;
  }
  
  .panel-chat {
    order: 1;
    grid-area: chat;
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
  min-width: 0;
}

.panel-title span {
  font-family: var(--font-ui);
  font-size: 0.65rem;
  color: var(--text-dim);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.panel-title span:first-child {
  flex-shrink: 0;
  margin-right: 0.5rem;
}

.path-label {
  font-family: var(--font-ui);
  font-size: 0.7rem;
  color: var(--text-dim);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}


/* File Input & Upload Controls */

.upload-row {
  display: flex;
  flex-direction: row;
  align-items: stretch;
  gap: 0.25rem;
}

/* Custom File Input */

.file-input {
  position: relative;
  display: flex;
  align-items: stretch;
  gap: 0.25rem;
  font-family: var(--font-ui);
  font-size: 0.75rem;
  flex: 1;
  min-width: 0;
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
  padding: 0.4rem;
  text-transform: uppercase;
  font-weight: 600;
  font-size: 0.65rem;
  letter-spacing: 0.2px;
  min-width: 3.5rem;
  text-align: center;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-ui);
}

.file-name {
  flex: 1;
  padding: 0 0.3rem;
  border: 1px dashed #bbbbbb;
  color: var(--text-dim);
  white-space: nowrap;
  font-size: 0.65rem;
  overflow: hidden;
  text-overflow: ellipsis;
  background: #fafafa;
  min-height: 44px;
  display: block;
  line-height: 42px;
  min-width: 0;
}


/* Buttons */

.btn {
  appearance: none;
  -webkit-appearance: none;
  background: #ffffff;
  border: var(--border-width) solid var(--border-color);
  color: var(--text-main);
  padding: 0.4rem;
  font-family: var(--font-ui);
  font-size: 0.65rem;
  text-transform: uppercase;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.08s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 3.5rem;
  min-height: 44px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex-shrink: 0;
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
    flex: none;
    width: 100%;
  }

  .file-button,
  .file-name {
    width: 100%;
    padding: 0.45rem 0.6rem;
    letter-spacing: 0.1px;
  }

  .upload-row .btn {
    width: 100%;
    flex-shrink: 1;
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
  font-family: var(--font-ui);
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
  font-family: var(--font-ui);
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
  font-family: var(--font-ui);
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
  font-family: var(--font-ui);
  font-size: 0.7rem;
  color: var(--text-secondary);
}


/* Error Messages */

.upload-error {
  color: var(--error-color);
  font-family: var(--font-ui);
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


/* Chat Panel */

.panel-chat {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-height: 350px;
  max-height: 550px;
}

@media (max-width: 1200px) and (min-width: 901px) {
  .panel-chat {
    min-height: 300px;
    max-height: 450px;
  }
}

@media (max-width: 900px) {
  .panel-chat {
    min-height: 300px;
    max-height: 500px;
  }
}

#chat-status {
  font-size: 0.8rem;
  color: #00cc00;
  animation: pulse 2s infinite;
}

#chat-status.offline {
  color: #cc0000;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Chat Messages - Terminal Log Style */

.chat-messages {
  flex: 1;
  overflow-y: auto;
  border: var(--border-width) solid var(--border-color);
  padding: 0.6rem;
  background: var(--surface-color);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-family: var(--font-ui);
  -webkit-overflow-scrolling: touch;
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.chat-messages::-webkit-scrollbar {
  display: none;
}

/* Chat Message - System Log Entry Style */

.chat-message {
  padding: 0.5rem 0.6rem;
  border-left: 3px solid var(--border-light);
  background: var(--surface-alt);
  word-wrap: break-word;
  font-family: var(--font-ui);
}

.chat-message-own {
  background: #ffffff;
  border-left-color: var(--accent-color);
  border-left-width: 3px;
}

/* Chat Sender - Terminal Prompt Style */

.chat-sender {
  font-size: 0.65rem;
  font-weight: 800;
  color: var(--text-main);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.3rem;
  font-family: var(--font-ui);
}

.chat-message-own .chat-sender {
  color: var(--accent-color);
}

/* Kick Button - Host Controls */

.kick-button {
  display: inline-block;
  margin-left: 0.5rem;
  padding: 0 0.3rem;
  font-size: 1rem;
  font-weight: bold;
  font-family: var(--font-ui);
  color: #ff3b00;
  background: transparent;
  border: 1px solid #ff3b00;
  border-radius: 2px;
  cursor: pointer;
  line-height: 1;
  transition: all 0.15s ease;
}

.kick-button:hover {
  background: #ff3b00;
  color: #ffffff;
}

.kick-button:active {
  transform: scale(0.95);
}

/* Chat Disconnected State */

.chat-form input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.chat-form input:disabled::placeholder {
  color: #ff3b00;
}

/* Host Controls Container */

.host-controls {
  display: none;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.btn-manage-devices,
.btn-manage-bans {
  flex: 1;
  padding: 0.4rem;
  font-size: 0.65rem;
  font-weight: 600;
  font-family: var(--font-ui);
  color: var(--text-main);
  background: var(--surface-alt);
  border: var(--border-width) solid var(--border-color);
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  transition: all 0.15s ease;
}

.btn-manage-devices:hover {
  background: var(--accent-color);
  border-color: var(--accent-color);
  color: #ffffff;
}

.btn-manage-bans:hover {
  background: #ff3b00;
  border-color: #ff3b00;
  color: #ffffff;
}

/* Active Devices Section */

.active-devices-section {
  background: var(--surface-main);
  border: var(--border-width) solid var(--accent-color);
  margin-bottom: 0.5rem;
  max-height: 200px;
  overflow-y: auto;
}

.active-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.4rem 0.6rem;
  background: var(--accent-color);
  color: #ffffff;
  border-bottom: var(--border-width) solid var(--accent-color);
  font-size: 0.65rem;
  font-weight: 800;
  font-family: var(--font-ui);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.active-close {
  background: transparent;
  border: 1px solid #ffffff;
  color: #ffffff;
  font-size: 1rem;
  font-weight: bold;
  line-height: 1;
  padding: 0 0.3rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.active-close:hover {
  background: #ffffff;
  color: var(--accent-color);
}

.active-list {
  padding: 0.5rem;
}

.active-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.4rem 0.5rem;
  margin-bottom: 0.3rem;
  background: var(--surface-alt);
  border-left: 3px solid var(--accent-color);
  font-family: var(--font-ui);
}

.active-device-name {
  font-size: 0.75rem;
  color: var(--text-main);
  font-weight: 600;
  letter-spacing: 0.3px;
  text-transform: uppercase;
}

.active-empty {
  padding: 1rem;
  text-align: center;
  font-size: 0.7rem;
  color: var(--text-dim);
  font-family: var(--font-ui);
}

.kick-button-inline {
  padding: 0.2rem 0.5rem;
  font-size: 0.65rem;
  font-weight: 600;
  font-family: var(--font-ui);
  color: #ffffff;
  background: #ff3b00;
  border: 1px solid #ff3b00;
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  transition: all 0.15s ease;
}

.kick-button-inline:hover {
  background: #cc2f00;
  border-color: #cc2f00;
}

.kick-button-inline:active {
  transform: scale(0.95);
}

/* Banned Devices Section */

.banned-devices-section {
  background: var(--surface-main);
  border: var(--border-width) solid var(--border-color);
  margin-bottom: 0.5rem;
  max-height: 200px;
  overflow-y: auto;
}

.banned-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.4rem 0.6rem;
  background: var(--surface-alt);
  border-bottom: var(--border-width) solid var(--border-color);
  font-size: 0.65rem;
  font-weight: 800;
  font-family: var(--font-ui);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.banned-close {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-dim);
  font-size: 1rem;
  font-weight: bold;
  line-height: 1;
  padding: 0 0.3rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.banned-close:hover {
  background: var(--error-color);
  border-color: var(--error-color);
  color: #ffffff;
}

.banned-list {
  padding: 0.5rem;
}

.banned-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.4rem 0.5rem;
  margin-bottom: 0.3rem;
  background: var(--surface-alt);
  border-left: 3px solid var(--error-color);
  font-family: var(--font-ui);
}

.banned-device-id {
  font-size: 0.7rem;
  color: var(--text-main);
  font-family: var(--font-mono);
  letter-spacing: 0.3px;
}

.banned-empty {
  padding: 1rem;
  text-align: center;
  font-size: 0.7rem;
  color: var(--text-dim);
  font-family: var(--font-ui);
}

.unkick-button {
  padding: 0.2rem 0.5rem;
  font-size: 0.65rem;
  font-weight: 600;
  font-family: var(--font-ui);
  color: var(--text-main);
  background: transparent;
  border: 1px solid var(--border-color);
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  transition: all 0.15s ease;
}

.unkick-button:hover {
  background: var(--accent-color);
  border-color: var(--accent-color);
  color: #ffffff;
}

.unkick-button:active {
  transform: scale(0.95);
}

/* Chat Content - Monospace Data */

.chat-content {
  font-family: var(--font-ui);
  font-size: 0.7rem;
  word-wrap: break-word;
  line-height: 1.5;
  color: var(--text-main);
}

.chat-content a {
  color: var(--accent-color);
  text-decoration: none;
  font-family: var(--font-ui);
  border-bottom: 1px solid var(--accent-color);
}

.chat-content a:hover {
  text-decoration: none;
  opacity: 0.8;
}

/* Chat Timestamp - Technical Readout */

.chat-timestamp {
  font-size: 0.65rem;
  font-family: var(--font-ui);
  color: var(--text-dim);
  margin-top: 0.3rem;
  text-align: left;
  letter-spacing: 0.3px;
}

/* Chat Form - Command Line Style */

.chat-form {
  display: flex;
  gap: 0.5rem;
  align-items: stretch;
}

/* Chat Input - Terminal Input Field */

#chat-input {
  flex: 1;
  padding: 0.5rem 0.6rem;
  border: var(--border-width) solid var(--border-color);
  font-family: var(--font-ui);
  font-size: 0.7rem;
  border-radius: 0;
  background: var(--surface-color);
  color: var(--text-main);
  min-height: 44px;
  letter-spacing: 0.2px;
}

#chat-input::placeholder {
  font-family: var(--font-ui);
  color: var(--text-dim);
  opacity: 1;
}

#chat-input:focus {
  outline: none;
  border-color: var(--accent-color);
  background: #ffffff;
}

.btn-chat {
  min-width: 4rem;
  font-size: 0.65rem;
  font-family: var(--font-ui);
}

@media (max-width: 600px) {
  .chat-form {
    flex-direction: column;
    gap: 0.5rem;
  }
  
  #chat-input {
    font-size: 16px; /* Prevent iOS zoom */
  }
  
  .chat-message {
    max-width: 100%;
  }
}


/* QR Code Container */

.qr-code-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 1rem;
  border-top: 1px solid var(--border-light);
  margin: 1rem auto 0;
  width: 100%;
}

.qr-title {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-dim);
  font-family: var(--font-ui);
  text-align: center;
}

#qr-code {
  border: 1px solid var(--border-light);
  padding: 0.3rem;
  background: #ffffff;
  border-radius: var(--radius);
  width: max-content;
}

#qr-code img {
  display: block;
  max-width: 100%;
  height: auto;
}

.qr-url {
  font-family: var(--font-ui);
  font-size: 0.6rem;
  color: var(--text-dim);
  word-break: break-all;
  text-align: center;
  max-width: 100%;
  line-height: 1.3;
}

@media (max-width: 900px) {
  .qr-code-container {
    display: none;
  }
}


/* Directory Size Info */

#dir-size-info {
  font-family: var(--font-ui);
  font-size: 0.7rem;
  color: var(--text-dim);
  white-space: nowrap;
}
"""
