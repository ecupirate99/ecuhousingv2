import os
from dotenv import load_dotenv
from llama_index.embeddings.google import GeminiEmbedding
from llama_index.core import Settings

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
print(f"Testing Gemini Embedding with key: {api_key[:10]}...")

try:
    embed_model = GeminiEmbedding(
        model_name="models/gemini-embedding-001",
        api_key=api_key
    )
    Settings.embed_model = embed_model
    
    text = "This is a test document to verify embedding works."
    embedding = embed_model.get_text_embedding(text)
    print(f"Success! Embedding length: {len(embedding)}")
except Exception as e:
    print(f"Embedding failed: {e}")
    import traceback
    traceback.print_exc()
