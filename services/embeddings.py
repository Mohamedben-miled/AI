"""
OpenAI Embeddings Service
Handles text embedding generation using OpenAI
"""
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class EmbeddingService:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = "text-embedding-ada-002"  # Reliable, cost-effective model
        self.dimension = 1536  # ada-002 dimension
    
    def embed(self, text):
        """
        Generate embedding for a single text
        
        Args:
            text: str - Text to embed
            
        Returns:
            list: Embedding vector (list of floats)
        """
        try:
            if not text or not text.strip():
                raise ValueError("Text cannot be empty")
            
            response = self.client.embeddings.create(
                model=self.model,
                input=text.strip()
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            print(f"[EMBEDDINGS] Error embedding text: {str(e)}")
            raise
    
    def embed_batch(self, texts, batch_size=100):
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of strings to embed
            batch_size: Number of texts to process per batch (OpenAI limit is 2048)
            
        Returns:
            list: List of embedding vectors
        """
        try:
            if not texts:
                return []
            
            all_embeddings = []
            
            # Process in batches
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                # Filter out empty texts
                valid_batch = [text.strip() for text in batch if text and text.strip()]
                
                if not valid_batch:
                    continue
                
                response = self.client.embeddings.create(
                    model=self.model,
                    input=valid_batch
                )
                
                # Map embeddings back to original order (handling empty texts)
                batch_embeddings = [None] * len(batch)
                valid_idx = 0
                for j, text in enumerate(batch):
                    if text and text.strip():
                        batch_embeddings[j] = response.data[valid_idx].embedding
                        valid_idx += 1
                
                all_embeddings.extend(batch_embeddings)
            
            print(f"[EMBEDDINGS] Generated {len([e for e in all_embeddings if e])} embeddings from {len(texts)} texts")
            return all_embeddings
            
        except Exception as e:
            print(f"[EMBEDDINGS] Error embedding batch: {str(e)}")
            raise

