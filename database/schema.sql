-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- Create chat sessions table
create table chat_sessions (
    id uuid primary key default uuid_generate_v4(),
    title text not null,
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now()
);

-- Create chat messages table
create table chat_messages (
    id uuid primary key default uuid_generate_v4(),
    session_id uuid references chat_sessions(id) on delete cascade,
    role text not null check (role in ('user', 'assistant', 'model')),
    content text not null,
    created_at timestamp with time zone default now()
);

-- Create indexes
create index idx_chat_messages_session_id on chat_messages(session_id);
create index idx_chat_sessions_created_at on chat_sessions(created_at);
