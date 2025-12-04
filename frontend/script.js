/**
 * AI Assistant Frontend
 * Supports both text and voice input
 */

const API_BASE_URL = 'http://localhost:3000';

// Session management for conversation memory
let sessionId = localStorage.getItem('chatSessionId') || null;

// Initialize session on page load
if (!sessionId) {
    sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    localStorage.setItem('chatSessionId', sessionId);
}

// UI Elements
const status = document.getElementById('status');
const textTab = document.getElementById('text-tab');
const voiceTab = document.getElementById('voice-tab');
const pdfTab = document.getElementById('pdf-tab');
const textInputSection = document.getElementById('text-input-section');
const voiceInputSection = document.getElementById('voice-input-section');
const pdfInputSection = document.getElementById('pdf-input-section');
const textInput = document.getElementById('text-input');
const sendTextBtn = document.getElementById('send-text-btn');
const recordBtn = document.getElementById('record-btn');
const stopBtn = document.getElementById('stop-btn');
const conversation = document.getElementById('conversation');
const audioPlayer = document.getElementById('audio-player');
const pdfFileInput = document.getElementById('pdf-file-input');
const selectPdfBtn = document.getElementById('select-pdf-btn');
const uploadPdfBtn = document.getElementById('upload-pdf-btn');
const pdfStatus = document.getElementById('pdf-status');
const pdfFileName = document.getElementById('pdf-file-name');
const documentsPanel = document.getElementById('documents-panel');
const documentsList = document.getElementById('documents-list');

// Track uploaded documents
let uploadedDocuments = [];

// Load documents from localStorage
function loadDocuments() {
    const saved = localStorage.getItem('uploadedDocuments');
    if (saved) {
        uploadedDocuments = JSON.parse(saved);
        updateDocumentsList();
    }
}

// Save documents to localStorage
function saveDocuments() {
    localStorage.setItem('uploadedDocuments', JSON.stringify(uploadedDocuments));
}

// Update documents list display
function updateDocumentsList() {
    if (uploadedDocuments.length === 0) {
        documentsList.innerHTML = '<div class="document-item" style="color: rgba(255, 255, 255, 0.5); font-style: italic;">No documents yet</div>';
        documentsPanel.style.display = 'none';
    } else {
        documentsList.innerHTML = uploadedDocuments.map(doc => 
            `<div class="document-item" title="ID: ${doc.id}">${doc.name}</div>`
        ).join('');
        documentsPanel.style.display = 'block';
    }
}

// Voice recording
let mediaRecorder;
let audioChunks = [];
let isRecording = false;

// KPI Metrics
let metrics = {
    messagesSent: 0,
    responsesReceived: 0,
    errors: 0,
    sttCalls: 0,
    gptCalls: 0,
    ttsCalls: 0,
    responseTimes: []
};

// Load metrics from localStorage
function loadMetrics() {
    const saved = localStorage.getItem('aiAssistantMetrics');
    if (saved) {
        metrics = JSON.parse(saved);
        updateKPIs();
    }
}

// Save metrics to localStorage
function saveMetrics() {
    localStorage.setItem('aiAssistantMetrics', JSON.stringify(metrics));
}

// Update KPI display
function updateKPIs() {
    document.getElementById('kpi-messages').textContent = metrics.messagesSent;
    document.getElementById('kpi-responses').textContent = metrics.responsesReceived;
    
    const totalAttempts = metrics.messagesSent;
    const successRate = totalAttempts > 0 
        ? Math.round((metrics.responsesReceived / totalAttempts) * 100) 
        : 100;
    document.getElementById('kpi-success-rate').textContent = `${successRate}%`;
    
    const avgTime = metrics.responseTimes.length > 0
        ? (metrics.responseTimes.reduce((a, b) => a + b, 0) / metrics.responseTimes.length / 1000).toFixed(1)
        : 0;
    document.getElementById('kpi-avg-time').textContent = `${avgTime}s`;
    
    document.getElementById('kpi-stt-calls').textContent = metrics.sttCalls;
    document.getElementById('kpi-gpt-calls').textContent = metrics.gptCalls;
    document.getElementById('kpi-tts-calls').textContent = metrics.ttsCalls;
    document.getElementById('kpi-errors').textContent = metrics.errors;
    
    saveMetrics();
}

