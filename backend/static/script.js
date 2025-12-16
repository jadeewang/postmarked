/**
 * postmarked - frontend application
 * handles file upload, API communication, and postcard display
 */

// API URL - same server, so just use relative paths
const API_BASE = '';

// state
let state = {
    files: [],
    sessionId: null,
    artStyle: 'vintage_postcard',
    captionTone: 'artistic',
    postcard: null
};

// dom elements
const elements = {
    // steps
    stepUpload: document.getElementById('step-upload'),
    stepCustomize: document.getElementById('step-customize'),
    stepGenerating: document.getElementById('step-generating'),
    stepResult: document.getElementById('step-result'),
    
    // upload
    uploadZone: document.getElementById('upload-zone'),
    fileInput: document.getElementById('file-input'),
    previewGrid: document.getElementById('preview-grid'),
    btnNextUpload: document.getElementById('btn-next-upload'),
    
    // customize
    locationInput: document.getElementById('location'),
    descriptionInput: document.getElementById('description'),
    artStyles: document.getElementById('art-styles'),
    captionTones: document.getElementById('caption-tones'),
    btnBackCustomize: document.getElementById('btn-back-customize'),
    btnGenerate: document.getElementById('btn-generate'),
    
    // generating
    generatingStatus: document.getElementById('generating-status'),
    
    // result
    postcardImage: document.getElementById('postcard-image'),
    postcardLocation: document.getElementById('postcard-location'),
    postcardCaption: document.getElementById('postcard-caption'),
    btnRegenerate: document.getElementById('btn-regenerate'),
    btnDownload: document.getElementById('btn-download'),
    btnStartOver: document.getElementById('btn-start-over')
};

// ============================================
// step navigation
// ============================================

function showStep(stepId) {
    document.querySelectorAll('.step').forEach(step => {
        step.classList.remove('active');
    });
    document.getElementById(stepId).classList.add('active');
}

// ============================================
// file upload handling
// ============================================

function initUpload() {
    const { uploadZone, fileInput, btnNextUpload } = elements;
    
    // click to upload
    uploadZone.addEventListener('click', () => fileInput.click());
    
    // file selection
    fileInput.addEventListener('change', handleFileSelect);
    
    // drag and drop
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });
    
    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });
    
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });
    
    // next button
    btnNextUpload.addEventListener('click', () => {
        showStep('step-customize');
    });
}

function handleFileSelect(e) {
    handleFiles(e.target.files);
}

function handleFiles(fileList) {
    const newFiles = Array.from(fileList).filter(file => 
        file.type.startsWith('image/')
    );
    
    // limit to 3 files
    const totalFiles = state.files.length + newFiles.length;
    if (totalFiles > 3) {
        const allowed = 3 - state.files.length;
        state.files = [...state.files, ...newFiles.slice(0, allowed)];
    } else {
        state.files = [...state.files, ...newFiles];
    }
    
    updatePreviews();
    updateUploadButton();
}

function updatePreviews() {
    const { previewGrid, uploadZone } = elements;
    previewGrid.innerHTML = '';
    
    if (state.files.length === 0) {
        uploadZone.style.display = 'block';
        return;
    }
    
    // hide upload zone when we have files
    if (state.files.length === 3) {
        uploadZone.style.display = 'none';
    } else {
        uploadZone.style.display = 'block';
    }
    
    state.files.forEach((file, index) => {
        const item = document.createElement('div');
        item.className = 'preview-item';
        
        const img = document.createElement('img');
        img.src = URL.createObjectURL(file);
        img.alt = `Photo ${index + 1}`;
        
        const removeBtn = document.createElement('button');
        removeBtn.className = 'preview-remove';
        removeBtn.innerHTML = '×';
        removeBtn.onclick = (e) => {
            e.stopPropagation();
            removeFile(index);
        };
        
        item.appendChild(img);
        item.appendChild(removeBtn);
        previewGrid.appendChild(item);
    });
}

function removeFile(index) {
    state.files.splice(index, 1);
    updatePreviews();
    updateUploadButton();
}

function updateUploadButton() {
    elements.btnNextUpload.disabled = state.files.length === 0;
}

// ============================================
// customize step
// ============================================

function initCustomize() {
    const { artStyles, captionTones, btnBackCustomize, btnGenerate } = elements;
    
    // art style selection
    artStyles.querySelectorAll('.style-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            artStyles.querySelectorAll('.style-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.artStyle = btn.dataset.value;
        });
    });
    
    // caption tone selection
    captionTones.querySelectorAll('.style-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            captionTones.querySelectorAll('.style-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.captionTone = btn.dataset.value;
        });
    });
    
    // back button
    btnBackCustomize.addEventListener('click', () => {
        showStep('step-upload');
    });
    
    // generate button
    btnGenerate.addEventListener('click', generatePostcard);
}

