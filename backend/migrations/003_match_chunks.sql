-- Semantic similarity search over document_chunks.
-- Apply after 002_documents_ingestion.sql.
-- Uses pgvector cosine distance. Returns only chunks from fully-ingested documents.

create or replace function match_chunks(
  query_embedding vector(768),
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