// Reset metrics
function resetMetrics() {
    if (confirm('Reset all performance metrics?')) {
        metrics = {
            messagesSent: 0,
            responsesReceived: 0,
            errors: 0,
            sttCalls: 0,
            gptCalls: 0,
            ttsCalls: 0,
            responseTimes: []
        };
        updateKPIs();
    }
}

// Initialize metrics and documents
loadMetrics();
loadDocuments();

// Tab switching
textTab.addEventListener('click', () => {
    textTab.classList.add('active');
    voiceTab.classList.remove('active');
    pdfTab.classList.remove('active');
    textInputSection.style.display = 'block';
    voiceInputSection.style.display = 'none';
    pdfInputSection.style.display = 'none';
});

voiceTab.addEventListener('click', () => {
    voiceTab.classList.add('active');
    textTab.classList.remove('active');
    pdfTab.classList.remove('active');
    voiceInputSection.style.display = 'block';
    textInputSection.style.display = 'none';
    pdfInputSection.style.display = 'none';
});

pdfTab.addEventListener('click', () => {
    pdfTab.classList.add('active');
    textTab.classList.remove('active');
    voiceTab.classList.remove('active');
    pdfInputSection.style.display = 'block';
    textInputSection.style.display = 'none';
    voiceInputSection.style.display = 'none';
});

// Text input handler
sendTextBtn.addEventListener('click', async () => {
    const userText = textInput.value.trim();
    if (!userText) {
        alert('Please enter a message');
        return;
    }
    
    await sendTextMessage(userText);
});

textInput.addEventListener('keypress', async (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
        const userText = textInput.value.trim();
        if (userText) {
            await sendTextMessage(userText);
        }
    }
});

// Voice recording handlers
recordBtn.addEventListener('click', async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        
        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };
        
        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            await sendVoiceMessage(audioBlob);
            stream.getTracks().forEach(track => track.stop());
        };
        
        mediaRecorder.start();
        isRecording = true;
        recordBtn.style.display = 'none';
        stopBtn.style.display = 'inline-block';
        status.textContent = '🔴 Recording... Click stop when done';
        status.className = 'status recording';
        
    } catch (error) {
        alert('Error accessing microphone: ' + error.message);
        console.error(error);
    }
});

stopBtn.addEventListener('click', () => {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        recordBtn.style.display = 'inline-block';
        stopBtn.style.display = 'none';
        status.textContent = 'Processing...';
        status.className = 'status processing';
    }
});

