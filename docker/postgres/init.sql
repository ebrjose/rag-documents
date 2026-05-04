CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS documents (
    document_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename       TEXT NOT NULL,
    sha256         TEXT UNIQUE NOT NULL,
    status         TEXT NOT NULL CHECK (status IN (
                       'pending','processing','indexed','error','requires_ocr'
                   )),
    uploaded_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    page_count     INTEGER,
    chunk_count    INTEGER,
    storage_path   TEXT NOT NULL,
    error_message  TEXT
);

CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_sha256 ON documents(sha256);
