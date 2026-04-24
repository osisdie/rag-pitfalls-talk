-- Demo schema. Runs once on first postgres container boot.

CREATE TABLE IF NOT EXISTS chat_sessions (
    id          TEXT PRIMARY KEY,
    scenario_id TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role        TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content     TEXT NOT NULL,
    citations   JSONB NOT NULL DEFAULT '[]'::jsonb,
    confidence  REAL NOT NULL DEFAULT 0.0,
    handoff     BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id, created_at);

CREATE TABLE IF NOT EXISTS rag_versions (
    id          SERIAL PRIMARY KEY,
    scenario_id TEXT,
    author      TEXT NOT NULL,
    label       TEXT NOT NULL,
    source      TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_versions_scenario ON rag_versions(scenario_id, id DESC);

-- Handoff queue (used by pit_12). Kept lightweight — no distinct table
-- for the demo; insertion pattern documented in scenario pit_12.
CREATE TABLE IF NOT EXISTS handoff_queue (
    id          SERIAL PRIMARY KEY,
    session_id  TEXT,
    question    TEXT NOT NULL,
    reason      TEXT NOT NULL,
    confidence  REAL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved    BOOLEAN NOT NULL DEFAULT false
);
