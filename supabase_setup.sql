-- SQL to verify or create the table and vector extension
-- Run this in your Supabase SQL Editor

-- 1. Enable the pgvector extension to work with embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create the table if it doesn't exist (as specified by user)
-- Note: User mentioned vec_documents already exists, but here is the schema for verification
CREATE TABLE IF NOT EXISTS vec_documents (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  content text NOT NULL,
  metadata jsonb,
  embedding vector(3072) -- 3072 is the dimension for Google Gemini Embedding models
);

-- 3. Create an index for faster similarity search
-- Adjust 'lists' based on your data volume (default 100 is often fine for starters)
CREATE INDEX IF NOT EXISTS idx_vec_documents_embedding ON vec_documents 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 4. Verify the column names and types
-- SELECT column_name, data_type 
-- FROM information_schema.columns 
-- WHERE table_name = 'vec_documents';
