const API_BASE_URL = 'http://localhost:3000';

// Tab switching
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tabName = btn.dataset.tab;
        
        // Update buttons
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        // Update content
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        document.getElementById(`${tabName}-tab`).classList.add('active');
    });
});

// PDF Upload
document.getElementById('upload-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const userId = document.getElementById('user-id').value;
    const title = document.getElementById('lesson-title').value;
    const file = document.getElementById('pdf-file').files[0];
    
    if (!file) {
        showStatus('upload-status', 'Please select a PDF file', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', userId);
    formData.append('title', title);
    
    showStatus('upload-status', 'Uploading and processing PDF...', 'success');
    
    try {
        const response = await fetch(`${API_BASE_URL}/upload_pdf`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showStatus('upload-status', 
                `✅ Success! Lesson ID: ${data.lesson_id}. Processed ${data.chunks_count} chunks.`, 
                'success');
            
            // Display PDF
            displayPDF(file);
        } else {
            showStatus('upload-status', `❌ Error: ${data.error}`, 'error');
        }
    } catch (error) {
        showStatus('upload-status', `❌ Error: ${error.message}`, 'error');
    }
});

function showStatus(elementId, message, type) {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.className = `status-message ${type}`;
}

function displayPDF(file) {
    const container = document.getElementById('pdf-container');
    const viewer = document.getElementById('lesson-viewer');
    viewer.style.display = 'block';
    container.innerHTML = '';
    
    const reader = new FileReader();
    reader.onload = async (e) => {
        const typedarray = new Uint8Array(e.target.result);
        
        pdfjsLib.getDocument({ data: typedarray }).promise.then(pdf => {
            const numPages = pdf.numPages;
            
            for (let pageNum = 1; pageNum <= numPages; pageNum++) {
                pdf.getPage(pageNum).then(page => {
                    const viewport = page.getViewport({ scale: 1.5 });
                    const canvas = document.createElement('canvas');
                    const context = canvas.getContext('2d');
                    canvas.height = viewport.height;
                    canvas.width = viewport.width;
                    
                    const renderContext = {
                        canvasContext: context,
                        viewport: viewport
                    };
                    
                    page.render(renderContext);
                    container.appendChild(canvas);
                });
            }
        });
    };
    reader.readAsArrayBuffer(file);
}

// Tutor - Ask Question (Simple chat without lesson requirement)
document.getElementById('ask-btn').addEventListener('click', async () => {
    const question = document.getElementById('question-input').value.trim();
    
    if (!question) {
        alert('Please enter a question');
        return;
    }
    
    const responseBox = document.getElementById('tutor-response');
    responseBox.innerHTML = '<p>🤔 Thinking...</p>';
    responseBox.classList.add('show');
    
    // Disable button during request
    const askBtn = document.getElementById('ask-btn');
    askBtn.disabled = true;
    askBtn.textContent = 'Thinking...';
    
    try {
        console.log('Sending request to:', `${API_BASE_URL}/chat`);
        console.log('Question:', question);
        
        // Use simple chat endpoint (no lesson required)
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            mode: 'cors',  // Explicitly enable CORS
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                question: question
            })
        });
        
        console.log('Response status:', response.status);
        console.log('Response headers:', response.headers);
        
        // Check if we got a response
        if (!response.ok) {
            // Try to get error message from response
            let errorMsg = 'Server error occurred';
            try {
                const errorData = await response.json();
                errorMsg = errorData.error || `HTTP ${response.status}: ${response.statusText}`;
            } catch (e) {
                errorMsg = `HTTP ${response.status}: ${response.statusText}`;
            }
            
            responseBox.innerHTML = `
                <h3 style="color: #dc3545;">❌ Error</h3>
                <p style="color: #dc3545;">${errorMsg}</p>
                <p style="color: #666; font-size: 0.9em; margin-top: 10px;">
                    Please check that the server is running on port 3000.
                </p>
            `;
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            responseBox.innerHTML = `
                <h3>💡 AI Tutor Response</h3>
                <p>${data.answer}</p>
            `;
            
            // Get TTS audio
            await getTTSAudio(data.answer);
        } else {
            const errorMsg = data.error || 'Unknown error occurred';
            responseBox.innerHTML = `
                <h3 style="color: #dc3545;">❌ Error</h3>
                <p style="color: #dc3545;">${errorMsg}</p>
                <p style="color: #666; font-size: 0.9em; margin-top: 10px;">
                    Please check that your OpenAI API key is configured correctly in the .env file.
                </p>
            `;
        }
    } catch (error) {
        // Network or connection error
        console.error('Fetch error:', error);
        let errorMsg = error.message;
        
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError') || error.message.includes('CORS')) {
            errorMsg = 'Cannot connect to server. This might be a CORS issue.';
        }
        
        responseBox.innerHTML = `
            <h3 style="color: #dc3545;">Connection Error</h3>
            <p style="color: #dc3545;">${errorMsg}</p>
            <p style="color: #666; font-size: 0.9em; margin-top: 10px;">
                <strong>To fix this:</strong><br>
                1. Make sure server is running: <code>python start_server.py</code><br>
                2. Check browser console (F12) for detailed errors<br>
                3. Try opening the frontend via a web server instead of file://<br>
                4. Server should be on: <code>http://localhost:3000</code>
            </p>
            <p style="color: #666; font-size: 0.9em; margin-top: 10px;">
                <strong>Quick test:</strong> Open <a href="http://localhost:3000/health" target="_blank">http://localhost:3000/health</a> in your browser
            </p>
        `;
    } finally {
        askBtn.disabled = false;
        askBtn.textContent = 'Ask Question';
    }
});

