// Dark mode handling
const themeToggle = document.getElementById("theme-toggle");

function updateTheme() {
  if (
    localStorage.theme === "dark" ||
    (!("theme" in localStorage) &&
      window.matchMedia("(prefers-color-scheme: dark)").matches)
  ) {
    document.documentElement.classList.add("dark");
  } else {
    document.documentElement.classList.remove("dark");
  }
}

themeToggle.addEventListener("click", () => {
  if (document.documentElement.classList.contains("dark")) {
    localStorage.theme = "light";
  } else {
    localStorage.theme = "dark";
  }
  updateTheme();
});

updateTheme();

// File handling
const fileInput = document.getElementById("file-input");
const fileList = document.getElementById("file-list");
const dropZone = document.getElementById("drop-zone");
const uploadProgress = document.getElementById("upload-progress");
const progressBar = document.getElementById("progress-bar");
const progressText = document.getElementById("progress-text");
const uploadButton = document.getElementById("upload-button");
const toast = document.getElementById("toast");
const toastMessage = document.getElementById("toast-message");

// Upload queue management
let uploadQueue = [];
let currentUpload = null;
let totalUploaded = 0;
let uploadStartTime = null;

function showToast(message, isError = false) {
  toastMessage.textContent = message;
  toast.classList.remove("hidden");
  setTimeout(() => {
    toast.classList.add("hidden");
  }, 3000);
}

function getFileIcon(fileType) {
  const icons = {
    image:
      '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />',
    video:
      '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />',
    audio:
      '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />',
    document:
      '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />',
  };

  const type = fileType.split("/")[0];
  return icons[type] || icons.document;
}

function formatFileSize(bytes) {
  const units = ["B", "KB", "MB", "GB"];
  let size = bytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  return `${size.toFixed(1)} ${units[unitIndex]}`;
}

function formatSpeed(bytesPerSecond) {
  return `${formatFileSize(bytesPerSecond)}/s`;
}

function formatTimeRemaining(seconds) {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  return `${Math.round(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}m`;
}

function createFileItem(file) {
  const fileItem = document.createElement("div");
  fileItem.className = "flex flex-col bg-gray-50 dark:bg-gray-700/50 p-3 rounded";
  fileItem.dataset.fileId = file.name + file.size; // Unique identifier

  const header = document.createElement("div");
  header.className = "flex items-center justify-between text-sm text-primary dark:text-blue-400 mb-2";
  
  header.innerHTML = `
    <div class="flex items-center space-x-3">
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        ${getFileIcon(file.type)}
      </svg>
      <span class="truncate max-w-[200px]">${file.name}</span>
    </div>
    <div class="flex items-center space-x-2">
      <span>${formatFileSize(file.size)}</span>
      <button class="remove-file p-1 hover:text-red-500 transition-colors" aria-label="Remove file">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  `;

  const progress = document.createElement("div");
  progress.className = "hidden"; // Initially hidden
  progress.innerHTML = `
    <div class="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-1.5 mb-1">
      <div class="bg-primary dark:bg-blue-400 h-1.5 rounded-full transition-all duration-300" style="width: 0%"></div>
    </div>
    <div class="flex justify-between text-xs text-gray-500 dark:text-gray-400">
      <span class="progress-text">Waiting...</span>
      <span class="speed-text"></span>
    </div>
  `;

  fileItem.appendChild(header);
  fileItem.appendChild(progress);

  // Add remove button handler
  const removeBtn = header.querySelector('.remove-file');
  removeBtn.addEventListener('click', () => {
    uploadQueue = uploadQueue.filter(f => f.name + f.size !== file.name + file.size);
    fileItem.remove();
    updateUploadButtonState();
  });

  return fileItem;
}

function updateUploadButtonState() {
  uploadButton.disabled = uploadQueue.length === 0;
  uploadButton.textContent = currentUpload ? 'Cancel Upload' : 'Upload Files';
}

function updateFileList(files) {
  Array.from(files).forEach((file) => {
    if (!uploadQueue.some(f => f.name + f.size === file.name + file.size)) {
      uploadQueue.push(file);
      const fileItem = createFileItem(file);
      fileList.appendChild(fileItem);
    }
  });
  updateUploadButtonState();
}

