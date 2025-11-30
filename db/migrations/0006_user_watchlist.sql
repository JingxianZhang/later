-- Per-user watchlist table to support user-scoped auto-updates and version linking
CREATE TABLE IF NOT EXISTS user_watchlist (
    user_id UUID NOT NULL,
    tool_id UUID NOT NULL REFERENCES tools(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, tool_id)
);

CREATE INDEX IF NOT EXISTS user_watchlist_tool_idx ON user_watchlist(tool_id);


