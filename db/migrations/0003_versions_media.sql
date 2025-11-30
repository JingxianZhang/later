-- Versioning and Media tables

-- tool_versions: versioned one_pagers per tool
CREATE TABLE IF NOT EXISTS tool_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID NOT NULL REFERENCES tools(id) ON DELETE CASCADE,
    version_no INT NOT NULL,
    is_latest BOOLEAN NOT NULL DEFAULT FALSE,
    base_version_id UUID REFERENCES tool_versions(id) ON DELETE SET NULL,
    one_pager JSONB NOT NULL DEFAULT '{}'::jsonb,
    diff_from_prev JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS tool_versions_unique ON tool_versions(tool_id, version_no);
CREATE INDEX IF NOT EXISTS tool_versions_latest_idx ON tool_versions(tool_id) WHERE is_latest = TRUE;

-- user_tool_versions: which version a user is linked to (single-user MVP ok; can be nullable)
CREATE TABLE IF NOT EXISTS user_tool_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    tool_version_id UUID NOT NULL REFERENCES tool_versions(id) ON DELETE CASCADE,
    linked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_viewed_at TIMESTAMPTZ
);

-- tool_version_documents: snapshot documents that informed a given version
CREATE TABLE IF NOT EXISTS tool_version_documents (
    tool_version_id UUID NOT NULL REFERENCES tool_versions(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    PRIMARY KEY(tool_version_id, document_id)
);

-- media_items: social/video highlights tied to a specific tool version
CREATE TABLE IF NOT EXISTS media_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_version_id UUID NOT NULL REFERENCES tool_versions(id) ON DELETE CASCADE,
    platform TEXT NOT NULL, -- youtube|tiktok|x|linkedin|other
    url TEXT NOT NULL,
    title TEXT,
    author TEXT,
    author_handle TEXT,
    is_influencer BOOLEAN NOT NULL DEFAULT FALSE,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb, -- {views,likes,comments,shares}
    published_at TIMESTAMPTZ,
    thumbnail_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS media_items_platform_idx ON media_items(platform);



