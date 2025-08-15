'use client'

import { useState, useRef, useEffect, Suspense } from 'react';
import ReactMarkdown from 'react-markdown';
import { supabase } from '../../utils/supabaseClient';
import { useRouter, useSearchParams } from 'next/navigation';
import Sidebar from './Sidebar';
import CallButton from '../components/CallButton';

// Utility to convert base64 to ArrayBuffer
function base64ToArrayBuffer(base64: string): ArrayBuffer {
  let cleanBase64 = base64.replace(/\s/g, '');
  while (cleanBase64.length % 4) cleanBase64 += '=';
  
  const binaryString = window.atob(cleanBase64);
  const len = binaryString.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes.buffer;
}

function ChatPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcription, setTranscription] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [inputText, setInputText] = useState('');
  const [image, setImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [chatHistory, setChatHistory] = useState<Array<{id: string, role: string, parts: Array<{text?: string; function_call?: any; function_response?: any}>, imageUrl?: string, audioUrl?: string, isAudioInput?: boolean}>>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [playingMessageId, setPlayingMessageId] = useState<string | null>(null);
  const [audioCache, setAudioCache] = useState<Record<string, string>>({});
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const initialQueryProcessed = useRef(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Function to create a new chat session (now only used for initial queries)
  const createNewChat = async (token: string) => {
    try {
      const response = await fetch('http://localhost:8000/api/chats', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (!response.ok) throw new Error('Failed to create new chat');
      const data = await response.json();
      setActiveChatId(data.id);
      setChatHistory([]);
      return data.id;
    } catch (error) {
      console.error("Failed to create new chat:", error);
      return null;
    }
  };

  useEffect(() => {
    document.body.classList.add('no-scroll');
    return () => {
      document.body.classList.remove('no-scroll');
    };
  }, []);

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.setAttribute('data-theme', 'light');
    }
  }, [isDarkMode]);

  useEffect(() => {
    const lastMessage = chatHistory[chatHistory.length - 1];
    if (lastMessage && lastMessage.role === 'model' && lastMessage.isAudioInput && audioCache[lastMessage.id] && playingMessageId !== lastMessage.id) {
      const audio = new Audio(audioCache[lastMessage.id]);
      setPlayingMessageId(lastMessage.id);
      audio.play();
      audio.onended = () => setPlayingMessageId(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chatHistory, audioCache]);

  useEffect(() => {
    const checkSession = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        router.replace('/login');
      } else {
       const initialQuery = searchParams.get('q');
       const initialAction = searchParams.get('initial');
       const chatId = searchParams.get('id');

       if (chatId) {
         loadChatSession(chatId);
       } else if (initialQuery && !initialQueryProcessed.current) {
         initialQueryProcessed.current = true;
         handleInitialQuery(initialQuery, session.access_token);
         router.replace('/chat', { scroll: false });
       } else if (initialAction === 'image' && !initialQueryProcessed.current) {
         initialQueryProcessed.current = true;
         const image = sessionStorage.getItem('initialImage');
         const prompt = sessionStorage.getItem('initialPrompt');
         if (image && prompt) {
           handleInitialImageQuery(prompt, image, session.access_token);
           sessionStorage.removeItem('initialImage');
           sessionStorage.removeItem('initialPrompt');
         }
         router.replace('/chat', { scroll: false });
       }
      }
    };
    checkSession();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  const handleInitialQuery = async (query: string, token: string) => {
    const newChatId = await createNewChat(token);
    if (newChatId) {
      await sendTextToServer(query, [], newChatId);
    }
 };

 const handleInitialImageQuery = async (prompt: string, imageBase64: string, token: string) => {
   const newChatId = await createNewChat(token);
   if (newChatId) {
     const byteString = atob(imageBase64.split(',')[1]);
     const mimeString = imageBase64.split(',')[0].split(':')[1].split(';')[0];
     const ab = new ArrayBuffer(byteString.length);
     const ia = new Uint8Array(ab);
     for (let i = 0; i < byteString.length; i++) {
       ia[i] = byteString.charCodeAt(i);
     }
     const blob = new Blob([ab], { type: mimeString });
     const file = new File([blob], "initial-image.jpg", { type: mimeString });

     const userMessage = { id: `user-${Date.now()}`, role: 'user', parts: [{ text: prompt }], imageUrl: imageBase64 };
     setChatHistory(prev => [...prev, userMessage]);

     const formData = new FormData();
     formData.append('image', file);
     formData.append('prompt', prompt);
     formData.append('history', JSON.stringify([]));
     formData.append('chat_id', newChatId);
     
     setIsLoading(true);
     try {
       const response = await fetch('http://localhost:8000/api/processImage', {
         method: 'POST',
         body: formData,
       });
       const data = await response.json();
       if (data.text) {
         const aiMessage = { id: `model-${Date.now()}`, role: 'model', parts: [{ text: data.text }] };
         setChatHistory(prev => [...prev, aiMessage]);
       }
     } catch (error) {
       console.error("Initial image processing error:", error);
     } finally {
       setIsLoading(false);
     }
   }
 };

  const handleNewChat = () => {
    router.push('/');
  };

  const loadChatSession = async (chatId: string) => {
    if (!chatId) {
      setActiveChatId(null);
      setChatHistory([]);
      return;
    }
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      const response = await fetch(`http://localhost:8000/api/chats/${chatId}`, {
        headers: { 'Authorization': `Bearer ${session.access_token}` },
      });
      const data = await response.json();
      setActiveChatId(data.session?.id ?? data.id);
      const formattedHistory = Array.isArray(data.messages) ? data.messages.map((msg: { role: string; content: string }, index: number) => ({
       id: `history-${index}`,
        role: msg.role,
        parts: [{ text: msg.content }],
      })) : [];
      setChatHistory(formattedHistory);
    } catch (error) {
      console.error("Failed to load chat session:", error);
      setChatHistory([]);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];
      
      mediaRecorder.ondataavailable = (event) => chunksRef.current.push(event.data);

     mediaRecorder.onstop = async () => {
       if (chunksRef.current.length === 0) {
         console.log("No audio data recorded, not sending.");
         return;
       }
       setIsTranscribing(true);
       const audioBlob = new Blob(chunksRef.current, { type: 'audio/wav' });
       const formData = new FormData();
       formData.append('audio', audioBlob, `recording.wav`);
       formData.append('history', JSON.stringify(chatHistory));
       if (activeChatId) formData.append('chat_id', activeChatId);
       formData.append('enable_tts', 'true');

       try {
         const response = await fetch('http://localhost:8000/api/full-conversation', {
           method: 'POST',
           body: formData,
         });
         const data = await response.json();
         
         const userMessage = { id: `user-${Date.now()}`, role: 'user', parts: [{ text: data.user_transcript }] };
         const aiMessage = { id: `model-${Date.now()}`, role: 'model', parts: [{ text: data.ai_response }], isAudioInput: true };
         setChatHistory(prev => [...prev, userMessage, aiMessage]);
         setTranscription('');

         if (data.audio_base64) {
           const audioBlob = new Blob([base64ToArrayBuffer(data.audio_base64)], { type: 'audio/wav' });
           const audioUrl = URL.createObjectURL(audioBlob);
           setAudioCache(prev => ({ ...prev, [aiMessage.id]: audioUrl }));
           // Autoplay is now handled by the new useEffect
         }
       } catch (error) {
         console.error('API Error:', error);
       } finally {
         setIsTranscribing(false);
       }
     };

      mediaRecorder.start();
     setIsRecording(true);
     setTranscription('...');

     const recognition = new (window as any).webkitSpeechRecognition();
     recognition.interimResults = true;
     recognition.continuous = true;
     recognition.lang = 'id-ID';

     recognition.onresult = (event: any) => {
       let interim_transcript = '';
       for (let i = event.resultIndex; i < event.results.length; ++i) {
         if (event.results[i].isFinal) {
           // Final transcript (not used here, handled by backend)
         } else {
           interim_transcript += event.results[i][0].transcript;
         }
       }
       setTranscription(interim_transcript);
       if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
       silenceTimerRef.current = setTimeout(() => {
         stopRecording();
       }, 2000);
     };
     
     recognition.start();
     
     (mediaRecorderRef.current as any).recognition = recognition;

   } catch (error) {
     console.error('Microphone access denied:', error);
   }
 };

  const stopRecording = (cancel = false) => {
   if (mediaRecorderRef.current) {
     if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
     
     const recognition = (mediaRecorderRef.current as any).recognition;
     if (recognition) {
       recognition.stop();
     }

     mediaRecorderRef.current.stop();
     mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
     setIsRecording(false);
     setTranscription('');
     if (cancel) {
       chunksRef.current = [];
     }
   }
 };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setImage(file);
      const reader = new FileReader();
      reader.onload = (e) => setImagePreview(e.target?.result as string);
      reader.readAsDataURL(file);
    }
  };

  const sendTextToServer = async (text: string, currentHistory: any[], chatId: string) => {
    setIsLoading(true);

    const userMessage = { id: `user-${Date.now()}`, role: 'user', parts: [{ text }] };
    const updatedHistory = [...currentHistory, userMessage];
    
    setChatHistory(updatedHistory);
    setInputText('');
    setImage(null);
    setImagePreview(null);

    try {
      const response = await fetch('http://localhost:8000/api/generateText', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, history: currentHistory, chat_id: chatId, enable_tts: false }),
      });
      const data = await response.json();
      
      if (data.text) {
        const aiMessage = { id: `model-${Date.now()}`, role: 'model', parts: [{ text: data.text }] };
        setChatHistory(prev => [...prev, aiMessage]);
        if (data.audio_base64) {
          const audioUrl = URL.createObjectURL(new Blob([base64ToArrayBuffer(data.audio_base64)], { type: 'audio/wav' }));
          setAudioCache(prev => ({ ...prev, [aiMessage.id]: audioUrl }));
          const audio = new Audio(audioUrl);
          setPlayingMessageId(aiMessage.id);
          audio.play();
          audio.onended = () => setPlayingMessageId(null);
        }
      }
    } catch (error) {
      console.error('API Error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() && !image) return;

    if (!activeChatId) {
      console.error("Tidak ada obrolan aktif. Mulai obrolan baru dari halaman utama.");
      return;
    }

    const userMessage: {id: string, role: string, parts: any[], imageUrl?: string} = { id: `user-${Date.now()}`, role: 'user', parts: [] };
    if (inputText.trim()) userMessage.parts.push({ text: inputText });
    if (imagePreview) userMessage.imageUrl = imagePreview;

    const textToSend = inputText;
    setInputText('');
    setImage(null);
    setImagePreview(null);

    if (image) {
      const formData = new FormData();
      formData.append('image', image);
      formData.append('prompt', inputText);
      formData.append('history', JSON.stringify(chatHistory));
      formData.append('chat_id', activeChatId);
      
      setIsLoading(true);
      try {
        const response = await fetch('http://localhost:8000/api/processImage', {
          method: 'POST',
          body: formData,
        });
        const data = await response.json();
        if (data.text) {
          const aiMessage = { id: `model-${Date.now()}`, role: 'model', parts: [{ text: data.text }] };
          setChatHistory(prev => [...prev, aiMessage]);
        }
      } catch (error) {
        console.error("Image processing error:", error);
      } finally {
        setIsLoading(false);
      }
    } else {
      if (activeChatId) {
        await sendTextToServer(textToSend, chatHistory, activeChatId);
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleFormSubmit(e as any);
    }
  };

  const handlePlayAudio = async (messageId: string, text: string) => {
    if (playingMessageId === messageId) {
      // Logic to stop audio could be added here if needed
      return;
    }

    if (audioCache[messageId]) {
      const audio = new Audio(audioCache[messageId]);
      setPlayingMessageId(messageId);
      audio.play();
      audio.onended = () => setPlayingMessageId(null);
      return;
    }

    try {
      const response = await fetch('http://localhost:8000/api/text-to-speech', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      if (!response.ok) throw new Error('Failed to fetch audio');
      const data = await response.json();
      
      const audioUrl = URL.createObjectURL(new Blob([base64ToArrayBuffer(data.audio_base64)], { type: 'audio/wav' }));
      setAudioCache(prev => ({ ...prev, [messageId]: audioUrl }));
      
      const audio = new Audio(audioUrl);
      setPlayingMessageId(messageId);
      audio.play();
      audio.onended = () => setPlayingMessageId(null);

    } catch (error) {
      console.error('Failed to play audio:', error);
    }
  };

  return (
    <div className="h-screen flex bg-white text-black">
      <Sidebar
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        onNewChat={handleNewChat}
        onLoadChat={loadChatSession}
        activeChatId={activeChatId}
      />

      {/* Main Chat Window */}
      <div className="flex-grow flex flex-col items-center h-full overflow-hidden relative">
        {isSidebarCollapsed && (
          <button
            onClick={() => setIsSidebarCollapsed(false)}
            className="absolute top-4 left-4 p-2 rounded-lg bg-gray-200 hover:bg-gray-300 z-10"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi bi-layout-sidebar-inset" viewBox="0 0 16 16">
              <path d="M16 2a2 2 0 0 0-2-2H2a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V2zM3 14V3h4v11H3z"/>
            </svg>
          </button>
        )}
        <div className="w-full max-w-3xl flex flex-col h-full">
          <div className="p-4 border-b border-gray-200 flex justify-between items-center">
            <h2 className="text-xl font-bold">Aria</h2>
          </div>
          <div className="flex-grow p-4 overflow-y-auto">
            {chatHistory.map((msg, index) => (
              <div key={msg.id} className={`flex mb-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`chat-bubble ${msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-model'} flex items-start gap-3 ${msg.role === 'user' ? 'ml-8' : ''}`}>
                  <div className="flex-grow">
                    {msg.imageUrl && <img src={msg.imageUrl} alt="upload" className="rounded-lg mb-2" />}
                    {msg.parts.map((part, i) => (
                      part.text ? <ReactMarkdown key={`part-${i}`}>{part.text}</ReactMarkdown> : null
                    ))}
                  </div>
                  {msg.role === 'model' && msg.parts.some(p => p.text) && (
                    <button onClick={() => handlePlayAudio(msg.id, msg.parts.find(p => p.text)?.text || '')} className="p-1 rounded-full hover:bg-gray-200 self-start">
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className={`bi bi-volume-up-fill ${playingMessageId === msg.id ? 'text-blue-500' : 'text-gray-400'}`} viewBox="0 0 16 16">
                        <path d="M11.536 14.01A8.47 8.47 0 0 0 14.026 8a8.47 8.47 0 0 0-2.49-6.01l-.708.707A7.48 7.48 0 0 1 13.025 8c0 2.071-.84 3.946-2.197 5.303z"/>
                        <path d="M10.121 12.596A6.48 6.48 0 0 0 12.025 8a6.48 6.48 0 0 0-1.904-4.596l-.707.707A5.48 5.48 0 0 1 11.025 8a5.48 5.48 0 0 1-1.61 3.89z"/>
                        <path d="M8.707 11.182A4.5 4.5 0 0 0 10.025 8a4.5 4.5 0 0 0-1.318-3.182L8 5.525A3.5 3.5 0 0 1 9.025 8 3.5 3.5 0 0 1 8 10.475zM6.717 3.55A.5.5 0 0 1 7 4v8a.5.5 0 0 1-.812.39L3.825 10.5H1.5A.5.5 0 0 1 1 10V6a.5.5 0 0 1 .5-.5h2.325l2.363-1.89a.5.5 0 0 1 .529-.06"/>
                      </svg>
                    </button>
                  )}
                </div>
              </div>
          ))}
           {isLoading && (
            <div className="flex justify-start mb-4">
              <div className="rounded-lg p-3 max-w-lg bg-gray-200 text-black">
                <div className="flex items-center">
                  <div className="dot-flashing"></div>
                </div>
              </div>
            </div>
          )}
          </div>
          <div className="p-4 border-t border-gray-200">
            <div className="bg-white rounded-xl shadow-md p-2 max-w-3xl mx-auto w-full">
              <form onSubmit={handleFormSubmit}>
                {imagePreview && (
                <div className="p-2">
                  <img src={imagePreview} alt="preview" className="max-h-24 rounded-lg" />
                </div>
              )}
              <textarea
                ref={inputRef}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Tulis pesan..."
                className="w-full p-2 border-none resize-none focus:outline-none"
                rows={1}
                onKeyDown={handleKeyDown}
              />
             <div className="flex items-center justify-between mt-2">
               <div className="flex items-center gap-2">
                 <label className="p-2 rounded-lg hover:bg-gray-100 cursor-pointer">
                   <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi bi-image" viewBox="0 0 16 16"><path d="M6.002 5.5a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0"/><path d="M2.002 1a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V3a2 2 0 0 0-2-2zm12 1a1 1 0 0 1 1 1v6.5l-3.777-1.947a.5.5 0 0 0-.577.093l-3.71 3.71-2.66-1.772a.5.5 0 0 0-.63.062L1.002 12V3a1 1 0 0 1 1-1z"/></svg>
                   <input type="file" className="hidden" accept="image/*" onChange={handleImageUpload} />
                 </label>
                 <button type="button" onClick={isRecording ? () => stopRecording(true) : startRecording} className={`p-2 rounded-lg ${isRecording ? 'bg-red-500 text-white' : 'hover:bg-gray-100'}`}>
                   {isRecording ? (
                     <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi bi-stop-fill" viewBox="0 0 16 16">
                       <path d="M5 3.5h6A1.5 1.5 0 0 1 12.5 5v6a1.5 1.5 0 0 1-1.5 1.5H5A1.5 1.5 0 0 1 3.5 11V5A1.5 1.5 0 0 1 5 3.5"/>
                     </svg>
                   ) : (
                     <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi bi-mic-fill" viewBox="0 0 16 16"><path d="M5 3a3 3 0 0 1 6 0v5a3 3 0 0 1-6 0z"/><path d="M3.5 6.5A.5.5 0 0 1 4 7v1a4 4 0 0 0 8 0V7a.5.5 0 0 1 1 0v1a5 5 0 0 1-4.5 4.975V15h3a.5.5 0 0 1 0 1h-7a.5.5 0 0 1 0-1h3v-2.025A5 5 0 0 1 3 8V7a.5.5 0 0 1 .5-.5"/></svg>
                   )}
                 </button>
                 {isRecording && (
                   <div className="text-sm text-gray-500 flex items-center">
                     <p className="mr-2">{transcription || "Mendengarkan..."}</p>
                     <button type="button" onClick={() => stopRecording(true)} className="p-1 rounded-full hover:bg-gray-200 text-xs">
                       Cancel
                     </button>
                   </div>
                 )}
                 {isTranscribing && <p className="text-sm text-red-500">Mengirim...</p>}
               </div>
               <CallButton />
                <button type="submit" disabled={isLoading || (!inputText.trim() && !image)} className="px-4 py-2 bg-blue-500 text-white rounded-lg font-semibold flex items-center gap-2 disabled:bg-gray-400 hover:bg-blue-600">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi bi-send-fill" viewBox="0 0 16 16"><path d="M15.964.686a.5.5 0 0 0-.65-.65L.767 5.855H.766l-.452.18a.5.5 0 0 0-.082.887l.41.26.001.002 4.995 3.178 3.178 4.995.002.002.26.41a.5.5 0 0 0 .886-.083zm-1.833 1.89L6.637 10.07l-4.995-3.178z"/></svg>
                  <span className="text-white">Kirim</span>
                </button>
              </div>
            </form>
          </div>
        </div>
        </div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <ChatPageContent />
    </Suspense>
  );
}
