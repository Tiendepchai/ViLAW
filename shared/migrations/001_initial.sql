CREATE TABLE IF NOT EXISTS documents (
    id          TEXT PRIMARY KEY,
    chu_de      TEXT DEFAULT '',
    de_muc      TEXT DEFAULT '',
    so_dieu     TEXT DEFAULT '',
    tieu_de_dieu TEXT DEFAULT '',
    noi_dung    TEXT DEFAULT '',
    nguon       TEXT DEFAULT '',
    path_goc    TEXT DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chunks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id      TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL DEFAULT 0,
    text        TEXT NOT NULL,
    faiss_id    INTEGER UNIQUE,
    chunk_hash  TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_hash ON chunks(chunk_hash);

CREATE TABLE IF NOT EXISTS index_metadata (
    key   TEXT PRIMARY KEY,
    value TEXT
);

INSERT OR IGNORE INTO index_metadata (key, value) VALUES ('version', '1');
INSERT OR IGNORE INTO index_metadata (key, value) VALUES ('last_built_at', '');

CREATE TABLE IF NOT EXISTS conversations (
    id          TEXT PRIMARY KEY,
    title       TEXT DEFAULT 'New chat',
    created_at  INTEGER NOT NULL,
    updated_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content         TEXT NOT NULL,
    citations       TEXT DEFAULT '[]',
    created_at      INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
