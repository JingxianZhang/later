-- Telegram linking tables

CREATE TABLE IF NOT EXISTS telegram_users (
    chat_id BIGINT PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    linked_user_id UUID,
    linked_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS user_link_tokens (
    token TEXT PRIMARY KEY,
    user_id UUID NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


