-- Resize document_chunks.embedding from vector(768) to vector(384).
-- Required after switching from Gemini text-embedding-004 (768 dims)
-- to sentence-transformers all-MiniLM-L12-v2 (384 dims).
--
-- WARNING: this drops all existing chunk data because the column type changes.
-- Re-ingest all documents after running this migration.
--
-- Apply after 003_match_chunks.sql.

-- 1. Drop the old IVFFlat index (tied to the 768-dim column).
drop index if exists document_chunks_embedding_idx;

-- 2. Delete existing chunk rows — they were embedded with the old model
--    and are incompatible with the new 384-dim vectors.
delete from document_chunks;

-- 3. Change the column type to 384 dimensions.
alter table document_chunks
  alter column embedding type vector(384)
  using embedding::text::vector(384);

-- 4. Recreate the IVFFlat index for the new dimension.
--    lists=100 is a sensible default; tune upward for larger datasets.
create index if not exists document_chunks_embedding_idx
  on document_chunks
  using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

-- 5. Replace match_chunks with a version that expects vector(384).
create or replace function match_chunks(
  query_embedding vector(384),
  match_count     int     default 5,
  match_threshold float   default 0.7
)
returns table (
  chunk_id        uuid,
  document_id     uuid,
  document_title  text,
  chunk_index     int,
  content         text,
  doc_type        text,
  language        text,
  metadata        jsonb,
  similarity      float
)
language sql stable
as $$
  select
    dc.id                                       as chunk_id,
    dc.document_id,
    d.title                                     as document_title,
    dc.chunk_index,
    dc.content,
    dc.doc_type,
    dc.language,
    dc.metadata,
    1 - (dc.embedding <=> query_embedding)      as similarity
  from   document_chunks dc
  join   documents d on d.id = dc.document_id
  where  d.status = 'completed'
    and  1 - (dc.embedding <=> query_embedding) >= match_threshold
  order  by dc.embedding <=> query_embedding
  limit  match_count;
$$;