function resetUpload() {
  currentUpload = null;
  totalUploaded = 0;
  uploadStartTime = null;
  updateUploadButtonState();
}

async function uploadFile(file) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const fileId = file.name + file.size;
    const fileItem = fileList.querySelector(`[data-file-id="${fileId}"]`);
    const progressBar = fileItem.querySelector('.bg-primary');
    const progressText = fileItem.querySelector('.progress-text');
    const speedText = fileItem.querySelector('.speed-text');
    
    fileItem.querySelector('div:last-child').classList.remove('hidden');
    
    let lastLoaded = 0;
    let lastTime = Date.now();

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        const now = Date.now();
        const timeDiff = (now - lastTime) / 1000;
        const loadedDiff = e.loaded - lastLoaded;
        const speed = loadedDiff / timeDiff;
        
        const percentComplete = (e.loaded / e.total) * 100;
        progressBar.style.width = percentComplete + '%';
        
        if (timeDiff > 0.5) { // Update speed every 500ms
          speedText.textContent = formatSpeed(speed);
          lastLoaded = e.loaded;
          lastTime = now;
        }

        const totalProgress = (totalUploaded + e.loaded) / getTotalSize();
        updateTotalProgress(totalProgress);
        
        const timeElapsed = (Date.now() - uploadStartTime) / 1000;
        const totalProgress2 = totalUploaded + e.loaded;
        const estimatedTotal = timeElapsed * getTotalSize() / totalProgress2;
        const timeRemaining = estimatedTotal - timeElapsed;
        
        progressText.textContent = `${Math.round(percentComplete)}% - ${formatTimeRemaining(timeRemaining)} left`;
      }
    });

    xhr.onload = function() {
      if (xhr.status === 200) {
        totalUploaded += file.size;
        resolve();
      } else {
        reject(new Error(xhr.responseText || 'Upload failed'));
      }
    };

    xhr.onerror = () => reject(new Error('Network error'));

    const formData = new FormData();
    formData.append('file', file);
    xhr.open('POST', '/upload', true);
    xhr.send(formData);
  });
}

function getTotalSize() {
  return uploadQueue.reduce((total, file) => total + file.size, 0);
}

function updateTotalProgress(progress) {
  progressBar.style.width = progress * 100 + '%';
  progressText.textContent = `Overall Progress: ${Math.round(progress * 100)}%`;
}

async function processQueue() {
  if (currentUpload) {
    // Cancel current upload
    resetUpload();
    return;
  }

  uploadProgress.classList.remove('hidden');
  uploadStartTime = Date.now();
  
  try {
    for (const file of uploadQueue) {
      currentUpload = file;
      updateUploadButtonState();
      await uploadFile(file);
    }
    
    showToast('All files uploaded successfully!');
    uploadQueue = [];
    fileList.innerHTML = '';
    
  } catch (error) {
    showToast(error.message, true);
  } finally {
    resetUpload();
    uploadProgress.classList.add('hidden');
    progressBar.style.width = '0%';
  }
}

fileInput.addEventListener("change", (e) => {
  updateFileList(e.target.files);
});

// Drag and drop handling
["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
  dropZone.addEventListener(eventName, preventDefaults, false);
  document.body.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
  e.preventDefault();
  e.stopPropagation();
}

["dragenter", "dragover"].forEach((eventName) => {
  dropZone.addEventListener(eventName, highlight, false);
});

["dragleave", "drop"].forEach((eventName) => {
  dropZone.addEventListener(eventName, unhighlight, false);
});

function highlight() {
  dropZone.classList.add(
    "border-primary",
    "bg-blue-50",
    "dark:bg-blue-900/20"
  );
}

function unhighlight() {
  dropZone.classList.remove(
    "border-primary",
    "bg-blue-50",
    "dark:bg-blue-900/20"
  );
}

dropZone.addEventListener("drop", handleDrop, false);

function handleDrop(e) {
  const dt = e.dataTransfer;
  const files = dt.files;
  updateFileList(files);
}

// Form submission and queue processing
document.querySelector("form").addEventListener("submit", async (e) => {
  e.preventDefault();
  processQueue();
}); 