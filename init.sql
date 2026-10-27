CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS issues (
    issue_id BIGINT PRIMARY KEY,
    repo_name VARCHAR(255) NOT NULL,
    title TEXT NOT NULL,
    body_clean TEXT,
    author_association VARCHAR(50),
    labels TEXT[],
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    closed_at TIMESTAMP WITH TIME ZONE,
    state_reason VARCHAR(50),
    title_body_embedding VECTOR(384)
);