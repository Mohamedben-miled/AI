# RAG Setup Guide

## Environment Variables

Add these to your `env` file:

```
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=ai-assistant-index  # Optional, defaults to this
PINECONE_REGION=us-east-1  # Optional, defaults to us-east-1
PINECONE_DIMENSION=1536  # Optional, defaults to 1536 (OpenAI ada-002)
RAG_TOP_K=5  # Optional, number of chunks to retrieve
RAG_CONTEXT_WINDOW=2000  # Optional, max context characters
```

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### 1. Upload Documents

```bash
curl -X POST http://localhost:3000/upload-document \
  -F "file=@document.pdf" \
  -F "document_id=doc1" \
  -F "namespace=my_namespace"
```

### 2. Chat with RAG

The chat endpoints automatically use RAG if available:

- `POST /chat-text` - Text input with RAG
- `POST /chat-voice` - Voice input with RAG

To disable RAG for a specific request:
```json
{
  "text": "your question",
  "use_rag": false
}
```

### 3. Manage Documents

- `POST /delete-document` - Delete a document
- `GET /vector-stats` - Get vector store statistics

## Architecture

- **VectorStore**: Pinecone integration for vector storage
- **EmbeddingService**: OpenAI embeddings (ada-002)
- **DocumentProcessor**: PDF/text extraction and chunking
- **RAGService**: Combines retrieval with GPT

## Reliability Features

- Graceful fallback if Pinecone is not configured
- Error handling and logging throughout
- Batch processing for embeddings
- Metadata filtering support
- Namespace support for multi-tenant scenarios

