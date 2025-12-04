# Minimal AI Assistant

A simple AI assistant that supports both **text** and **voice** input, with text and voice responses.

## Features

- ✅ Text input → GPT-4o → Text + Voice response
- ✅ Voice input → STT → GPT-4o → TTS → Text + Voice response
- ✅ RAG support with Pinecone (optional) - Upload documents for context-aware responses

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Your `env` file should contain:
```
OPENAI_API_KEY=your_key
ELEVENLABS_API_KEY=your_key
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
PINECONE_API_KEY=your_key  # Optional - for RAG support
```

### 3. Start Backend
```bash
python app.py
```
Server runs on: `http://localhost:3000`

### 4. Start Frontend
```bash
cd frontend
python -m http.server 8000
```
Or from root: `python -m http.server 8000 --directory frontend`

### 5. Open Browser
Go to: `http://localhost:8000`

## Endpoints

### Core Endpoints
- `POST /stt` - Speech to Text only
- `POST /chat-text` - Text input → (RAG) → GPT → TTS → Returns text + audio URL
- `POST /chat-voice` - Voice input → STT → (RAG) → GPT → TTS → Returns transcription + text + audio URL
- `GET /audio/<filename>` - Serve audio files

### RAG Endpoints (if Pinecone configured)
- `POST /upload-document` - Upload PDF/text documents for RAG
- `POST /delete-document` - Delete document from vector store
- `GET /vector-stats` - Get vector store statistics

See `RAG_SETUP.md` for RAG configuration details.

## Usage

1. **Text Mode**: Type your message and click "Send Message"
2. **Voice Mode**: Click "Start Recording", speak, then click "Stop & Send"
3. View conversation and listen to AI voice responses

## File Structure

```
/
├── app.py              # Flask backend
├── requirements.txt
├── env                 # API keys
├── services/
│   ├── stt.py              # ElevenLabs STT
│   ├── gpt.py              # OpenAI GPT-4o
│   ├── tts.py              # ElevenLabs TTS
│   ├── vector_store.py     # Pinecone vector store
│   ├── embeddings.py       # OpenAI embeddings
│   ├── document_processor.py  # PDF/text processing
│   └── rag.py              # RAG service
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css
└── audio/              # Generated audio files
```