// Send text message
async function sendTextMessage(userText) {
    // Check if we're in tutoring mode
    if (tutoringSessionId) {
        await sendTutoringMessage(userText);
        textInput.value = '';
        return;
    }
    
    // Clear input
    textInput.value = '';
    
    // Add user message to conversation
    addMessage('user', userText);
    
    // Update metrics
    metrics.messagesSent++;
    updateKPIs();
    
    // Update status
    status.textContent = 'Processing...';
    status.className = 'status processing';
    sendTextBtn.disabled = true;
    
    const startTime = Date.now();
    
    try {
        const response = await fetch(`${API_BASE_URL}/chat-text`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                text: userText,
                session_id: sessionId  // Send session ID for memory
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
            throw new Error(errorData.error || `HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        // Update session ID if provided
        if (data.session_id) {
            sessionId = data.session_id;
            localStorage.setItem('chatSessionId', sessionId);
        }
        
        // Track response time
        const responseTime = Date.now() - startTime;
        metrics.responseTimes.push(responseTime);
        if (metrics.responseTimes.length > 50) {
            metrics.responseTimes.shift(); // Keep only last 50
        }
        
        // Update metrics
        metrics.gptCalls++;
        metrics.ttsCalls++;
        metrics.responsesReceived++;
        updateKPIs();
        
        // Add AI reply to conversation with RAG indicator
        addMessage('ai', data.reply_text, false, data.rag_used);
        
        // Play audio
        if (data.audio_url) {
            playAudio(`${API_BASE_URL}${data.audio_url}`);
        }
        
        status.textContent = '✅ Complete!';
        status.className = 'status success';
        
    } catch (error) {
        console.error('Error:', error);
        metrics.errors++;
        updateKPIs();
        status.textContent = `❌ Error: ${error.message}`;
        status.className = 'status error';
        addMessage('error', `Error: ${error.message}`);
    } finally {
        sendTextBtn.disabled = false;
    }

}

// Send voice message
async function sendVoiceMessage(audioBlob) {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');
    formData.append('session_id', sessionId);  // Add session ID for memory
    
    // Update metrics
    metrics.messagesSent++;
    updateKPIs();
    
    status.textContent = '🔄 Processing: Speech → Text → AI → Speech...';
    status.className = 'status processing';
    
    const startTime = Date.now();
    
    try {
        const response = await fetch(`${API_BASE_URL}/chat-voice`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
            throw new Error(errorData.error || `HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        // Update session ID if provided
        if (data.session_id) {
            sessionId = data.session_id;
            localStorage.setItem('chatSessionId', sessionId);
        }
        
        // Track response time
        const responseTime = Date.now() - startTime;
        metrics.responseTimes.push(responseTime);
        if (metrics.responseTimes.length > 50) {
            metrics.responseTimes.shift(); // Keep only last 50
        }
        
        // Update metrics
        metrics.sttCalls++;
        metrics.gptCalls++;
        metrics.ttsCalls++;
        metrics.responsesReceived++;
        updateKPIs();
        
        // Add user transcription
        if (data.transcription) {
            addMessage('user', data.transcription, true);
        }
        
        // Add AI reply with RAG indicator
        if (data.reply_text) {
            addMessage('ai', data.reply_text, false, data.rag_used);
        }
        
        // Play audio
        if (data.audio_url) {
            playAudio(`${API_BASE_URL}${data.audio_url}`);
        }
        
        status.textContent = '✅ Complete!';
        status.className = 'status success';
        
    } catch (error) {
        console.error('Error:', error);
        metrics.errors++;
        updateKPIs();
        status.textContent = `❌ Error: ${error.message}`;
        status.className = 'status error';
        addMessage('error', `Error: ${error.message}`);
    }
}

// Add message to conversation
function addMessage(role, text, isTranscription = false, ragUsed = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const label = role === 'user' ? (isTranscription ? 'You (voice)' : 'You') : 'AI';
    const icon = role === 'user' ? '👤' : '🤖';
    
    // Add RAG badge if document context was used
    const ragBadge = (role === 'ai' && ragUsed) 
        ? '<span class="rag-badge">📄 Using document context</span>' 
        : '';
    
    messageDiv.innerHTML = `
        <div class="message-header">
            <span class="message-icon">${icon}</span>
            <span class="message-label">${label}</span>
            ${ragBadge}
        </div>
        <div class="message-text">${text}</div>
    `;
    
    conversation.appendChild(messageDiv);
    conversation.scrollTop = conversation.scrollHeight;
}

// Play audio
function playAudio(audioUrl) {
    audioPlayer.src = audioUrl;
    audioPlayer.style.display = 'block';
    try {
        audioPlayer.play().catch(err => {
            console.log('Autoplay prevented:', err);
        });
    } catch (err) {
        console.log('Audio play error:', err);
    }
}

// Tutoring mode variables
let tutoringSessionId = null;
let currentDocumentId = null;
let pdfDocument = null;
let pdfPages = [];

// PDF Viewer elements
const miniPdfViewerPanel = document.getElementById('mini-pdf-viewer-panel');
const miniPdfViewerTitle = document.getElementById('mini-pdf-viewer-title');
const btnMinimizePdf = document.getElementById('btn-minimize-pdf');
const btnMaximizePdf = document.getElementById('btn-maximize-pdf');
const btnClosePdf = document.getElementById('btn-close-pdf');
const pdfCanvasContainer = document.getElementById('pdf-canvas-container');
const sectionHighlight = document.getElementById('section-highlight');
const sectionTitleDisplay = document.getElementById('section-title-display');
const sectionProgress = document.getElementById('section-progress');
const sectionPreview = document.getElementById('section-preview');

// PDF Viewer controls
btnMinimizePdf?.addEventListener('click', () => {
    miniPdfViewerPanel.style.width = '250px';
    miniPdfViewerPanel.classList.add('minimized');
});

btnMaximizePdf?.addEventListener('click', () => {
    miniPdfViewerPanel.style.width = '350px';
    miniPdfViewerPanel.classList.remove('minimized');
});

btnClosePdf?.addEventListener('click', () => {
    miniPdfViewerPanel.style.display = 'none';
});

// Render PDF in mini viewer using PDF.js
async function renderPdfInMiniViewer(file) {
    if (!file || file.type !== 'application/pdf') return;
    
    try {
        // Initialize PDF.js if available
        if (typeof pdfjsLib === 'undefined') {
            console.error('PDF.js library not loaded');
            return;
        }
        
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
        
        const arrayBuffer = await file.arrayBuffer();
        pdfDocument = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
        pdfPages = [];
        
        pdfCanvasContainer.innerHTML = '';
        
            // Render all pages (limit to first 10 pages for performance)
            const maxPages = Math.min(pdfDocument.numPages, 10);
            for (let pageNum = 1; pageNum <= maxPages; pageNum++) {
                const page = await pdfDocument.getPage(pageNum);
                const viewport = page.getViewport({ scale: 1.2 });
                
                const canvas = document.createElement('canvas');
                const context = canvas.getContext('2d');
                canvas.className = 'pdf-page-canvas';
                canvas.height = viewport.height;
                canvas.width = viewport.width;
                canvas.setAttribute('data-page', pageNum);
                
                await page.render({
                    canvasContext: context,
                    viewport: viewport
                }).promise;
                
                pdfCanvasContainer.appendChild(canvas);
                pdfPages.push({ page, canvas, pageNum });
            }
            
            if (pdfDocument.numPages > maxPages) {
                const moreInfo = document.createElement('div');
                moreInfo.className = 'pdf-more-info';
                moreInfo.style.cssText = 'text-align: center; padding: 10px; color: rgba(255,255,255,0.6); font-size: 0.85em;';
                moreInfo.textContent = `... and ${pdfDocument.numPages - maxPages} more pages`;
                pdfCanvasContainer.appendChild(moreInfo);
            }
        
        miniPdfViewerTitle.textContent = file.name;
        miniPdfViewerPanel.style.display = 'block';
        
    } catch (error) {
        console.error('Error rendering PDF:', error);
    }
}

// Show PDF viewer
function showPdfViewer(title, pdfPath) {
    if (pdfCanvasContainer.children.length > 0) {
        // Already rendered client-side
        miniPdfViewerTitle.textContent = title;
        miniPdfViewerPanel.style.display = 'block';
    } else {
        // Fallback: use iframe for server-side PDF
        pdfCanvasContainer.innerHTML = `<iframe src="${pdfPath}" style="width: 100%; height: 100%; border: none;"></iframe>`;
        miniPdfViewerTitle.textContent = title;
        miniPdfViewerPanel.style.display = 'block';
    }
}

// Highlight section in PDF viewer - shows where AI is currently reading
function highlightSection(sectionIndex, sectionTitle, sectionText, totalSections, emphasize = false) {
    sectionTitleDisplay.textContent = sectionTitle || `Section ${sectionIndex + 1}`;
    sectionProgress.textContent = `Section ${sectionIndex + 1} of ${totalSections}`;
    
    // Show preview of section text
    const previewText = sectionText ? sectionText.substring(0, 200) + (sectionText.length > 200 ? '...' : '') : '';
    sectionPreview.textContent = previewText;
    
    sectionHighlight.style.display = 'block';
    
    // Add emphasis styling if wrong answer (needs review)
    if (emphasize) {
        sectionHighlight.style.border = '2px solid #f44336';
        sectionHighlight.style.backgroundColor = 'rgba(244, 67, 54, 0.1)';
        sectionHighlight.classList.add('section-needs-review');
    } else {
        sectionHighlight.style.border = '2px solid rgba(100, 181, 246, 0.6)';
        sectionHighlight.style.backgroundColor = 'rgba(100, 181, 246, 0.15)';
        sectionHighlight.classList.remove('section-needs-review');
    }
    
    // Clear previous highlights
    pdfPages.forEach(({ canvas }) => {
        canvas.style.boxShadow = '';
        canvas.style.border = '';
        canvas.classList.remove('pdf-page-reading');
    });
    
    // Highlight the relevant page(s) where this section is located
    if (pdfPages.length > 0 && sectionIndex >= 0 && totalSections > 0) {
        // Calculate which page(s) contain this section
        const sectionRatio = sectionIndex / totalSections;
        const estimatedPage = Math.max(1, Math.min(
            Math.ceil(sectionRatio * pdfPages.length),
            pdfPages.length
        ));
        
        // Find and highlight the target page
        const targetCanvas = pdfPages.find(p => p.pageNum === estimatedPage)?.canvas;
        if (targetCanvas) {
            // Scroll to the page
            targetCanvas.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            // Add persistent highlight showing AI is reading this section
            const shadowColor = emphasize ? 'rgba(244, 67, 54, 0.9)' : 'rgba(100, 181, 246, 0.9)';
            const shadowSize = emphasize ? '40px' : '25px';
            targetCanvas.style.boxShadow = `0 0 ${shadowSize} ${shadowColor}, inset 0 0 20px ${shadowColor}`;
            targetCanvas.style.border = `3px solid ${emphasize ? '#f44336' : '#64b5f6'}`;
            targetCanvas.classList.add('pdf-page-reading');
            
            // Add a reading indicator overlay
            if (!targetCanvas.dataset.readingIndicator) {
                const indicator = document.createElement('div');
                indicator.className = 'pdf-reading-indicator';
                indicator.textContent = '📖 AI is reading here';
                indicator.style.cssText = `
                    position: absolute;
                    top: 10px;
                    left: 50%;
                    transform: translateX(-50%);
                    background: rgba(100, 181, 246, 0.9);
                    color: white;
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-size: 0.85em;
                    font-weight: 600;
                    z-index: 1000;
                    pointer-events: none;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                `;
                
                // Position relative to canvas
                const canvasRect = targetCanvas.getBoundingClientRect();
                const containerRect = pdfCanvasContainer.getBoundingClientRect();
                indicator.style.position = 'absolute';
                indicator.style.top = `${canvasRect.top - containerRect.top + 10}px`;
                indicator.style.left = `${canvasRect.left - containerRect.left + (canvasRect.width / 2)}px`;
                indicator.style.transform = 'translateX(-50%)';
                
                pdfCanvasContainer.appendChild(indicator);
                targetCanvas.dataset.readingIndicator = 'true';
                
                // Remove indicator after 5 seconds (but keep page highlight)
                setTimeout(() => {
                    if (indicator.parentNode) {
                        indicator.style.opacity = '0';
                        indicator.style.transition = 'opacity 0.5s';
                        setTimeout(() => indicator.remove(), 500);
                    }
                }, 5000);
            }
            
            // Keep highlight persistent (don't remove after timeout)
            // Only remove when a new section is highlighted
        }
        
        // Also highlight adjacent pages if section spans multiple pages
        if (estimatedPage > 1) {
            const prevCanvas = pdfPages.find(p => p.pageNum === estimatedPage - 1)?.canvas;
            if (prevCanvas) {
                prevCanvas.style.boxShadow = `0 0 15px rgba(100, 181, 246, 0.5)`;
                prevCanvas.style.border = `2px solid rgba(100, 181, 246, 0.5)`;
            }
        }
        if (estimatedPage < pdfPages.length) {
            const nextCanvas = pdfPages.find(p => p.pageNum === estimatedPage + 1)?.canvas;
            if (nextCanvas) {
                nextCanvas.style.boxShadow = `0 0 15px rgba(100, 181, 246, 0.5)`;
                nextCanvas.style.border = `2px solid rgba(100, 181, 246, 0.5)`;
            }
        }
    }
}

// Start tutoring session
async function startTutoringSession(documentId) {
    if (!documentId) {
        console.error('No document ID provided');
        return;
    }
    
    currentDocumentId = documentId;
    
    try {
        status.textContent = 'Starting tutoring session...';
        status.className = 'status processing';
        
        const response = await fetch(`${API_BASE_URL}/start-tutoring`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ document_id: documentId })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to start tutoring session');
        }
        
        tutoringSessionId = data.session_id;
        
        // Show PDF viewer if we have the path
        if (data.pdf_file_path) {
            showPdfViewer(data.pdf_filename || 'Document', data.pdf_file_path);
            if (data.current_section_index !== undefined && data.current_section_title) {
                highlightSection(
                    data.current_section_index,
                    data.current_section_title,
                    data.section_text || '',
                    data.sections ? data.sections.length : 1
                );
            }
        }
        
        // Add AI's message (might contain introduction + first section)
        addMessage('ai', data.message);
        
        // Display quiz if present in initial response
        if (data.quiz_question && data.quiz_options) {
            displayQuizQuestion(data.quiz_question, data.quiz_options);
        }
        
        // Ensure section highlighting is displayed
        if (data.current_section_index !== undefined && data.current_section_title) {
            highlightSection(
                data.current_section_index,
                data.current_section_title,
                data.section_text || '',
                data.sections ? data.sections.length : 1,
                false
            );
        }
        
        // Play TTS audio (should be provided from backend)
        if (data.audio_url) {
            console.log('[TUTORING] Playing audio from backend:', data.audio_url);
            playAudio(`${API_BASE_URL}${data.audio_url}`);
        } else {
            console.warn('[TUTORING] No audio URL provided in response');
        }
        
        status.textContent = '✅ Tutoring session started!';
        status.className = 'status success';
        
        // Auto-scroll to show the message
        conversation.scrollTop = conversation.scrollHeight;
        
        // Switch to text input for tutoring
        textTab.click();
        
    } catch (error) {
        console.error('Error starting tutoring:', error);
        status.textContent = `❌ Error: ${error.message}`;
        status.className = 'status error';
        addMessage('error', `Error starting tutoring: ${error.message}`);
    }
}

