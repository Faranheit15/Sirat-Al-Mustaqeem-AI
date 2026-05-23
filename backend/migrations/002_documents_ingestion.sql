-- Document ingestion pipeline: storage records, vector chunks, and job tracking.
-- Requires the pgvector extension. Apply after 001_conversations.sql.

create extension if not exists vector;

create table if not exists documents (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  file_path text,
  file_type text not null,
  file_size integer,
  language text,
  page_count integer,
  is_ocr boolean default false,
  status text not null default 'pending',
  chunk_count integer default 0,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  metadata jsonb
);

create table if not exists document_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid references documents(id) on delete cascade,
  chunk_index integer not null,
  content text not null,
  embedding vector(768),
  doc_type text,
  language text,
  metadata jsonb,
  created_at timestamptz default now()
);

create index if not exists document_chunks_embedding_idx
  on document_chunks using ivfflat (embedding vector_cosine_ops);

create table if not exists ingestion_jobs (
  id uuid primary key default gen_random_uuid(),
  document_id uuid references documents(id) on delete cascade,
  status text not null default 'pending',
  progress integer default 0,
  error_log text,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz default now()
);