// ============================================
// postcard generation
// ============================================

async function generatePostcard() {
    const { locationInput, descriptionInput, generatingStatus } = elements;
    
    const location = locationInput.value.trim() || 'my trip';
    const description = descriptionInput.value.trim();
    
    showStep('step-generating');
    
    try {
        // step 1: upload files using the full pipeline
        generatingStatus.textContent = 'uploading photos...';
        
        const formData = new FormData();
        state.files.forEach(file => {
            formData.append('files', file);
        });
        formData.append('location_label', location);
        formData.append('art_style', state.artStyle);
        formData.append('caption_tone', state.captionTone);
        if (description) {
            formData.append('user_description', description);
        }
        
        generatingStatus.textContent = 'analyzing your memories...';
        
        // use the full pipeline endpoint
        const response = await fetch(`${API_BASE}/api/pipeline`, {
            method: 'POST',
            body: formData
        });
        
        generatingStatus.textContent = 'creating your postcard...';
        
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.error || 'Failed to generate postcard');
        }
        
        // save state
        state.sessionId = result.session_id;
        state.postcard = result.postcard;
        
        // display result
        displayPostcard(result.postcard);
        showStep('step-result');
        
    } catch (error) {
        console.error('Generation error:', error);
        showError(error.message);
    }
}

function displayPostcard(postcard) {
    const { postcardImage, postcardLocation, postcardCaption } = elements;
    
    if (postcard.image?.image_url) {
        postcardImage.src = postcard.image.image_url;
    }
    
    if (postcard.caption) {
        postcardLocation.textContent = postcard.caption.location_label || '';
        postcardCaption.textContent = `"${postcard.caption.caption || ''}"`;
    }
}

function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    
    const stepContent = elements.stepGenerating.querySelector('.step-content');
    stepContent.innerHTML = '';
    stepContent.appendChild(errorDiv);
    
    const retryBtn = document.createElement('button');
    retryBtn.className = 'btn btn-secondary';
    retryBtn.textContent = 'try again';
    retryBtn.style.marginTop = '1rem';
    retryBtn.onclick = () => showStep('step-customize');
    stepContent.appendChild(retryBtn);
}

// ============================================
// result actions
// ============================================

function initResult() {
    const { btnRegenerate, btnDownload, btnStartOver } = elements;
    
    btnRegenerate.addEventListener('click', regeneratePostcard);
    btnDownload.addEventListener('click', downloadPostcard);
    btnStartOver.addEventListener('click', startOver);
}

async function regeneratePostcard() {
    if (!state.sessionId) return;
    
    showStep('step-generating');
    elements.generatingStatus.textContent = 'regenerating your postcard...';
    
    try {
        const response = await fetch(`${API_BASE}/api/regenerate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: state.sessionId,
                location_label: elements.locationInput.value.trim() || 'my trip',
                art_style: state.artStyle,
                caption_tone: state.captionTone,
                user_description: elements.descriptionInput.value.trim() || null
            })
        });
        
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.error || 'Failed to regenerate');
        }
        
        state.postcard = result.postcard;
        displayPostcard(result.postcard);
        showStep('step-result');
        
    } catch (error) {
        console.error('Regeneration error:', error);
        showError(error.message);
    }
}

async function downloadPostcard() {
    if (!state.postcard?.image?.image_url) return;
    
    try {
        // fetch the image
        const response = await fetch(state.postcard.image.image_url);
        const blob = await response.blob();
        
        // create download link
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `postmarked-${Date.now()}.png`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
    } catch (error) {
        console.error('Download error:', error);
        // fallback: open in new tab
        window.open(state.postcard.image.image_url, '_blank');
    }
}

function startOver() {
    // reset state
    state = {
        files: [],
        sessionId: null,
        artStyle: 'vintage_postcard',
        captionTone: 'artistic',
        postcard: null
    };
    
    // reset UI
    elements.fileInput.value = '';
    elements.previewGrid.innerHTML = '';
    elements.uploadZone.style.display = 'block';
    elements.locationInput.value = '';
    elements.descriptionInput.value = '';
    elements.btnNextUpload.disabled = true;
    
    // reset style selections
    elements.artStyles.querySelectorAll('.style-btn').forEach((btn, i) => {
        btn.classList.toggle('active', i === 0);
    });
    elements.captionTones.querySelectorAll('.style-btn').forEach((btn, i) => {
        btn.classList.toggle('active', i === 0);
    });
    
    // go to first step
    showStep('step-upload');
}

// ============================================
// initialize
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initUpload();
    initCustomize();
    initResult();
});

