-- Aliases for entity resolution
CREATE TABLE IF NOT EXISTS tool_aliases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID NOT NULL REFERENCES tools(id) ON DELETE CASCADE,
    alias_value TEXT NOT NULL,
    alias_type TEXT NOT NULL, -- name|domain|twitter|linkedin|other
    confidence REAL NOT NULL DEFAULT 0.9,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS tool_aliases_value_idx ON tool_aliases(LOWER(alias_value));
CREATE INDEX IF NOT EXISTS tool_aliases_tool_idx ON tool_aliases(tool_id);



