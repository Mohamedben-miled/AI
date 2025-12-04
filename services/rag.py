"""
RAG (Retrieval Augmented Generation) Service
Combines vector retrieval with GPT for context-aware responses
"""
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

from services.vector_store import VectorStore
from services.embeddings import EmbeddingService
from services.gpt import GPTService

class RAGService:
    def __init__(self):
        """Initialize RAG service with all required components"""
        print("[RAG] Initializing RAG service...")
        
        self.vector_store = VectorStore()
        self.embedding_service = EmbeddingService()
        self.gpt_service = GPTService()
        
        # RAG configuration
        self.top_k = int(os.getenv('RAG_TOP_K', '5'))  # Number of chunks to retrieve
        self.context_window = int(os.getenv('RAG_CONTEXT_WINDOW', '2000'))  # Max context chars
        
        print("[RAG] RAG service initialized")
    
    def add_documents(self, chunks: List[Dict], namespace: Optional[str] = None):
        """
        Add document chunks to vector store
        
        Args:
            chunks: List of chunk dicts with 'id', 'text', and 'metadata'
            namespace: Optional namespace for organization
        
        Returns:
            dict: Result with success status and count
        """
        try:
            if not chunks:
                return {'success': False, 'error': 'No chunks provided'}
            
            # Generate embeddings for all chunks
            texts = [chunk['text'] for chunk in chunks]
            print(f"[RAG] Generating embeddings for {len(texts)} chunks...")
            embeddings = self.embedding_service.embed_batch(texts)
            
            # Prepare vectors for upsert
            vectors = []
            metadata_list = []
            
            for i, chunk in enumerate(chunks):
                if embeddings[i] is not None:
                    # Store text in metadata for retrieval
                    chunk_metadata = chunk.get('metadata', {}).copy()
                    chunk_metadata['text'] = chunk['text']  # Store text for retrieval
                    
                    vectors.append((chunk['id'], embeddings[i]))
                    metadata_list.append(chunk_metadata)
            
            # Upsert to vector store
            result = self.vector_store.upsert(vectors, metadata_list, namespace)
            
            print(f"[RAG] Added {result['count']} chunks to vector store")
            return result
            
        except Exception as e:
            print(f"[RAG] Error adding documents: {str(e)}")
            raise
    
    def retrieve_context(self, query: str, top_k: Optional[int] = None, namespace: Optional[str] = None, filter_dict: Optional[Dict] = None):
        """
        Retrieve relevant context for a query
        
        Args:
            query: User query string
            top_k: Number of chunks to retrieve (defaults to self.top_k)
            namespace: Optional namespace
            filter_dict: Optional metadata filter
        
        Returns:
            List[Dict]: List of relevant chunks with metadata
        """
        try:
            if not query or not query.strip():
                return []
            
            top_k = top_k or self.top_k
            
            # Generate query embedding
            query_embedding = self.embedding_service.embed(query)
            
            # Query vector store
            results = self.vector_store.query(
                query_vector=query_embedding,
                top_k=top_k,
                namespace=namespace,
                filter_dict=filter_dict,
                include_metadata=True
            )
            
            # Format results
            context_chunks = []
            for match in results['matches']:
                # Get metadata - Pinecone returns it as a dict
                if hasattr(match, 'metadata'):
                    metadata = match.metadata if isinstance(match.metadata, dict) else {}
                else:
                    metadata = {}
                
                # Get text from metadata (we store it there)
                text = metadata.get('text', '')
                
                # Get score
                score = match.score if hasattr(match, 'score') else 0.0
                
                context_chunks.append({
                    'text': text,
                    'score': score,
                    'metadata': metadata
                })
            
            print(f"[RAG] Retrieved {len(context_chunks)} context chunks")
            return context_chunks
            
        except Exception as e:
            print(f"[RAG] Error retrieving context: {str(e)}")
            return []
    
    def build_context_prompt(self, context_chunks: List[Dict], query: str) -> str:
        """
        Build prompt with retrieved context
        
        Args:
            context_chunks: List of context chunks
            query: User query
        
        Returns:
            str: Formatted prompt with context
        """
        if not context_chunks:
            return query
        
        # Build context section
        context_text = "\n\n---\n\n".join([
            f"Context {i+1}:\n{chunk['text']}"
            for i, chunk in enumerate(context_chunks)
        ])
        
        # Limit context size
        if len(context_text) > self.context_window:
            context_text = context_text[:self.context_window] + "..."
        
        # Build final prompt
        prompt = f"""Use the following context to answer the question. If the context doesn't contain relevant information, answer based on your general knowledge.

Context:
{context_text}

Question: {query}

Answer:"""
        
        return prompt
    
    def chat(self, user_message: str, use_rag: bool = True, namespace: Optional[str] = None, 
             filter_dict: Optional[Dict] = None, conversation_history: Optional[List[Dict]] = None):
        """
        Chat with RAG-enhanced GPT
        
        Args:
            user_message: User's message
            use_rag: Whether to use RAG (retrieve context before answering)
            namespace: Optional namespace for retrieval
            filter_dict: Optional metadata filter for retrieval
            conversation_history: Optional conversation history
        
        Returns:
            str: GPT response
        """
        try:
            if use_rag:
                # Retrieve relevant context
                context_chunks = self.retrieve_context(user_message, namespace=namespace, filter_dict=filter_dict)
                
                if context_chunks:
                    # Build prompt with context
                    prompt = self.build_context_prompt(context_chunks, user_message)
                    print(f"[RAG] Using RAG with {len(context_chunks)} context chunks")
                else:
                    # No context found, use direct query
                    prompt = user_message
                    print("[RAG] No context found, using direct query")
            else:
                # Direct query without RAG
                prompt = user_message
                print("[RAG] RAG disabled, using direct query")
            
            # Get GPT response with conversation history
            response = self.gpt_service.chat(prompt, conversation_history=conversation_history)
            return response
            
        except Exception as e:
            print(f"[RAG] Error in RAG chat: {str(e)}")
            # Fallback to direct GPT
            return self.gpt_service.chat(user_message, conversation_history=conversation_history)
    
    def delete_documents(self, document_id: str, namespace: Optional[str] = None):
        """
        Delete all chunks for a document
        
        Args:
            document_id: Document ID to delete
            namespace: Optional namespace
        
        Returns:
            dict: Delete result
        """
        try:
            filter_dict = {'document_id': document_id}
            result = self.vector_store.delete(filter_dict=filter_dict, namespace=namespace)
            print(f"[RAG] Deleted chunks for document: {document_id}")
            return result
        except Exception as e:
            print(f"[RAG] Error deleting documents: {str(e)}")
            raise

