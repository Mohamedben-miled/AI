"""
Pinecone Vector Store Service
Handles vector storage and retrieval using Pinecone
"""
import os
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
import time

load_dotenv()

class VectorStore:
    def __init__(self):
        self.api_key = os.getenv('PINECONE_API_KEY')
        if not self.api_key:
            raise ValueError("PINECONE_API_KEY not found in environment variables")
        
        self.index_name = os.getenv('PINECONE_INDEX_NAME', 'ai-assistant-index')
        self.dimension = int(os.getenv('PINECONE_DIMENSION', '1536'))  # OpenAI ada-002 dimension
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=self.api_key)
        
        # Get or create index
        self._ensure_index()
        
        # Get index instance
        self.index = self.pc.Index(self.index_name)
    
    def _ensure_index(self):
        """Ensure the index exists, create if it doesn't"""
        try:
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]
            
            if self.index_name not in existing_indexes:
                print(f"[VECTOR_STORE] Creating index: {self.index_name}")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric='cosine',
                    spec=ServerlessSpec(
                        cloud='aws',
                        region=os.getenv('PINECONE_REGION', 'us-east-1')
                    )
                )
                # Wait for index to be ready
                print("[VECTOR_STORE] Waiting for index to be ready...")
                time.sleep(5)
                print(f"[VECTOR_STORE] Index {self.index_name} created successfully")
            else:
                print(f"[VECTOR_STORE] Index {self.index_name} already exists")
        except Exception as e:
            print(f"[VECTOR_STORE] Error ensuring index: {str(e)}")
            raise
    
    def upsert(self, vectors, metadata_list=None, namespace=None):
        """
        Upsert vectors to Pinecone
        
        Args:
            vectors: List of tuples (id, vector) or list of dicts with 'id' and 'values'
            metadata_list: Optional list of metadata dicts
            namespace: Optional namespace string
        
        Returns:
            dict: Upsert response
        """
        try:
            # Format vectors for Pinecone
            formatted_vectors = []
            for i, vector_data in enumerate(vectors):
                if isinstance(vector_data, tuple):
                    vector_id, vector_values = vector_data
                    metadata = metadata_list[i] if metadata_list and i < len(metadata_list) else {}
                elif isinstance(vector_data, dict):
                    vector_id = vector_data['id']
                    vector_values = vector_data['values']
                    metadata = vector_data.get('metadata', {})
                else:
                    raise ValueError("Invalid vector format")
                
                # Pinecone metadata must be flat and contain only strings, numbers, booleans, or lists
                # Convert any nested structures to strings
                clean_metadata = {}
                for key, value in metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        clean_metadata[key] = value
                    elif isinstance(value, list):
                        # Lists are allowed if all items are strings/numbers
                        clean_metadata[key] = value
                    else:
                        clean_metadata[key] = str(value)
                
                formatted_vectors.append({
                    'id': str(vector_id),
                    'values': vector_values,
                    'metadata': clean_metadata
                })
            
            # Upsert in batches of 100 (Pinecone limit)
            batch_size = 100
            for i in range(0, len(formatted_vectors), batch_size):
                batch = formatted_vectors[i:i + batch_size]
                self.index.upsert(vectors=batch, namespace=namespace)
            
            print(f"[VECTOR_STORE] Upserted {len(formatted_vectors)} vectors")
            return {'success': True, 'count': len(formatted_vectors)}
            
        except Exception as e:
            print(f"[VECTOR_STORE] Error upserting vectors: {str(e)}")
            raise
    
    def query(self, query_vector, top_k=5, namespace=None, filter_dict=None, include_metadata=True):
        """
        Query similar vectors from Pinecone
        
        Args:
            query_vector: List of floats - the query embedding vector
            top_k: Number of results to return
            namespace: Optional namespace string
            filter_dict: Optional metadata filter dict
            include_metadata: Whether to include metadata in results
        
        Returns:
            dict: Query results with matches
        """
        try:
            results = self.index.query(
                vector=query_vector,
                top_k=top_k,
                namespace=namespace,
                filter=filter_dict,
                include_metadata=include_metadata
            )
            
            matches = results.get('matches', [])
            print(f"[VECTOR_STORE] Found {len(matches)} matches")
            
            return {
                'matches': matches,
                'count': len(matches)
            }
            
        except Exception as e:
            print(f"[VECTOR_STORE] Error querying vectors: {str(e)}")
            raise
    
    def delete(self, ids=None, filter_dict=None, namespace=None, delete_all=False):
        """
        Delete vectors from Pinecone
        
        Args:
            ids: List of vector IDs to delete
            filter_dict: Metadata filter to delete matching vectors
            namespace: Optional namespace
            delete_all: If True, delete all vectors (use with caution)
        
        Returns:
            dict: Delete response
        """
        try:
            if delete_all:
                self.index.delete(delete_all=True, namespace=namespace)
                print(f"[VECTOR_STORE] Deleted all vectors from namespace: {namespace or 'default'}")
            elif filter_dict:
                self.index.delete(filter=filter_dict, namespace=namespace)
                print(f"[VECTOR_STORE] Deleted vectors matching filter")
            elif ids:
                self.index.delete(ids=[str(id) for id in ids], namespace=namespace)
                print(f"[VECTOR_STORE] Deleted {len(ids)} vectors")
            else:
                raise ValueError("Must provide ids, filter_dict, or delete_all=True")
            
            return {'success': True}
            
        except Exception as e:
            print(f"[VECTOR_STORE] Error deleting vectors: {str(e)}")
            raise
    
    def get_stats(self, namespace=None):
        """
        Get index statistics
        
        Returns:
            dict: Index statistics
        """
        try:
            stats = self.index.describe_index_stats()
            return stats
        except Exception as e:
            print(f"[VECTOR_STORE] Error getting stats: {str(e)}")
            return None

