-- Switch to 1536-dim vectors to support IVFFLAT index (limit 2000 dims)
-- Note: re-embed will be needed after this change

-- 1) Drop any existing vector indexes on documents
DROP INDEX IF EXISTS documents_chunk_embedding_ivfflat;

-- 2) Clear existing documents (old 3072-d embeddings are incompatible)
DELETE FROM documents;

-- 3) Alter vector column dimensions
ALTER TABLE documents
    ALTER COLUMN chunk_embedding TYPE vector(1536);

ALTER TABLE tools
    ALTER COLUMN embedding TYPE vector(1536);

-- 4) Create IVFFLAT index for faster similarity with cosine distance
--    (Run this after you have a reasonable number of rows; adjust lists as needed)
CREATE INDEX IF NOT EXISTS documents_chunk_embedding_ivfflat
ON documents USING ivfflat (chunk_embedding vector_cosine_ops) WITH (lists = 100);


