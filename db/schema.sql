CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS qa_records (
  id SERIAL PRIMARY KEY,
  question_id TEXT UNIQUE,
  title TEXT,
  question TEXT,
  best_answer TEXT,
  llm_answer TEXT,
  score REAL,
  times_seen INTEGER DEFAULT 1,
  first_seen TIMESTAMPTZ DEFAULT now(),
  last_seen TIMESTAMPTZ DEFAULT now(),
  metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_qa_question_id ON qa_records(question_id);

CREATE TABLE IF NOT EXISTS request_logs (
  id SERIAL PRIMARY KEY,
  qa_id INTEGER REFERENCES qa_records(id) ON DELETE SET NULL,
  question_id TEXT,
  served_from TEXT,   -- 'cache' o 'llm'
  latency_ms INTEGER,
  response_length INTEGER,
  created_at TIMESTAMPTZ DEFAULT now(),
  metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS staging_raw (
  raw_id SERIAL,
  question_id TEXT,
  title TEXT,
  question TEXT,
  best_answer TEXT
);
