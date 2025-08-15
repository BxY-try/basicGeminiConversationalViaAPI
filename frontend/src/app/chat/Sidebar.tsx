'use client'

import { useState, useEffect } from 'react';
import { supabase } from '../../utils/supabaseClient';
import { useRouter } from 'next/navigation';

type ChatSession = {
  id: string;
  created_at: string;
  title: string;
};

type SidebarProps = {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  onNewChat: () => void;
  onLoadChat: (chatId: string) => void;
  activeChatId: string | null;
};

export default function Sidebar({ isCollapsed, onToggleCollapse, onNewChat, onLoadChat, activeChatId }: SidebarProps) {
  const router = useRouter();
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [renamingChatId, setRenamingChatId] = useState<string | null>(null);
  const [renamingText, setRenamingText] = useState('');

  useEffect(() => {
    const checkSession = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (session) {
        setUserEmail(session.user.email ?? null);
        fetchChatSessions(session.access_token);
      }
    };
    checkSession();
  }, []);

  const fetchChatSessions = async (token: string) => {
    try {
      const response = await fetch('http://localhost:8000/api/chats', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      const data = await response.json();
      setChatSessions(data);
    } catch (error) {
      console.error("Failed to fetch chat sessions:", error);
    }
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push('/login');
  };

  const handleDeleteChat = async (chatId: string) => {
    if (!confirm('Are you sure you want to delete this chat session?')) return;

    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        router.push('/login');
        return;
      }

      const response = await fetch(`http://localhost:8000/api/chats/${chatId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${session.access_token}` },
      });

      if (response.ok) {
        setChatSessions(prev => prev.filter(s => s.id !== chatId));
        if (activeChatId === chatId) {
          onLoadChat(''); // Reset active chat
        }
      } else {
        console.error('Failed to delete chat session');
      }
    } catch (error) {
      console.error('Error deleting chat session:', error);
    }
  };

  const handleRenameChat = async (chatId: string) => {
    if (!renamingText.trim()) {
      setRenamingChatId(null);
      return;
    }

    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        router.push('/login');
        return;
      }

      const response = await fetch(`http://localhost:8000/api/chats/${chatId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ title: renamingText }),
      });

      if (response.ok) {
        const { data: { session: currentSession } } = await supabase.auth.getSession();
        if (currentSession) {
          fetchChatSessions(currentSession.access_token);
        }
        setRenamingChatId(null);
        setRenamingText('');
      } else {
        console.error('Failed to rename chat session');
      }
    } catch (error) {
      console.error('Error renaming chat session:', error);
    }
  };

  return (
    <div className={`bg-gray-50 border-r border-gray-200 p-4 flex flex-col h-full transition-all duration-300 ${isCollapsed ? 'w-20' : 'w-80'}`}>
      <div className="flex items-center justify-between mb-4">
        {!isCollapsed && <h1 className="text-xl font-bold">Aria</h1>}
        <button onClick={onToggleCollapse} className="p-2 rounded-lg hover:bg-gray-200">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi bi-layout-sidebar-inset-reverse" viewBox="0 0 16 16">
            <path d="M16 2a2 2 0 0 0-2-2H2a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V2zm-5 11H2V3h9v10z"/>
          </svg>
        </button>
      </div>
      <button onClick={onNewChat} className={`w-full px-4 py-2 mb-4 bg-gray-200 text-black rounded-lg font-semibold flex items-center justify-center gap-2 ${isCollapsed ? 'px-2' : ''}`}>
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi bi-plus-lg" viewBox="0 0 16 16"><path fillRule="evenodd" d="M8 2a.5.5 0 0 1 .5.5v5h5a.5.5 0 0 1 0 1h-5v5a.5.5 0 0 1-1 0v-5h-5a.5.5 0 0 1 0-1h5v-5A.5.5 0 0 1 8 2"/></svg>
        {!isCollapsed && 'New chat'}
      </button>
      <div className="flex-grow overflow-y-auto pr-2">
        {chatSessions.length > 0 && <p className={`text-sm text-gray-500 mb-2 ${isCollapsed ? 'hidden' : ''}`}>Obrolan sebelumnya</p>}
        {chatSessions.map((session, index) => (
          <div key={`${session.id}-${index}`} className="group p-2 rounded-lg hover:bg-gray-200 flex justify-between items-center">
            {renamingChatId === session.id ? (
              <input
                type="text"
                value={renamingText}
                onChange={(e) => setRenamingText(e.target.value)}
                onBlur={() => handleRenameChat(session.id)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleRenameChat(session.id) }}
                className="font-medium text-sm text-gray-800 bg-white border border-gray-300 rounded px-1 flex-grow"
                autoFocus
              />
            ) : (
              <div className="flex-grow cursor-pointer" onClick={() => onLoadChat(session.id)}>
                <p className={`font-medium text-sm truncate text-gray-800 ${isCollapsed ? 'hidden' : ''}`}>{session.title || session.id}</p>
              </div>
            )}
            <div className={`items-center ${isCollapsed ? 'flex' : 'hidden group-hover:flex'}`}>
              <button onClick={() => { setRenamingChatId(session.id); setRenamingText(session.title || session.id); }} className="p-1 text-gray-500 hover:text-black">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" className="bi bi-pencil-square" viewBox="0 0 16 16">
                  <path d="M15.502 1.94a.5.5 0 0 1 0 .706L14.459 3.69l-2-2L13.502.646a.5.5 0 0 1 .707 0l1.293 1.293zm-1.75 2.456-2-2L4.939 9.21a.5.5 0 0 0-.121.196l-.805 2.414a.25.25 0 0 0 .316.316l2.414-.805a.5.5 0 0 0 .196-.12l6.813-6.814z"/>
                  <path fillRule="evenodd" d="M1 13.5A1.5 1.5 0 0 0 2.5 15h11a1.5 1.5 0 0 0 1.5-1.5v-6a.5.5 0 0 0-1 0v6a.5.5 0 0 1-.5.5h-11a.5.5 0 0 1-.5-.5v-11a.5.5 0 0 1 .5-.5H9a.5.5 0 0 0 0-1H2.5A1.5 1.5 0 0 0 1 2.5z"/>
                </svg>
              </button>
              <button onClick={() => handleDeleteChat(session.id)} className="p-1 text-gray-500 hover:text-red-500">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" className="bi bi-trash" viewBox="0 0 16 16">
                  <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0z"/>
                  <path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4zM2.5 3h11V2h-11z"/>
                </svg>
              </button>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-auto pt-4 border-t border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold">
            {userEmail ? userEmail.charAt(0).toUpperCase() : 'G'}
          </div>
          <span className={`text-sm font-medium truncate ${isCollapsed ? 'hidden' : ''}`}>{userEmail ?? 'guest@example.com'}</span>
        </div>
        <button onClick={handleLogout} className="p-2 rounded-full hover:bg-gray-200">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi bi-box-arrow-right" viewBox="0 0 16 16"><path fillRule="evenodd" d="M10 12.5a.5.5 0 0 1-.5.5h-8a.5.5 0 0 1-.5-.5v-9a.5.5 0 0 1 .5-.5h8a.5.5 0 0 1 .5.5v2.5a.5.5 0 0 0 1 0v-2.5a1.5 1.5 0 0 0-1.5-1.5h-8A1.5 1.5 0 0 0 0 4.5v9A1.5 1.5 0 0 0 1.5 15h8a1.5 1.5 0 0 0 1.5-1.5v-2.5a.5.5 0 0 0-1 0z"/><path fillRule="evenodd" d="M15.854 8.354a.5.5 0 0 0 0-.708l-3-3a.5.5 0 0 0-.708.708L14.293 7.5H5.5a.5.5 0 0 0 0 1h8.793l-2.147 2.146a.5.5 0 0 0 .708.708z"/></svg>
        </button>
      </div>
    </div>
  );
}