// Send tutoring message
async function sendTutoringMessage(userMessage) {
    if (!tutoringSessionId) {
        addMessage('error', 'No active tutoring session');
        return;
    }
    
    addMessage('user', userMessage);
    metrics.messagesSent++;
    updateKPIs();
    
    status.textContent = 'Processing...';
    status.className = 'status processing';
    
    try {
        const response = await fetch(`${API_BASE_URL}/tutoring-chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: tutoringSessionId,
                message: userMessage
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to send tutoring message');
        }
        
        // Add AI response with special styling for wrong answers
        if (data.is_correct === false) {
            // Wrong answer - add visual indicator
            const errorMsg = document.createElement('div');
            errorMsg.className = 'message ai wrong-answer';
            errorMsg.innerHTML = `
                <div class="wrong-answer-indicator">⚠️ Let's review this section</div>
                <div class="message-content">${escapeHtml(data.message)}</div>
                ${data.explanation_attempts > 0 ? `<div class="attempt-counter">Explanation attempt ${data.explanation_attempts} of 5</div>` : ''}
            `;
            conversation.appendChild(errorMsg);
        } else {
            addMessage('ai', data.message);
        }
        
        // Update section highlight if needed
        if (data.section_index !== undefined && data.section_title) {
            // Get total sections - try to get from response or use estimate
            const totalSections = data.sections ? data.sections.length : (data.section_index + 1);
            highlightSection(
                data.section_index,
                data.section_title,
                data.section_text || '',
                totalSections,
                data.highlight_section  // Pass highlight flag for stronger visual emphasis
            );
        }
        
        // Handle quiz questions - display them interactively
        if (data.quiz_question && data.quiz_options) {
            displayQuizQuestion(data.quiz_question, data.quiz_options);
            hideNextSectionButton(); // Hide button when new quiz appears
        }
        
        // Show "Next Section" button if available (after quiz is passed)
        if (data.can_skip_to_next && data.state === 'quiz_complete') {
            showNextSectionButton();
        } else if (data.state !== 'quiz_complete') {
            hideNextSectionButton(); // Hide if not in quiz_complete state
        }
        
        // Play audio
        if (data.audio_url) {
            playAudio(`${API_BASE_URL}${data.audio_url}`);
        }
        
        metrics.responsesReceived++;
        updateKPIs();
        
        status.textContent = data.state === 'complete' ? '✅ Session completed!' : '✅ Ready';
        status.className = 'status success';
        
        // If session is complete, reset
        if (data.state === 'complete') {
            tutoringSessionId = null;
        }
        
    } catch (error) {
        console.error('Error in tutoring chat:', error);
        metrics.errors++;
        updateKPIs();
        status.textContent = `❌ Error: ${error.message}`;
        status.className = 'status error';
        addMessage('error', `Error: ${error.message}`);
    }
}

// Helper function to escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Show/Hide Next Section button
function showNextSectionButton() {
    // Remove existing button if any
    hideNextSectionButton();
    
    const buttonContainer = document.createElement('div');
    buttonContainer.id = 'next-section-button-container';
    buttonContainer.style.cssText = 'margin: 15px 0; text-align: center;';
    
    const nextBtn = document.createElement('button');
    nextBtn.id = 'btn-next-section';
    nextBtn.textContent = '➡️ Move to Next Section';
    nextBtn.className = 'btn-next-section';
    nextBtn.style.cssText = `
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        font-size: 1em;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    `;
    
    nextBtn.onmouseover = () => {
        nextBtn.style.transform = 'translateY(-2px)';
        nextBtn.style.boxShadow = '0 6px 20px rgba(102, 126, 234, 0.6)';
    };
    nextBtn.onmouseout = () => {
        nextBtn.style.transform = 'translateY(0)';
        nextBtn.style.boxShadow = '0 4px 15px rgba(102, 126, 234, 0.4)';
    };
    
    nextBtn.onclick = () => {
        if (tutoringSessionId) {
            sendTutoringMessage('next section');
        }
    };
    
    buttonContainer.appendChild(nextBtn);
    conversation.appendChild(buttonContainer);
    
    // Scroll to button
    buttonContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function hideNextSectionButton() {
    const existing = document.getElementById('next-section-button-container');
    if (existing) {
        existing.remove();
    }
}

// Display quiz question in the conversation
function displayQuizQuestion(question, options) {
    
    const quizDiv = document.createElement('div');
    quizDiv.className = 'quiz-container';
    
    // Create question element
    const questionDiv = document.createElement('div');
    questionDiv.className = 'quiz-question';
    questionDiv.textContent = question;
    
    // Create options container
    const optionsDiv = document.createElement('div');
    optionsDiv.className = 'quiz-options';
    
    // Create option buttons
    options.forEach((opt, idx) => {
        const letter = String.fromCharCode(65 + idx); // A, B, C, D
        const button = document.createElement('button');
        button.className = 'quiz-option';
        button.textContent = `${letter}) ${opt}`;
        button.onclick = () => selectQuizAnswer(letter);
        optionsDiv.appendChild(button);
    });
    
    quizDiv.appendChild(questionDiv);
    quizDiv.appendChild(optionsDiv);
    
    conversation.appendChild(quizDiv);
    conversation.scrollTop = conversation.scrollHeight;
}

// Select quiz answer
function selectQuizAnswer(answer) {
    if (tutoringSessionId) {
        // Add user's answer selection to conversation
        addMessage('user', `I choose answer ${answer}`);
        
        // Send the answer to the tutoring service
        sendTutoringMessage(answer);
        
        // Remove quiz buttons to prevent multiple clicks
        const quizOptions = document.querySelectorAll('.quiz-option');
        quizOptions.forEach(btn => {
            btn.disabled = true;
            if (btn.textContent.trim().startsWith(answer)) {
                btn.style.background = 'rgba(100, 181, 246, 0.3)';
                btn.style.borderColor = 'rgba(100, 181, 246, 0.8)';
            }
        });
    }
}

// Progress step helpers
function updateProgressStep(stepId, status, icon = '') {
    const step = document.getElementById(stepId);
    if (!step) return;
    
    step.className = `progress-step ${status}`;
    const iconEl = step.querySelector('.step-icon');
    if (iconEl && icon) {
        iconEl.textContent = icon;
    }
}

function updateProgressSummary(stepId, status) {
    const summaryText = document.getElementById('progress-summary-text');
    if (summaryText) {
        const stepNames = {
            'step-extract': 'Extracting text',
            'step-sections': 'Identifying sections',
            'step-rag': 'Uploading to Pinecone'
        };
        summaryText.textContent = `${stepNames[stepId] || 'Processing'}... (${status})`;
    }
}

function updateProgressSummaryTime(timeText) {
    const timeEl = document.getElementById('progress-time');
    if (timeEl) {
        timeEl.textContent = timeText;
    }
}

// Initialize progress info buttons
function initProgressInfoButtons() {
    document.querySelectorAll('.step-info-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const step = btn.closest('.progress-step');
            const details = step.querySelector('.step-details');
            if (details) {
                details.style.display = details.style.display === 'none' ? 'block' : 'none';
            }
        });
    });
}

// Check server connection on load
async function checkServer() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
            status.textContent = '✅ Connected to server';
            status.className = 'status success';
        }
    } catch (error) {
        status.textContent = '❌ Cannot connect to server. Make sure backend is running on port 3000.';
        status.className = 'status error';
    }
}

// Reset KPI button
const resetBtn = document.getElementById('reset-kpis-btn');
if (resetBtn) {
    resetBtn.addEventListener('click', resetMetrics);
}

// PDF Upload handlers
selectPdfBtn.addEventListener('click', () => {
    pdfFileInput.click();
});

pdfFileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (file) {
        pdfFileName.textContent = `Selected: ${file.name}`;
        pdfFileName.style.display = 'block';
        uploadPdfBtn.style.display = 'inline-block';
        uploadPdfBtn.disabled = false;
        pdfStatus.style.display = 'none';
        
        // Render PDF immediately in mini viewer
        if (file.type === 'application/pdf') {
            await renderPdfInMiniViewer(file);
        }
    }
});

uploadPdfBtn.addEventListener('click', async () => {
    const file = pdfFileInput.files[0];
    if (!file) {
        showPdfStatus('Please select a file first', 'error');
        return;
    }
    
    uploadPdfBtn.disabled = true;
    uploadPdfBtn.textContent = '⏳ Processing...';
    
    // Show progress container
    const progressContainer = document.getElementById('pdf-progress-container');
    if (progressContainer) {
        progressContainer.style.display = 'block';
    }
    
    // Initialize progress steps
    updateProgressStep('step-extract', 'active', '⏳');
    updateProgressStep('step-sections', 'pending', '⏳');
    updateProgressStep('step-rag', 'pending', '⏳');
    updateProgressSummary('step-extract', 'Starting...');
    
    const startTime = Date.now();
    const updateTimer = setInterval(() => {
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
        updateProgressSummaryTime(`${elapsed}s`);
    }, 100);
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_BASE_URL}/upload-document`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        clearInterval(updateTimer);
        
        if (response.ok) {
            // Update progress steps
            updateProgressStep('step-extract', 'complete', '✅');
            updateProgressSummary('step-extract', 'Complete');
            
            if (data.processing_time) {
                setTimeout(() => {
                    updateProgressStep('step-sections', 'complete', '✅');
                    updateProgressSummary('step-sections', 'Complete');
                    
                    setTimeout(() => {
                        updateProgressStep('step-rag', 'complete', '✅');
                        updateProgressSummary('step-rag', 'Complete');
                        updateProgressSummaryTime(`Total: ${data.processing_time.total}s`);
                    }, 500);
                }, 500);
            }
            
            // Add to documents list
            uploadedDocuments.push({
                id: data.document_id,
                name: file.name,
                chunks: data.chunks_count,
                uploadedAt: new Date().toISOString()
            });
            saveDocuments();
            updateDocumentsList();
            
            showPdfStatus(
                `✅ Success! Processed ${data.chunks_count} chunks. Document ID: ${data.document_id}`,
                'success'
            );
            
            // Auto-start tutoring if flag is set
            if (data.auto_start_tutoring && data.document_id) {
                // Wait a moment for progress to show, then start tutoring
                setTimeout(() => {
                    startTutoringSession(data.document_id);
                }, 1000);
            }
            
            // Show PDF viewer with file path if available
            if (data.pdf_file_path) {
                showPdfViewer(data.pdf_filename || file.name, data.pdf_file_path);
            }
            
            pdfFileInput.value = '';
            pdfFileName.textContent = '';
            pdfFileName.style.display = 'none';
            uploadPdfBtn.style.display = 'none';
            
            // Update status
            status.textContent = '✅ Document uploaded successfully';
            status.className = 'status success';
        } else {
            updateProgressStep('step-extract', 'error', '❌');
            showPdfStatus(`❌ Error: ${data.error}`, 'error');
            status.textContent = `❌ Upload failed: ${data.error}`;
            status.className = 'status error';
        }
    } catch (error) {
        clearInterval(updateTimer);
        console.error('Upload error:', error);
        updateProgressStep('step-extract', 'error', '❌');
        showPdfStatus(`❌ Error: ${error.message}`, 'error');
        status.textContent = `❌ Upload failed: ${error.message}`;
        status.className = 'status error';
    } finally {
        uploadPdfBtn.disabled = false;
        uploadPdfBtn.textContent = '⬆️ Upload & Process';
    }
});

function showPdfStatus(message, type) {
    pdfStatus.textContent = message;
    pdfStatus.className = `pdf-status pdf-status-${type}`;
    pdfStatus.style.display = 'block';
}

// Greet user on page load
async function greetUser() {
    try {
        const response = await fetch(`${API_BASE_URL}/greet`, {
            method: 'GET'
        });
        
        if (response.ok) {
            const data = await response.json();
            addMessage('ai', data.greeting);
            
            // Play greeting audio (ElevenLabs speaking)
            if (data.audio_url) {
                playAudio(`${API_BASE_URL}${data.audio_url}`);
            }
        }
    } catch (error) {
        console.error('Greeting error:', error);
        // Fallback greeting
        addMessage('ai', "Hello! I'm your AI assistant. How can I help you today?");
    }
}

// Initialize progress info buttons on load
initProgressInfoButtons();

// Check on page load
checkServer().then(() => {
    setTimeout(greetUser, 500); // Small delay to ensure server is ready
});

