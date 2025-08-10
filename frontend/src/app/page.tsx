'use client'

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from './chat/Sidebar';

export default function LandingPage() {
  const [inputText, setInputText] = useState('');
  const [image, setImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [transcription, setTranscription] = useState('');
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const router = useRouter();
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  const handleSuggestionClick = (type: string) => {
    let prompt = '';
    switch (type) {
      case 'cuaca':
        prompt = 'bagaimana ya cuaca saat ini di ____?';
        setInputText(prompt);
        break;
      case 'tanggal':
        prompt = 'hari ini tanggal berapa?';
        router.push(`/chat?q=${encodeURIComponent(prompt)}`);
        break;
      case 'berita':
        prompt = 'ada berita apa terkait ____ hari ini?';
        setInputText(prompt);
        break;
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

 const startRecording = async () => {
   try {
     const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
     const mediaRecorder = new MediaRecorder(stream);
     mediaRecorderRef.current = mediaRecorder;
     chunksRef.current = [];
     
     mediaRecorder.ondataavailable = (event) => chunksRef.current.push(event.data);

     mediaRecorder.onstop = () => {
       // The submission logic is now handled in stopRecording
     };

     mediaRecorder.start();
     setIsRecording(true);
     setTranscription(''); // Clear previous transcription

     const recognition = new (window as any).webkitSpeechRecognition();
     recognition.interimResults = true;
     recognition.continuous = true;
     recognition.lang = 'id-ID';

     recognition.onresult = (event: any) => {
       let interim_transcript = '';
       let final_transcript = '';
       for (let i = event.resultIndex; i < event.results.length; ++i) {
         const transcript_part = event.results[i][0].transcript;
         if (event.results[i].isFinal) {
           final_transcript += transcript_part;
         } else {
           interim_transcript += transcript_part;
         }
       }
       setTranscription(final_transcript + interim_transcript);
       
       if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
       silenceTimerRef.current = setTimeout(() => {
         // Use the final transcript from the event if available, otherwise use the state
         const transcriptToSubmit = final_transcript || transcription;
         stopRecording(false, transcriptToSubmit);
       }, 2000);
     };
     
     recognition.start();
     (mediaRecorderRef.current as any).recognition = recognition;

   } catch (error) {
     console.error('Microphone access denied:', error);
   }
 };

 const stopRecording = (cancel = false, finalTranscription?: string) => {
   if (mediaRecorderRef.current) {
     if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
     
     const recognition = (mediaRecorderRef.current as any).recognition;
     if (recognition) {
       recognition.stop();
     }

     if (mediaRecorderRef.current.state === "recording") {
        mediaRecorderRef.current.stop();
     }
     
     mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
     setIsRecording(false);

     if (cancel) {
       chunksRef.current = [];
       setTranscription('');
     } else if (finalTranscription && finalTranscription.trim()) {
        // Submit directly with the final transcription
        const syntheticEvent = { preventDefault: () => {} } as React.FormEvent;
        handleFormSubmit(syntheticEvent, finalTranscription);
     }
   }
 };

  const handleFormSubmit = (e: React.FormEvent, textOverride?: string) => {
    e.preventDefault();
    const textToSubmit = textOverride || inputText;

    if (!textToSubmit.trim() && !image) return;

    if (image) {
       const reader = new FileReader();
       reader.onload = (event) => {
           sessionStorage.setItem('initialImage', event.target?.result as string);
           sessionStorage.setItem('initialPrompt', textToSubmit);
           router.push(`/chat?initial=image`);
       };
       reader.readAsDataURL(image);
    } else {
       router.push(`/chat?q=${encodeURIComponent(textToSubmit)}`);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleFormSubmit(e as any);
    }
  };

  return (
    <div className="h-screen flex bg-white text-black">
      <Sidebar
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        onNewChat={() => router.push('/chat')}
        onLoadChat={(chatId) => router.push(`/chat?id=${chatId}`)}
        activeChatId={null}
      />
      <div className="flex-grow flex flex-col items-center justify-center h-full overflow-hidden relative">
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
        <div className="w-full max-w-2xl text-center">
          <div className="relative">
            <h1 className="text-6xl font-bold mb-4">Halo, saya Aria. Siap bantu!</h1>
        </div>
        <p className="text-gray-500 mb-8">
          Aku disini siap menemanimu ngobrol, latihan speaking, dan banyak lainnya..
        </p>
        <div className="bg-white rounded-xl shadow-lg p-6">
          <form onSubmit={handleFormSubmit}>
           {imagePreview && (
             <div className="p-2">
               <img src={imagePreview} alt="preview" className="max-h-24 rounded-lg mx-auto" />
             </div>
           )}
            <textarea
              ref={inputRef}
              value={isRecording ? (transcription || "Mendengarkan...") : inputText}
              onChange={(e) => { if (!isRecording) setInputText(e.target.value); }}
              placeholder="Tulis apapun yang sedang kamu pikirkan di sini..."
              className="w-full h-32 p-4 border border-gray-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-gray-300"
             onKeyDown={handleKeyDown}
            />
            <div className="flex items-center justify-between mt-4">
              <div className="flex gap-2">
                <button type="button" onClick={() => handleSuggestionClick('cuaca')} className="px-3 py-2 bg-gray-100 rounded-lg text-sm flex items-center gap-2">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi bi-brightness-high" viewBox="0 0 16 16">
                    <path d="M8 11a3 3 0 1 1 0-6 3 3 0 0 1 0 6m0 1a4 4 0 1 0 0-8 4 4 0 0 0 0 8M8 0a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2A.5.5 0 0 1 8 0m0 13a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2A.5.5 0 0 1 8 13m-5-5a.5.5 0 0 1 .5-.5h2a.5.5 0 0 1 0 1h-2a.5.5 0 0 1-.5-.5M11 8a.5.5 0 0 1 .5-.5h2a.5.5 0 0 1 0 1h-2a.5.5 0 0 1-.5-.5m-6.364 3.879a.5.5 0 0 1 .707 0l1.414-1.414a.5.5 0 1 1 .707.707l-1.414 1.414a.5.5 0 0 1-.707-.707zm9.193-9.193a.5.5 0 0 1 0 .707L12.364 5.05a.5.5 0 1 1-.707-.707l1.414-1.414a.5.5 0 0 1 .707 0zm-9.193 0a.5.5 0 0 1 .707 0l1.414 1.414a.5.5 0 1 1 .707-.707L3.636 2.95a.5.5 0 0 1 0-.707zm9.193 9.193a.5.5 0 0 1 0 .707l-1.414 1.414a.5.5 0 1 1-.707-.707l1.414-1.414a.5.5 0 0 1 .707 0z"/>
                  </svg>
                  Cek cuaca
                </button>
                <button type="button" onClick={() => handleSuggestionClick('tanggal')} className="px-3 py-2 bg-gray-100 rounded-lg text-sm flex items-center gap-2">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi bi-calendar-event" viewBox="0 0 16 16">
                    <path d="M11 6.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5z"/>
                    <path d="M3.5 0a.5.5 0 0 1 .5.5V1h8V.5a.5.5 0 0 1 1 0V1h1a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2h1V.5a.5.5 0 0 1 .5-.5M1 4v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V4z"/>
                  </svg>
                  Cek tanggal hari ini
                </button>
                <button type="button" onClick={() => handleSuggestionClick('berita')} className="px-3 py-2 bg-gray-100 rounded-lg text-sm flex items-center gap-2">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi bi-stars" viewBox="0 0 16 16">
                    <path d="M7.657 6.247a.5.5 0 0 1 .364.606l-1.522 4.245a.5.5 0 0 1-.948-.34l1.522-4.245a.5.5 0 0 1 .586-.266zM8.5 1a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2a.5.5 0 0 1 .5-.5m-4.243 1.757a.5.5 0 0 1 .707 0l1.414 1.414a.5.5 0 1 1-.707.707L3.557 3.464a.5.5 0 0 1 0-.707m8.486 0a.5.5 0 0 1 .707.707l-1.414 1.414a.5.5 0 1 1-.707-.707l1.414-1.414a.5.5 0 0 1 0 .707M2 8a.5.5 0 0 1 .5-.5h2a.5.5 0 0 1 0 1h-2A.5.5 0 0 1 2 8m11.5 0a.5.5 0 0 1 .5-.5h2a.5.5 0 0 1 0 1h-2a.5.5 0 0 1-.5-.5m-4.243 4.243a.5.5 0 0 1 .707 0l1.414 1.414a.5.5 0 1 1-.707-.707l-1.414-1.414a.5.5 0 0 1 0-.707m-4.243 0a.5.5 0 0 1 .707.707l-1.414 1.414a.5.5 0 1 1-.707-.707l1.414-1.414a.5.5 0 0 1 0 .707"/>
                  </svg>
                  Update berita
                </button>
              </div>
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
                <button
                  type="submit"
                  disabled={!inputText.trim() && !image && !isRecording}
                  className="px-5 py-3 bg-blue-500 text-white rounded-lg font-semibold flex items-center gap-2 disabled:bg-gray-400 hover:bg-blue-600"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi bi-send-fill" viewBox="0 0 16 16">
                    <path d="M15.964.686a.5.5 0 0 0-.65-.65L.767 5.855H.766l-.452.18a.5.5 0 0 0-.082.887l.41.26.001.002 4.995 3.178 3.178 4.995.002.002.26.41a.5.5 0 0 0 .886-.083zm-1.833 1.89L6.637 10.07l-4.995-3.178z"/>
                  </svg>
                  <span className="text-white">Kirim</span>
                </button>
              </div>
            </div>
          </form>
          {/*<p className="text-xs text-gray-500 mt-3 text-left">Shortcut hanya tampil di sini (landing). Di layar chat akan disembunyikan.</p>*/}
        </div>
      </div>
      </div>
    </div>
  );
}
