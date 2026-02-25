import os

# Vercel specific: tiktoken needs a writable cache directory
os.environ["TIKTOKEN_CACHE_DIR"] = "/tmp"

import json
import pypdf
import httpx
from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    Document,
    Settings,
)
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.llms.groq import Groq
from llama_index.core.embeddings import BaseEmbedding
from llama_index.vector_stores.postgres import PGVectorStore
from supabase import create_client, Client
import asyncio
from typing import List, Generator, Any

# Lightweight Custom Gemini Embedding to avoid heavy Google SDK dependencies
class LiteGeminiEmbedding(BaseEmbedding):
    _api_key: str = ""
    _model_name: str = "models/embedding-001"

    def __init__(self, api_key: str, model_name: str = "models/embedding-001", **kwargs: Any):
        super().__init__(**kwargs)
        self._api_key = api_key
        self._model_name = model_name

    def _get_query_embedding(self, query: str) -> List[float]:
        return self._get_text_embedding(query)

    async def _aget_query_embedding(self, query: str) -> List[float]:
        return await self._aget_text_embedding(query)

    def _get_text_embedding(self, text: str) -> List[float]:
        url = f"https://generativelanguage.googleapis.com/v1beta/{self._model_name}:embedContent?key={self._api_key}"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "model": self._model_name,
            "content": {"parts": [{"text": text}]}
        }
        with httpx.Client() as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()['embedding']['values']

    async def _aget_text_embedding(self, text: str) -> List[float]:
        url = f"https://generativelanguage.googleapis.com/v1beta/{self._model_name}:embedContent?key={self._api_key}"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "model": self._model_name,
            "content": {"parts": [{"text": text}]}
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=60.0)
            response.raise_for_status()
            return response.json()['embedding']['values']

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        # For simplicity in Lite version, embed one by one or batch if needed
        return [self._get_text_embedding(t) for t in texts]

class RAGEngine:
    def __init__(self):
        try:
            # Load environment variables
            self.supabase_url = os.getenv("SUPABASE_URL")
            self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
            self.google_api_key = os.getenv("GOOGLE_API_KEY")
            self.groq_api_key = os.getenv("GROQ_API_KEY")
            
            # Basic validation
            if not all([self.supabase_url, self.supabase_key, self.google_api_key, self.groq_api_key]):
                raise ValueError("Missing required environment variables.")

            # Initialize Supabase Client (for storage)
            self.supabase_client: Client = create_client(self.supabase_url, self.supabase_key)
            
            # Initialize LlamaIndex Settings
            self.setup_settings()
            
            # Initialize Vector Store
            db_url = os.getenv("SUPABASE_DB_URL") or self.get_postgres_url()
            self.vector_store = PGVectorStore(
                connection_string=db_url,
                table_name="vec_documents",
                embed_dim=768,
                text_column="content",
                metadata_column="metadata"
            )
            self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            
            # Load or initialize the index
            self.index = VectorStoreIndex.from_vector_store(
                vector_store=self.vector_store,
                storage_context=self.storage_context
            )
        except Exception as e:
            print(f"CRITICAL: RAGEngine init failed: {e}")
            raise e

    def get_postgres_url(self):
        project_ref = self.supabase_url.split("//")[1].split(".")[0]
        password = os.getenv("SUPABASE_DB_PASSWORD")
        return f"postgresql://postgres:{password}@db.{project_ref}.supabase.co:5432/postgres"

    def setup_settings(self):
        # LLM - Groq
        Settings.llm = Groq(model="llama-3.3-70b-versatile", api_key=self.groq_api_key)
        
        # Lightweight Embedding - Custom LiteGemini
        Settings.embed_model = LiteGeminiEmbedding(api_key=self.google_api_key)
        
        # Chunking Strategy
        Settings.node_parser = TokenTextSplitter(
            chunk_size=900,
            chunk_overlap=175
        )

    async def process_and_index_pdf(self, file_path: str, filename: str):
        print(f"Starting processing for {filename}...")
        reader = pypdf.PdfReader(file_path)
        documents = []
        
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            metadata = {
                "filename": filename,
                "page_number": page_num + 1,
                "total_pages": len(reader.pages)
            }
            documents.append(Document(text=text, metadata=metadata))
        
        # Upload to Supabase Storage
        try:
            with open(file_path, "rb") as f:
                self.supabase_client.storage.from_("ecu_handbooks").upload(filename, f, {"upsert": "true"})
        except Exception as e:
            print(f"Supabase Storage warning: {e}")

        # Indexing
        nodes = Settings.node_parser.get_nodes_from_documents(documents)
        batch_size = 10
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i + batch_size]
            self.index.insert_nodes(batch)
            if i + batch_size < len(nodes):
                await asyncio.sleep(2) # Prevent rate limits
        
        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store,
            storage_context=self.storage_context
        )

    async def chat_stream(self, query: str, model_name: str = "llama-3.3-70b-versatile"):
        if model_name != Settings.llm.model:
            Settings.llm = Groq(model=model_name, api_key=self.groq_api_key)
        
        query_engine = self.index.as_query_engine(
            streaming=True,
            similarity_top_k=5,
            system_prompt=(
                "You are the ECU Residence Hall Handbook Chatbot. "
                "You must provide answers based STRICTLY on the ECU Residence Hall Handbook provided in the context. "
                "If the answer is not available in the ECU Residence Hall Handbook, "
                "respond with: 'The answer is not available in the ECU Residence Hall Handbook.' "
                "Always include source citations in your response."
            )
        )
        
        response = await query_engine.aquery(query)
        async for text in response.response_gen:
            yield f"data: {json.dumps({'text': text})}\n\n"
        
        citations = []
        for node in response.source_nodes:
            m = node.metadata
            citations.append(f"(Source: {m.get('filename', 'Doc')}, Page {m.get('page_number', '?')})")
        
        if citations:
            yield f"data: {json.dumps({'text': '\n\n' + '\n'.join(list(set(citations))), 'done': True})}\n\n"
        else:
            yield f"data: {json.dumps({'text': '', 'done': True})}\n\n"