// Voice Recording
let mediaRecorder;
let audioChunks = [];

document.getElementById('record-btn').addEventListener('click', async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        
        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };
        
        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            await sendAudioToSTT(audioBlob);
            stream.getTracks().forEach(track => track.stop());
        };
        
        mediaRecorder.start();
        document.getElementById('record-btn').style.display = 'none';
        document.getElementById('stop-record-btn').style.display = 'inline-block';
        document.getElementById('recording-status').classList.add('recording');
        document.getElementById('recording-status').textContent = '🔴 Recording...';
    } catch (error) {
        alert('Error accessing microphone: ' + error.message);
    }
});

document.getElementById('stop-record-btn').addEventListener('click', () => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        document.getElementById('record-btn').style.display = 'inline-block';
        document.getElementById('stop-record-btn').style.display = 'none';
        document.getElementById('recording-status').classList.remove('recording');
        document.getElementById('recording-status').textContent = '';
    }
});

async function sendAudioToSTT(audioBlob) {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');
    
    try {
        const response = await fetch(`${API_BASE_URL}/speech_to_text`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            document.getElementById('question-input').value = data.text;
        } else {
            alert('STT Error: ' + data.error);
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function getTTSAudio(text) {
    try {
        const response = await fetch(`${API_BASE_URL}/text_to_speech`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text })
        });
        
        if (response.ok) {
            const audioBlob = await response.blob();
            const audioUrl = URL.createObjectURL(audioBlob);
            const audioElement = document.getElementById('tts-audio');
            audioElement.src = audioUrl;
            audioElement.style.display = 'block';
            audioElement.play();
        }
    } catch (error) {
        console.error('TTS Error:', error);
    }
}

// Quiz Generation
let currentQuizSessionId = null;
let currentAnswers = {};

document.getElementById('generate-quiz-btn').addEventListener('click', async () => {
    const userId = document.getElementById('quiz-user-id').value;
    const lessonId = document.getElementById('quiz-lesson-id').value;
    const numQuestions = document.getElementById('num-questions').value;
    
    const quizContainer = document.getElementById('quiz-container');
    quizContainer.innerHTML = '<p>🔄 Generating quiz...</p>';
    
    try {
        const response = await fetch(`${API_BASE_URL}/quiz`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: parseInt(userId),
                lesson_id: parseInt(lessonId),
                num_questions: parseInt(numQuestions)
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentQuizSessionId = data.quiz_session_id;
            currentAnswers = {};
            displayQuiz(data.questions);
        } else {
            quizContainer.innerHTML = `<p style="color: #dc3545;">❌ Error: ${data.error}</p>`;
        }
    } catch (error) {
        quizContainer.innerHTML = `<p style="color: #dc3545;">❌ Error: ${error.message}</p>`;
    }
});

