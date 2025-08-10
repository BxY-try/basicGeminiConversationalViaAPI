-- Add user_id column to chat_sessions table
alter table public.chat_sessions
  add column user_id uuid references auth.users(id) on delete cascade;

-- Enable RLS for the tables
alter table public.chat_sessions enable row level security;
alter table public.chat_messages enable row level security;

-- Drop existing policies to recreate them
drop policy if exists "Users can manage their own chat sessions" on public.chat_sessions;
drop policy if exists "Users can manage messages in their own sessions" on public.chat_messages;

-- Create policy for chat_sessions: Users can only manage their own sessions
create policy "Users can manage their own chat sessions"
on public.chat_sessions
for all
using (auth.uid() = user_id and user_id is not null);

-- Create policy for chat_messages: Users can only manage messages in sessions they own
create policy "Users can manage messages in their own sessions"
on public.chat_messages
for all
using (
  exists (
    select 1
    from chat_sessions
    where chat_sessions.id = chat_messages.session_id
      and chat_sessions.user_id = auth.uid()
      and chat_sessions.user_id is not null
  )
);