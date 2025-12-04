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
  // ==========================================================================
  // CONFIGURATION
  // ==========================================================================

  // Maximum number of simultaneous upload connections.
  // Higher values can improve throughput but may overwhelm slower networks.
  var MAX_PARALLEL = 4;


  // ==========================================================================
  // FILE INPUT DISPLAY
  // ==========================================================================
  // Update the filename display when user selects files.

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


  // ==========================================================================
  // PARALLEL MULTI-FILE UPLOAD
  // ==========================================================================
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


  // ==========================================================================
  // UTILITY FUNCTIONS
  // ==========================================================================

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
});
"""
