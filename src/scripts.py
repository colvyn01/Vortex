# MIT License
# Copyright (c) 2024 Vortex Contributors
# See LICENSE file for full license text.

"""
JavaScript for Vortex web interface.

This module contains the client-side JavaScript that handles file selection
display and parallel multi-file uploads with progress tracking.
"""

JS_UPLOAD_HANDLER = """
document.addEventListener('DOMContentLoaded', function() {
  // Configuration

  // Maximum number of simultaneous upload connections.
  // Higher values can improve throughput but may overwhelm slower networks.
  var MAX_PARALLEL = 4;


  // File Input Display
  // Update the filename display when user selects files.

  var fileInputs = document.querySelectorAll('.file-input input[type="file"]');

  fileInputs.forEach(function(input) {
    input.addEventListener('change', function() {
      var label = input.closest('.file-input');
      if (!label) return;

      var nameSpan = label.querySelector('.file-name');
      if (!nameSpan) return;

      if (input.files && input.files.length > 0) {
        if (input.files.length > 10) {
          // Large selection: show processing indicator, yield to UI thread
          nameSpan.textContent = 'Processing ' + input.files.length + ' files...';
          setTimeout(function() {
            nameSpan.textContent = input.files.length + ' files selected';
          }, 50);
        } else if (input.files.length === 1) {
          nameSpan.textContent = input.files[0].name;
        } else {
          nameSpan.textContent = input.files.length + ' files selected';
        }
      } else {
        nameSpan.textContent = 'No file selected';
      }
    });
  });


  // Parallel Multi-File Upload
  // Handles uploading multiple files simultaneously with aggregate progress.

  var uploadForm = document.querySelector('form[enctype="multipart/form-data"]');

  if (uploadForm) {
    uploadForm.addEventListener('submit', function(e) {
      e.preventDefault();

      var fileInput = uploadForm.querySelector('input[type="file"]');
      if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
        return;
      }

      // --- Initialize Upload State ---

      var files = Array.from(fileInput.files);
      var totalFiles = files.length;
      var totalBytes = files.reduce(function(sum, f) { return sum + f.size; }, 0);
      var uploadedBytes = 0;
      var completedFiles = 0;
      var failedFiles = [];
      var activeUploads = 0;
      var fileIndex = 0;

      // --- Get UI Elements ---

      var progressContainer = document.querySelector('.upload-progress');
      var progressBar = document.querySelector('.progress-bar');
      var progressText = document.querySelector('.progress-text');
      var uploadError = document.querySelector('.upload-error');
      var submitBtn = uploadForm.querySelector('button[type="submit"]');

      // Show progress UI, hide errors, disable submit
      if (progressContainer) progressContainer.classList.add('active');
      if (uploadError) {
        uploadError.classList.remove('active');
        uploadError.textContent = '';
      }
      if (submitBtn) submitBtn.disabled = true;

      // Track bytes uploaded per file for accurate progress calculation
      var fileProgress = {};

      // --- Progress Update Function ---

      function updateProgress() {
        var currentUploaded = uploadedBytes;
        for (var key in fileProgress) {
          currentUploaded += fileProgress[key];
        }
        var percent = totalBytes > 0
          ? Math.round((currentUploaded / totalBytes) * 100)
          : 0;

        if (progressBar) {
          progressBar.style.width = percent + '%';
        }
        if (progressText) {
          progressText.textContent =
            formatSize(currentUploaded) + ' / ' + formatSize(totalBytes) +
            ' (' + percent + '%) - ' + completedFiles + '/' + totalFiles + ' files';
        }
      }

      // --- Upload Queue Manager ---
      // Starts uploads up to MAX_PARALLEL at a time.

      function uploadNext() {
        while (activeUploads < MAX_PARALLEL && fileIndex < files.length) {
          uploadFile(files[fileIndex], fileIndex);
          fileIndex++;
        }
      }

      // --- Single File Upload Function ---

      function uploadFile(file, idx) {
        activeUploads++;
        fileProgress[idx] = 0;

        var formData = new FormData();
        formData.append('file', file);

        var xhr = new XMLHttpRequest();

        // Track upload progress for this file
        xhr.upload.addEventListener('progress', function(e) {
          if (e.lengthComputable) {
            fileProgress[idx] = e.loaded;
            updateProgress();
          }
        });

        // Handle upload completion
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

          // Start next upload or handle completion
          if (fileIndex < files.length) {
            uploadNext();
          } else if (activeUploads === 0) {
            handleAllComplete();
          }
        });

        // Handle network errors
        xhr.addEventListener('error', function() {
          activeUploads--;
          delete fileProgress[idx];
          failedFiles.push(file.name);

          if (fileIndex < files.length) {
            uploadNext();
          } else if (activeUploads === 0) {
            handleAllComplete();
          }
        });

        xhr.open('POST', window.location.pathname, true);
        xhr.send(formData);
      }

      // --- Completion Handler ---

      function handleAllComplete() {
        if (failedFiles.length === 0) {
          // All uploads succeeded - refresh page to show new files
          window.location.reload();
        } else {
          // Some uploads failed - show error
          if (uploadError) {
            uploadError.textContent = 'Failed: ' + failedFiles.join(', ');
            uploadError.classList.add('active');
          }

          if (completedFiles > 0) {
            // Some succeeded - refresh after brief delay
            setTimeout(function() { window.location.reload(); }, 2000);
          } else {
            // All failed - reset UI for retry
            if (progressContainer) progressContainer.classList.remove('active');
            if (submitBtn) submitBtn.disabled = false;
          }
        }
      }

      // --- Start Upload ---
      uploadNext();
    });
  }


  // Utility Functions

  /**
   * Format bytes as human-readable string (e.g., "1.5 MB").
   */
  function formatSize(bytes) {
    var units = ['B', 'KB', 'MB', 'GB', 'TB'];
    var i = 0;
    while (bytes >= 1024 && i < units.length - 1) {
      bytes /= 1024;
      i++;
    }
    return bytes.toFixed(1) + ' ' + units[i];
  }


  // Chat and Real-Time Features
  // Cross-device chat with polling, QR code generation, and directory size display

  var sessionData = document.getElementById('session-data');
  if (!sessionData) return;

  var sessionId = sessionData.getAttribute('data-session-id');
  var baseDir = sessionData.getAttribute('data-base-dir');

  if (!sessionId) return;

  // Chat State
  var lastMessageId = null;
  var pollInterval = null;
  var POLL_INTERVAL_MS = 1000;
  var SENDER_NAME = 'User-' + Math.random().toString(36).substr(2, 6);

  // UI Elements
  var chatMessages = document.getElementById('chat-messages');
  var chatForm = document.getElementById('chat-form');
  var chatInput = document.getElementById('chat-input');
  var chatStatus = document.getElementById('chat-status');
  var dirSizeInfo = document.getElementById('dir-size-info');
  var qrContainer = document.getElementById('qr-container');
  var qrCode = document.getElementById('qr-code');
  var qrUrlText = document.getElementById('qr-url-text');

  // Initialize Features
  initializeChat();
  initializeQRCode();
  fetchDirectorySize();

  /**
   * Initialize chat polling and message sending.
   */
  function initializeChat() {
    if (!chatMessages || !chatForm || !chatInput) return;

    // Start polling for new messages
    fetchNewMessages();
    pollInterval = setInterval(fetchNewMessages, POLL_INTERVAL_MS);

    // Handle message sending
    chatForm.addEventListener('submit', function(e) {
      e.preventDefault();

      var content = chatInput.value.trim();
      if (!content) return;

      var submitBtn = chatForm.querySelector('button[type=\"submit\"]');
      if (submitBtn) submitBtn.disabled = true;

      // Send message to server
      fetch('/api/messages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          session_id: sessionId,
          sender: SENDER_NAME,
          content: content
        })
      })
      .then(function(response) {
        if (!response.ok) throw new Error('Send failed');
        return response.json();
      })
      .then(function(data) {
        chatInput.value = '';
        if (submitBtn) submitBtn.disabled = false;
        // Message will appear via polling
      })
      .catch(function(error) {
        console.error('Failed to send message:', error);
        if (submitBtn) submitBtn.disabled = false;
      });
    });

    // Cleanup on page unload
    window.addEventListener('beforeunload', function() {
      if (pollInterval) clearInterval(pollInterval);
    });
  }

  /**
   * Fetch new chat messages from server.
   */
  function fetchNewMessages() {
    var url = '/api/messages?session=' + encodeURIComponent(sessionId);
    if (lastMessageId) {
      url += '&since=' + encodeURIComponent(lastMessageId);
    }

    fetch(url)
      .then(function(response) {
        if (!response.ok) throw new Error('Fetch failed');
        return response.json();
      })
      .then(function(data) {
        if (chatStatus) {
          chatStatus.style.color = '#00cc00';
          chatStatus.classList.remove('offline');
        }

        if (data.messages && data.messages.length > 0) {
          data.messages.forEach(function(msg) {
            renderMessage(msg);
          });
          lastMessageId = data.messages[data.messages.length - 1].id;
        }
      })
      .catch(function(error) {
        if (chatStatus) {
          chatStatus.style.color = '#cc0000';
          chatStatus.classList.add('offline');
        }
      });
  }

  /**
   * Render a chat message to the UI.
   */
  function renderMessage(message) {
    if (!chatMessages) return;

    var messageDiv = document.createElement('div');
    messageDiv.className = 'chat-message';
    
    if (message.sender === SENDER_NAME) {
      messageDiv.classList.add('chat-message-self');
    }

    var senderDiv = document.createElement('div');
    senderDiv.className = 'chat-sender';
    senderDiv.textContent = message.sender;

    var contentDiv = document.createElement('div');
    contentDiv.className = 'chat-content';
    
    // Sanitize and linkify content
    var sanitized = escapeHtml(message.content);
    var linkified = linkifyUrls(sanitized);
    contentDiv.innerHTML = linkified;

    var timeDiv = document.createElement('div');
    timeDiv.className = 'chat-timestamp';
    timeDiv.textContent = formatTime(message.timestamp);

    messageDiv.appendChild(senderDiv);
    messageDiv.appendChild(contentDiv);
    messageDiv.appendChild(timeDiv);

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  /**
   * Escape HTML to prevent XSS.
   */
  function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Convert URLs in text to clickable links.
   */
  function linkifyUrls(text) {
    var urlRegex = /(https?:\\/\\/[^\\s]+)/g;
    return text.replace(urlRegex, function(url) {
      return '<a href=\"' + url + '\" target=\"_blank\" rel=\"noopener noreferrer\">' + url + '</a>';
    });
  }

  /**
   * Format Unix timestamp to HH:MM.
   */
  function formatTime(timestamp) {
    var date = new Date(timestamp * 1000);
    var hours = date.getHours().toString().padStart(2, '0');
    var minutes = date.getMinutes().toString().padStart(2, '0');
    return hours + ':' + minutes;
  }

  /**
   * Initialize QR code generation (desktop only).
   */
  function initializeQRCode() {
    if (!qrContainer || !qrCode || !qrUrlText) return;

    // Skip on mobile/tablet
    if (window.innerWidth < 900) return;

    // Wait for QRCode library to load
    if (typeof QRCode === 'undefined') {
      setTimeout(initializeQRCode, 100);
      return;
    }

    var currentUrl = window.location.href;
    
    // Generate QR code with smaller size for better fit
    new QRCode(qrCode, {
      text: currentUrl,
      width: 120,
      height: 120
    });

    // Display URL text
    qrUrlText.textContent = currentUrl;
  }

  /**
   * Fetch directory size information.
   */
  function fetchDirectorySize() {
    if (!dirSizeInfo) return;

    fetch('/api/directory-size?session=' + encodeURIComponent(sessionId))
      .then(function(response) {
        if (!response.ok) throw new Error('Fetch failed');
        return response.json();
      })
      .then(function(data) {
        if (data.size) {
          dirSizeInfo.textContent = 'Total: ' + data.size.total_formatted + 
            ' (' + data.size.file_count + ' files)';
        }
      })
      .catch(function(error) {
        dirSizeInfo.textContent = 'Size unavailable';
      });
  }
});
"""
