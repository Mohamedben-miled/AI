"""
Minimal AI Assistant - Flask Backend
Supports both text and voice input
"""
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os
import uuid
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
script_dir = os.path.dirname(os.path.abspath(__file__))
env_paths = [
    os.path.join(script_dir, '.env'),
    os.path.join(script_dir, 'env'),
    '.env',
    'env'
]

env_loaded = False
for env_path in env_paths:
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
        print(f"[OK] Loaded env from: {env_path}")
        env_loaded = True
        break

if not env_loaded:
    print("[WARNING] No env file found, trying default load_dotenv()")
    load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
AUDIO_FOLDER = 'audio'
UPLOAD_FOLDER = 'uploads'
os.makedirs(AUDIO_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Session-based conversation memory (in-memory storage)
conversations = {}

def get_conversation_history(session_id):
    """Get conversation history for a session"""
    if session_id not in conversations:
        conversations[session_id] = []
    return conversations[session_id]

def add_to_conversation(session_id, role, content):
    """Add message to conversation history - full session memory"""
    if session_id not in conversations:
        conversations[session_id] = []
    conversations[session_id].append({"role": role, "content": content})
    # Full session memory - no limits (GPT-4o has 128k token context window)

# Import services
from services.stt import STTService
from services.gpt import GPTService
from services.tts import TTSService

# Initialize core services
try:
    print("Initializing core services...")
    stt_service = STTService()
    print("[OK] STT Service initialized")
    gpt_service = GPTService()
    print("[OK] GPT Service initialized")
    tts_service = TTSService()
    print("[OK] TTS Service initialized")
except Exception as e:
    print(f"[ERROR] Failed to initialize core services: {e}")
    import traceback
    traceback.print_exc()
    raise

# Initialize RAG service (optional - only if Pinecone is configured)
rag_service = None
try:
    from services.rag import RAGService
    rag_service = RAGService()
    print("[OK] RAG Service initialized")
except Exception as e:
    print(f"[WARNING] RAG Service not available: {e}")
    print("[INFO] Continuing without RAG. Add PINECONE_API_KEY to enable RAG.")
    rag_service = None

# Initialize Tutoring Service
tutoring_service = None
try:
    from services.tutoring_service import TutoringService
    tutoring_service = TutoringService(gpt_service)
    print("[OK] Tutoring Service initialized")
except Exception as e:
    print(f"[WARNING] Tutoring Service not available: {e}")
    import traceback
    traceback.print_exc()
    tutoring_service = None

# Document cache to store processed documents (text, chunks, sections)
app.processed_documents_cache = {}

print("All services ready!\n")

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'healthy'}), 200

@app.route('/greet', methods=['GET'])
def greet():
    """Generate a friendly greeting from the AI - GPT writes, ElevenLabs speaks"""
    try:
        # GPT writes the greeting text
        greeting_prompt = "Give a warm, friendly greeting to a user who just opened the AI assistant. Be conversational and inviting. Keep it to 1-2 sentences."
        print("[GREET] GPT writing greeting...")
        greeting_text = gpt_service.chat(greeting_prompt)
        
        if not greeting_text:
            greeting_text = "Hello! I'm your AI assistant. How can I help you today?"
        
        # ElevenLabs speaks the greeting
        print("[GREET] ElevenLabs generating speech...")
        audio_bytes = tts_service.synthesize(greeting_text)
        
        audio_url = None
        if audio_bytes:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            audio_filename = f"greeting_{timestamp}.mp3"
            audio_path = os.path.join(AUDIO_FOLDER, audio_filename)
            
            with open(audio_path, 'wb') as f:
                f.write(audio_bytes)
            
            audio_url = f'/audio/{audio_filename}'
            print(f"[GREET] Audio saved: {audio_filename}")
        
        return jsonify({
            'greeting': greeting_text,
            'audio_url': audio_url
        }), 200
        
    except Exception as e:
        print(f"[GREET] Error: {str(e)}")
        return jsonify({
            'greeting': "Hello! I'm your AI assistant. How can I help you today?",
            'audio_url': None
        }), 200

