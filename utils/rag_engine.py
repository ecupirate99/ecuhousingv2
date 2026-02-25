import os
import json
import fitz  # PyMuPDF
from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    Document,
    Settings,
)
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.llms.groq import Groq
from llama_index.embeddings.google import GeminiEmbedding
from llama_index.vector_stores.supabase import SupabaseVectorStore
from supabase import create_client, Client
import asyncio
from typing import List, Generator

class RAGEngine:
    def __init__(self):
        try:
            # Load environment variables
            self.supabase_url = os.getenv("SUPABASE_URL")
            self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
            self.google_api_key = os.getenv("GOOGLE_API_KEY")
            self.groq_api_key = os.getenv("GROQ_API_KEY")
            
            # Initialize Supabase Client (for storage and direct queries)
            self.supabase_client: Client = create_client(self.supabase_url, self.supabase_key)
            
            # Initialize LlamaIndex Settings
            self.setup_settings()
            
            # Initialize Vector Store
            self.vector_store = SupabaseVectorStore(
                postgres_connection_string=self.get_postgres_url(),
                collection_name="vec_documents"
            )
            self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            
            # Load or initialize the index
            self.index = VectorStoreIndex.from_vector_store(
                vector_store=self.vector_store,
                storage_context=self.storage_context
            )
        except Exception as e:
            print(f"CRITICAL: RAGEngine init failed: {e}")
            import traceback
            traceback.print_exc()
            raise e

    def get_postgres_url(self):
        # Use the direct DB URL if provided in .env (recommended for Supabase Pooler)
        db_url = os.getenv("SUPABASE_DB_URL")
        if db_url:
            return db_url
            
        # Fallback to constructing it from parts
        project_ref = self.supabase_url.split("//")[1].split(".")[0]
        password = os.getenv("SUPABASE_DB_PASSWORD")
        return f"postgresql://postgres:{password}@db.{project_ref}.supabase.co:5432/postgres"

    def setup_settings(self):
        # LLM - Groq
        Settings.llm = Groq(model="llama-3.3-70b-versatile", api_key=self.groq_api_key)
        
        # Embedding - Gemini
        Settings.embed_model = GeminiEmbedding(
            model_name="models/gemini-embedding-001",
            api_key=self.google_api_key
        )
        
        # Chunking Strategy
        Settings.node_parser = TokenTextSplitter(
            chunk_size=900,  # 800-1000 range
            chunk_overlap=175  # 150-200 range
        )

    async def process_and_index_pdf(self, file_path: str, filename: str):
        print(f"Starting processing for {filename}...")
        # 1. Parse PDF with PyMuPDF
        doc = fitz.open(file_path)
        documents = []
        
        for page_num, page in enumerate(doc):
            text = page.get_text()
            # Create a Document for each page to preserve page metadata
            metadata = {
                "filename": filename,
                "page_number": page_num + 1,
                "total_pages": len(doc)
            }
            documents.append(Document(text=text, metadata=metadata))
        doc.close()
        print(f"Parsed {len(documents)} pages.")
        
        # 2. Upload to Supabase Storage (Optional but requested: "Store file in Supabase Storage")
        try:
            print("Uploading to Supabase Storage...")
            with open(file_path, "rb") as f:
                self.supabase_client.storage.from_("ecu_handbooks").upload(filename, f, {"upsert": "true"})
            print("Upload successful.")
        except Exception as e:
            print(f"Supabase Storage warning: {e}")
            print("Indexing will continue anyway.")
            # We don't raise here so indexing can still proceed

        # 3. Create Nodes and Insert into Vector DB
        # This uses the Settings.node_parser and Settings.embed_model automatically
        print("Inserting nodes into Vector DB (this involves embedding)...")
        try:
            nodes = Settings.node_parser.get_nodes_from_documents(documents)
            print(f"Generated {len(nodes)} nodes. Inserting in batches to avoid API quota limits...")
            
            # Insert in small batches with delays to avoid 429 ResourceExhausted errors
            batch_size = 5
            for i in range(0, len(nodes), batch_size):
                batch = nodes[i:i + batch_size]
                self.index.insert_nodes(batch)
                print(f"Successfully indexed nodes {i+1} to {min(i + batch_size, len(nodes))}")
                
                if i + batch_size < len(nodes):
                    # Adaptive delay: shorter for small batches, longer if we're deeper in
                    await asyncio.sleep(4) 
                    
            print("All nodes inserted successfully.")
        except Exception as e:
            print(f"Vector DB insertion error: {e}")
            raise e
        
        # Re-initialize the index to ensure it picks up new nodes (or use from_vector_store)
        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store,
            storage_context=self.storage_context
        )
        print("Index re-initialized.")

    async def chat_stream(self, query: str, model_name: str = "llama-3.3-70b-versatile"):
        # Update LLM if model changed
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
                "Do not hallucinate or use outside knowledge. "
                "Always include source citations in your response."
            )
        )
        
        response = query_engine.query(query)
        
        # Prepare Citations
        citations = []
        for node in response.source_nodes:
            metadata = node.metadata
            filename = metadata.get("filename", "Unknown")
            page = metadata.get("page_number", "unknown")
            citation = f"(Source: {filename}, Page {page})"
            if citation not in citations:
                citations.append(citation)
        
        # Stream the response
        for text in response.response_gen:
            yield f"data: {json.dumps({'text': text})}\n\n"
        
        # Send citations at the end
        citation_text = "\n\n" + "\n".join(citations)
        yield f"data: {json.dumps({'text': citation_text, 'done': True})}\n\n"
