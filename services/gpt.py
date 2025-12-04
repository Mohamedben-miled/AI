"""
OpenAI GPT Service
"""
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class GPTService:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = OpenAI(api_key=self.api_key, timeout=30.0)  # 30 second timeout
        self.model = "gpt-4o"  # Using GPT-4o as requested
    
    def chat(self, user_message, conversation_history=None):
        """
        Send message to GPT and get response
        
        Args:
            user_message: str - User's message/text
            conversation_history: List[Dict] - Previous messages in format [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
            
        Returns:
            str: GPT's response
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful, friendly, and conversational AI assistant. Keep responses concise and natural, as if speaking."
                }
            ]
            
            # Add conversation history if provided
            if conversation_history:
                messages.extend(conversation_history)
            
            # Add current user message
            messages.append({
                "role": "user",
                "content": user_message
            })
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"GPT Error: {str(e)}")
            return None

