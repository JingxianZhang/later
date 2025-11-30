-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Enums
DO $$ BEGIN
    CREATE TYPE tool_status AS ENUM ('pending_research', 'partially_verified', 'fully_verified', 'archived');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Tables
CREATE TABLE IF NOT EXISTS tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    canonical_url TEXT UNIQUE,
    one_pager JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding VECTOR(3072),
    category_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    watchlist BOOLEAN NOT NULL DEFAULT FALSE,
    status tool_status NOT NULL DEFAULT 'pending_research'
);

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID NOT NULL REFERENCES tools(id) ON DELETE CASCADE,
    source_url TEXT NOT NULL,
    chunk_index INT NOT NULL,
    chunk_hash TEXT,
    chunk_text TEXT NOT NULL,
    chunk_embedding VECTOR(3072),
    raw_content TEXT,
    last_crawled TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS documents_tool_source_chunk_idx ON documents(tool_id, source_url, chunk_index);

CREATE TABLE IF NOT EXISTS tool_updates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID NOT NULL REFERENCES tools(id) ON DELETE CASCADE,
    field_changed TEXT NOT NULL,
    new_value TEXT NOT NULL,
    citation_source TEXT,
    source_agent TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    tool_context_id UUID REFERENCES tools(id) ON DELETE SET NULL,
    transcript TEXT NOT NULL,
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type TEXT NOT NULL,
    tool_id UUID REFERENCES tools(id) ON DELETE SET NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'queued',
    run_at TIMESTAMPTZ,
    dedupe_key TEXT,
    attempts INT NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Vector index (create IVFFLAT when table is populated)
-- CREATE INDEX IF NOT EXISTS documents_chunk_embedding_ivfflat ON documents USING ivfflat (chunk_embedding vector_cosine_ops) WITH (lists = 100);

-- Similarity RPC: simple example using cosine distance; expects a query embedding computed client-side
CREATE OR REPLACE FUNCTION top_k_similar_documents(p_tool_id UUID, p_query TEXT, p_k INT)
RETURNS TABLE(source_url TEXT, chunk_text TEXT, chunk_embedding VECTOR(3072))
LANGUAGE SQL STABLE AS $$
    WITH q AS (
        SELECT
            embedding
        FROM tools
        WHERE id = p_tool_id
    ),
    c AS (
        SELECT d.source_url, d.chunk_text, d.chunk_embedding
        FROM documents d
        WHERE d.tool_id = p_tool_id AND d.chunk_embedding IS NOT NULL
        ORDER BY (d.chunk_embedding <#> (SELECT embedding FROM q LIMIT 1)) ASC
        LIMIT p_k
    )
    SELECT * FROM c;
$$;


