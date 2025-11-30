-- Media items for videos/social posts associated with a tool version or tool
CREATE TABLE IF NOT EXISTS media_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID NOT NULL REFERENCES tools(id) ON DELETE CASCADE,
    tool_version_id UUID, -- optional future link to tool_versions
    platform TEXT NOT NULL, -- youtube|tiktok|x|linkedin|other
    url TEXT NOT NULL,
    title TEXT,
    author TEXT,
    author_handle TEXT,
    is_influencer BOOLEAN NOT NULL DEFAULT FALSE,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb, -- views, likes, comments, shares
    published_at TIMESTAMPTZ,
    thumbnail_url TEXT,
    score REAL NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS media_items_tool_idx ON media_items(tool_id);
CREATE INDEX IF NOT EXISTS media_items_platform_idx ON media_items(platform);
CREATE UNIQUE INDEX IF NOT EXISTS media_items_unique ON media_items(tool_id, url);