function displayQuiz(questions) {
    const container = document.getElementById('quiz-container');
    container.innerHTML = '';
    
    questions.forEach((q, index) => {
        const questionDiv = document.createElement('div');
        questionDiv.className = 'quiz-question';
        questionDiv.innerHTML = `
            <h4>Question ${index + 1}: ${q.question}</h4>
            <div class="quiz-options">
                ${q.options.map((opt, optIdx) => {
                    const optionLetter = String.fromCharCode(65 + optIdx); // A, B, C, D
                    return `
                        <div class="quiz-option" data-question-id="${q.id}" data-answer="${optionLetter}">
                            ${optionLetter}. ${opt}
                        </div>
                    `;
                }).join('')}
            </div>
        `;
        container.appendChild(questionDiv);
    });
    
    // Add submit button
    const submitBtn = document.createElement('button');
    submitBtn.className = 'btn btn-primary';
    submitBtn.textContent = 'Submit Quiz';
    submitBtn.addEventListener('click', submitQuiz);
    container.appendChild(submitBtn);
    
    // Add click handlers for options
    document.querySelectorAll('.quiz-option').forEach(option => {
        option.addEventListener('click', function() {
            const questionId = this.dataset.questionId;
            const answer = this.dataset.answer;
            
            // Remove previous selection for this question
            document.querySelectorAll(`[data-question-id="${questionId}"]`).forEach(opt => {
                opt.classList.remove('selected');
            });
            
            // Mark this option as selected
            this.classList.add('selected');
            currentAnswers[questionId] = answer;
        });
    });
}

async function submitQuiz() {
    if (!currentQuizSessionId) {
        alert('No quiz session available');
        return;
    }
    
    if (Object.keys(currentAnswers).length === 0) {
        alert('Please answer at least one question');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/evaluate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                quiz_session_id: currentQuizSessionId,
                answers: currentAnswers
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayQuizResults(data);
        } else {
            alert('Error: ' + data.error);
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

function displayQuizResults(results) {
    const resultsBox = document.getElementById('quiz-results');
    resultsBox.innerHTML = `
        <h3>Quiz Results</h3>
        <div class="score-display">${results.score}%</div>
        <p>Correct: ${results.correct} / ${results.total}</p>
    `;
    resultsBox.classList.add('show');
    
    // Highlight correct/incorrect answers
    document.querySelectorAll('.quiz-option').forEach(option => {
        const questionId = option.dataset.questionId;
        // You would need to get the correct answer from the server
        // For now, just show user selections
    });
}

// Dashboard
document.getElementById('load-dashboard-btn').addEventListener('click', async () => {
    const userId = document.getElementById('dashboard-user-id').value;
    
    try {
        const response = await fetch(`${API_BASE_URL}/dashboard?user_id=${userId}`);
        const data = await response.json();
        
        if (response.ok) {
            displayDashboard(data);
        } else {
            alert('Error: ' + data.error);
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
});

function displayDashboard(data) {
    // Display lessons
    const lessonsList = document.getElementById('lessons-list');
    if (data.lessons.length === 0) {
        lessonsList.innerHTML = '<p>No lessons yet. Upload a PDF to get started!</p>';
    } else {
        lessonsList.innerHTML = data.lessons.map(lesson => `
            <div class="lesson-item">
                <h4>${lesson.title}</h4>
                <p>Lesson ID: ${lesson.id}</p>
                <p>Created: ${new Date(lesson.created_at).toLocaleDateString()}</p>
            </div>
        `).join('');
    }
    
    // Display quiz scores
    const scoresList = document.getElementById('quiz-scores-list');
    if (data.quiz_results.length === 0) {
        scoresList.innerHTML = '<p>No quiz results yet. Take a quiz to see your scores!</p>';
    } else {
        scoresList.innerHTML = data.quiz_results.map(result => `
            <div class="quiz-score-item">
                <h4>${result.lesson_title}</h4>
                <p>Completed: ${new Date(result.completed_at).toLocaleDateString()}</p>
                <div class="score">${result.score}%</div>
                <p>${result.correct} / ${result.total} correct</p>
            </div>
        `).join('');
    }
}

