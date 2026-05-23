-- Conversations and messages for chat history persistence.
-- Apply this before running the app for the first time.

create table if not exists conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  title text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid references conversations(id) on delete cascade,
  role text not null,
  content text not null,
  citations jsonb,
  created_at timestamptz default now()
);