@app.route('/stt', methods=['POST'])
def stt():
    """
    Speech-to-Text endpoint
    Receives audio file and returns transcription
    """
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'error': 'Empty audio file'}), 400
        
        print("[STT] Converting speech to text...")
        text = stt_service.transcribe(audio_file)
        
        if not text:
            return jsonify({'error': 'Failed to transcribe audio'}), 500
        
        print(f"[STT] Transcribed: {text}")
        return jsonify({'text': text}), 200
        
    except Exception as e:
        print(f"[STT] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/chat-text', methods=['POST'])
def chat_text():
    """
    Text input endpoint
    User sends text → (RAG) → GPT → TTS → Returns text reply + audio URL
    """
    try:
        data = request.json
        user_text = data.get('text')
        use_rag = data.get('use_rag', True)  # Default to True if RAG is available
        
        if not user_text:
            return jsonify({'error': 'No text provided'}), 400
        
        print(f"[CHAT-TEXT] User text: {user_text[:50]}...")
        
        # Get GPT response (with RAG if available and enabled)
        print("[CHAT-TEXT] Sending to GPT...")
        if rag_service and use_rag:
            reply_text = rag_service.chat(user_text, use_rag=True)
        else:
            reply_text = gpt_service.chat(user_text)
        
        if not reply_text:
            return jsonify({'error': 'Failed to get GPT response'}), 500
        
        print(f"[CHAT-TEXT] GPT reply: {reply_text[:50]}...")
        
        # Generate TTS audio
        print("[CHAT-TEXT] Generating TTS audio...")
        audio_bytes = tts_service.synthesize(reply_text)
        
        if not audio_bytes:
            return jsonify({'error': 'Failed to generate audio'}), 500
        
        # Save audio file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        audio_filename = f"reply_{timestamp}.mp3"
        audio_path = os.path.join(AUDIO_FOLDER, audio_filename)
        
        with open(audio_path, 'wb') as f:
            f.write(audio_bytes)
        
        print(f"[CHAT-TEXT] Audio saved: {audio_filename}")
        
        # Return text reply and audio URL
        return jsonify({
            'reply_text': reply_text,
            'audio_url': f'/audio/{audio_filename}',
            'rag_used': rag_service is not None and use_rag
        }), 200
        
    except Exception as e:
        print(f"[CHAT-TEXT] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/chat-voice', methods=['POST'])
def chat_voice():
    """
    Voice input endpoint with conversation memory
    User sends audio → STT → GPT → TTS → Returns transcription + text reply + audio URL
    """
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'error': 'Empty audio file'}), 400
        
        session_id = request.form.get('session_id') or str(uuid.uuid4())
        
        print("[CHAT-VOICE] Processing voice input...")
        
        # Step 1: Speech to Text
        print("[CHAT-VOICE] Step 1: STT...")
        transcription = stt_service.transcribe(audio_file)
        
        if not transcription:
            return jsonify({'error': 'Failed to transcribe audio'}), 500
        
        print(f"[CHAT-VOICE] Transcribed: {transcription}")
        
        # Get conversation history
        conversation_history = get_conversation_history(session_id)
        print(f"[CHAT-VOICE] Session: {session_id}, History: {len(conversation_history)} messages")
        
        # Step 2: Get GPT response (with RAG if available)
        print("[CHAT-VOICE] Step 2: GPT...")
        use_rag = request.form.get('use_rag', 'true').lower() == 'true'
        if rag_service and use_rag:
            reply_text = rag_service.chat(transcription, use_rag=True, conversation_history=conversation_history)
        else:
            reply_text = gpt_service.chat(transcription, conversation_history=conversation_history)
        
        if not reply_text:
            return jsonify({'error': 'Failed to get GPT response'}), 500
        
        # Add to conversation history
        add_to_conversation(session_id, "user", transcription)
        add_to_conversation(session_id, "assistant", reply_text)
        
        print(f"[CHAT-VOICE] GPT reply: {reply_text[:50]}...")
        
        # Step 3: Generate TTS audio
        print("[CHAT-VOICE] Step 3: TTS...")
        audio_bytes = tts_service.synthesize(reply_text)
        
        if not audio_bytes:
            return jsonify({'error': 'Failed to generate audio'}), 500
        
        # Save audio file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        audio_filename = f"reply_{timestamp}.mp3"
        audio_path = os.path.join(AUDIO_FOLDER, audio_filename)
        
        with open(audio_path, 'wb') as f:
            f.write(audio_bytes)
        
        print(f"[CHAT-VOICE] Audio saved: {audio_filename}")
        
        # Return transcription, text reply, and audio URL
        return jsonify({
            'transcription': transcription,
            'reply_text': reply_text,
            'audio_url': f'/audio/{audio_filename}',
            'rag_used': rag_service is not None and use_rag,
            'session_id': session_id
        }), 200
        
    except Exception as e:
        print(f"[CHAT-VOICE] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/audio/<filename>', methods=['GET'])
def get_audio(filename):
    """Serve audio files"""
    try:
        return send_from_directory(AUDIO_FOLDER, filename)
    except Exception as e:
        return jsonify({'error': 'Audio file not found'}), 404

@app.route('/upload-document', methods=['POST'])
def upload_document():
    """
    Upload and process document for RAG
    Accepts PDF and text files
    Automatically processes for tutoring mode
    """
    import time
    start_time = time.time()
    
    if not rag_service:
        return jsonify({'error': 'RAG service not available. Configure Pinecone API key.'}), 503
    
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Empty file'}), 400
        
        # Get optional metadata
        document_id = request.form.get('document_id')
        namespace = request.form.get('namespace')
        
        # Save uploaded file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        print(f"[UPLOAD] Processing document: {filename} ({file_size} bytes)")
        
        # Process document
        from services.document_processor import DocumentProcessor
        processor = DocumentProcessor()
        
        document_metadata = {
            'uploaded_at': timestamp,
            'original_filename': file.filename
        }
        
        # Step 1: Extract text
        print("[UPLOAD] Step 1: Extracting text...")
        extract_start = time.time()
        processed = processor.process_document(
            file_path,
            document_id=document_id,
            document_metadata=document_metadata
        )
        extract_time = time.time() - extract_start
        print(f"[UPLOAD] Text extraction completed in {extract_time:.2f}s")
        
        # Step 2: Identify sections for tutoring
        print("[UPLOAD] Step 2: Identifying sections...")
        sections_start = time.time()
        sections = processor.identify_sections(processed['text'])
        sections_time = time.time() - sections_start
        print(f"[UPLOAD] Identified {len(sections)} sections in {sections_time:.2f}s")
        
        # Step 3: Add chunks to vector store (RAG)
        print("[UPLOAD] Step 3: Adding to Pinecone vector store...")
        rag_start = time.time()
        result = rag_service.add_documents(processed['chunks'], namespace=namespace)
        rag_time = time.time() - rag_start
        chunks_added = result.get('count', processed['chunk_count']) if isinstance(result, dict) else processed['chunk_count']
        print(f"[UPLOAD] Added {chunks_added} chunks to Pinecone in {rag_time:.2f}s")
        
        # Cache processed document data for tutoring
        processed_data = {
            'text': processed['text'],
            'chunks': processed['chunks'],
            'sections': sections,
            'document_id': processed['document_id'],
            'file_path': file_path,
            'filename': filename
        }
        app.processed_documents_cache[processed['document_id']] = processed_data
        print(f"[UPLOAD] Cached document data for tutoring")
        
        # Return response immediately (non-blocking for GPT comment and TTS)
        total_time = time.time() - start_time
        print(f"[UPLOAD] Total processing time: {total_time:.2f}s")
        
        # Generate GPT comment and TTS asynchronously (non-blocking)
        import threading
        def generate_comment_async():
            try:
                doc_summary = f"Document: {file.filename}, {processed['chunk_count']} chunks extracted"
                ai_comment_prompt = f"I just processed a document called '{file.filename}' with {processed['chunk_count']} sections. Give a brief, friendly comment about it (1-2 sentences). Be conversational and enthusiastic."
                print("[UPLOAD] GPT writing comment about document...")
                ai_comment = gpt_service.chat(ai_comment_prompt)
                if not ai_comment:
                    ai_comment = f"Great! I've processed {file.filename} and extracted {processed['chunk_count']} sections. I'm ready to answer questions about it!"
                
                print("[UPLOAD] ElevenLabs generating speech for comment...")
                audio_bytes = tts_service.synthesize(ai_comment)
                
                if audio_bytes:
                    audio_filename = f"comment_{timestamp}.mp3"
                    audio_path = os.path.join(AUDIO_FOLDER, audio_filename)
                    
                    with open(audio_path, 'wb') as f:
                        f.write(audio_bytes)
                    
                    print(f"[UPLOAD] Comment audio saved: {audio_filename}")
            except Exception as e:
                print(f"[UPLOAD] Error in async comment generation: {e}")
        
        threading.Thread(target=generate_comment_async, daemon=True).start()
        
        return jsonify({
            'success': True,
            'document_id': processed['document_id'],
            'chunks_count': processed['chunk_count'],
            'sections': sections,
            'pdf_file_path': file_path,
            'pdf_filename': filename,
            'message': f'Document processed and {chunks_added} chunks added to vector store',
            'auto_start_tutoring': True,  # Auto-start tutoring mode
            'processing_time': {
                'extract': round(extract_time, 2),
                'sections': round(sections_time, 2),
                'rag': round(rag_time, 2),
                'total': round(total_time, 2)
            }
        }), 200
        
    except Exception as e:
        print(f"[UPLOAD] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/delete-document', methods=['POST'])
def delete_document():
    """
    Delete a document and its chunks from vector store
    """
    if not rag_service:
        return jsonify({'error': 'RAG service not available'}), 503
    
    try:
        data = request.json
        document_id = data.get('document_id')
        namespace = data.get('namespace')
        
        if not document_id:
            return jsonify({'error': 'document_id required'}), 400
        
        result = rag_service.delete_documents(document_id, namespace=namespace)
        
        return jsonify({
            'success': True,
            'message': f'Document {document_id} deleted'
        }), 200
        
    except Exception as e:
        print(f"[DELETE] Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/vector-stats', methods=['GET'])
def vector_stats():
    """
    Get vector store statistics
    """
    if not rag_service:
        return jsonify({'error': 'RAG service not available'}), 503
    
    try:
        namespace = request.args.get('namespace')
        stats = rag_service.vector_store.get_stats(namespace=namespace)
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
        
    except Exception as e:
        print(f"[STATS] Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/start-tutoring', methods=['POST'])
def start_tutoring():
    """
    Start a tutoring session for a document
    """
    if not tutoring_service:
        return jsonify({'error': 'Tutoring service not available'}), 503
    
    try:
        data = request.json
        document_id = data.get('document_id')
        
        if not document_id:
            return jsonify({'error': 'document_id required'}), 400
        
        # Check cache first
        if document_id in app.processed_documents_cache:
            print(f"[TUTORING] Using cached document data for {document_id}")
            cached = app.processed_documents_cache[document_id]
            text = cached['text']
            sections = cached['sections']
            file_path = cached['file_path']
            filename = cached['filename']
        else:
            # Process document from file
            print(f"[TUTORING] Document not in cache, processing from file...")
            from services.document_processor import DocumentProcessor
            processor = DocumentProcessor()
            
            # Find the file in uploads folder
            file_path = None
            for fname in os.listdir(UPLOAD_FOLDER):
                if document_id in fname or fname.endswith('.pdf'):
                    file_path = os.path.join(UPLOAD_FOLDER, fname)
                    break
            
            if not file_path or not os.path.exists(file_path):
                return jsonify({'error': f'Document file not found for document_id: {document_id}'}), 404
            
            filename = os.path.basename(file_path)
            processed = processor.process_document(file_path, document_id=document_id)
            text = processed['text']
            sections = processor.identify_sections(text)
            
            # Add to RAG if not already added
            if rag_service:
                print(f"[TUTORING] Adding document to RAG...")
                rag_service.add_documents(processed['chunks'])
            
            # Cache it
            app.processed_documents_cache[document_id] = {
                'text': text,
                'chunks': processed['chunks'],
                'sections': sections,
                'document_id': document_id,
                'file_path': file_path,
                'filename': filename
            }
        
        if not sections or len(sections) == 0:
            return jsonify({'error': 'Could not identify sections in document'}), 500
        
        # Start tutoring session
        session_id = tutoring_service.start_tutoring_session(
            document_id=document_id,
            text=text,
            sections=sections
        )
        
        # Auto-advance to first section
        response = tutoring_service.process_user_message(session_id, "start")
        
        current_section_index = tutoring_service.get_session_state(session_id)['current_section_index']
        current_section = sections[current_section_index] if current_section_index < len(sections) else sections[0]
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': response['message'],
            'state': response['state'],
            'pdf_file_path': file_path,
            'pdf_filename': filename,
            'sections': sections,
            'current_section_index': current_section_index,
            'current_section_title': current_section.get('title', 'Section 1')
        }), 200
        
    except Exception as e:
        print(f"[TUTORING] Error starting tutoring: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/tutoring-chat', methods=['POST'])
def tutoring_chat():
    """
    Send a message in an active tutoring session
    """
    if not tutoring_service:
        return jsonify({'error': 'Tutoring service not available'}), 503
    
    try:
        data = request.json
        session_id = data.get('session_id')
        user_message = data.get('message')
        
        if not session_id:
            return jsonify({'error': 'session_id required'}), 400
        if not user_message:
            return jsonify({'error': 'message required'}), 400
        
        # Process user message
        response = tutoring_service.process_user_message(session_id, user_message)
        
        # Get session state for metadata
        session_state = tutoring_service.get_session_state(session_id)
        if not session_state:
            return jsonify({'error': 'Session not found'}), 404
        
        sections = session_state['sections']
        current_section_index = session_state.get('current_section_index', 0)
        current_section = sections[current_section_index] if current_section_index < len(sections) else None
        
        # Build response with metadata
        response_data = {
            'message': response.get('message', ''),
            'state': response.get('state', 'unknown'),
            'section_index': current_section_index,
            'section_title': current_section.get('title', '') if current_section else '',
            'quiz_question': response.get('quiz_question'),
            'quiz_options': response.get('quiz_options'),
            'user_answer': response.get('user_answer')
        }
        
        # Generate TTS audio
        audio_url = None
        try:
            audio_bytes = tts_service.synthesize(response_data['message'])
            if audio_bytes:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                audio_filename = f"tutoring_{timestamp}.mp3"
                audio_path = os.path.join(AUDIO_FOLDER, audio_filename)
                
                with open(audio_path, 'wb') as f:
                    f.write(audio_bytes)
                
                audio_url = f'/audio/{audio_filename}'
                response_data['audio_url'] = audio_url
        except Exception as e:
            print(f"[TUTORING] Error generating TTS: {e}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"[TUTORING] Error in tutoring chat: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("AI Assistant Server with RAG")
    print("=" * 60)
    print("Server running on: http://localhost:3000")
    print("\nCore Endpoints:")
    print("  POST /stt - Speech to Text")
    print("  POST /chat-text - Text input -> (RAG) -> GPT -> TTS")
    print("  POST /chat-voice - Voice input -> STT -> (RAG) -> GPT -> TTS")
    print("  GET  /audio/<filename> - Serve audio files")
    if rag_service:
        print("\nRAG Endpoints:")
        print("  POST /upload-document - Upload PDF/text for RAG")
        print("  POST /delete-document - Delete document from vector store")
        print("  GET  /vector-stats - Get vector store statistics")
    else:
        print("\nRAG: Not available (add PINECONE_API_KEY to enable)")
    print("=" * 60 + "\n")
    
    app.run(debug=True, port=3000, host='127.0.0.1')

