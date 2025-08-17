'use client';

import { useEffect, useState, useRef, useCallback } from 'react';

interface CallOverlayProps {
  onClose: () => void;
}

// Hook to manage the audio queue.
const useAudioQueue = (onAudioStart: (transcript: string) => void, onAudioEnd: () => void) => {
  const [audioQueue, setAudioQueue] = useState<{ audio: string; transcript: string }[]>([]);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Effect to initialize and clean up the audio element
  useEffect(() => {
    audioRef.current = new Audio();
    const currentAudioRef = audioRef.current;

    const handleAudioEnd = () => {
      setTimeout(() => {
        setIsPlaying(false);
        onAudioEnd();
        setAudioQueue(prev => prev.slice(1));
      }, 100);
    };

    currentAudioRef.addEventListener('ended', handleAudioEnd);

    return () => {
      currentAudioRef.removeEventListener('ended', handleAudioEnd);
      currentAudioRef.pause();
      currentAudioRef.src = '';
    };
  }, []);

  // Effect to play audio when the queue has items and we are not already playing
  useEffect(() => {
    if (audioQueue.length > 0 && !isPlaying) {
      setIsPlaying(true);
      const { audio, transcript } = audioQueue[0];
      onAudioStart(transcript);
      const nextAudioSrc = `data:audio/wav;base64,${audio}`;
      if (audioRef.current) {
        audioRef.current.src = nextAudioSrc;
        audioRef.current.play().catch(e => {
          console.error("Audio play failed:", e);
          setIsPlaying(false);
          onAudioEnd();
          setAudioQueue(prev => prev.slice(1));
        });
      }
    } else if (audioQueue.length === 0 && !isPlaying) {
      onAudioEnd();
    }
  }, [audioQueue, isPlaying, onAudioStart, onAudioEnd]);

  const addAudioToQueue = useCallback((audioBase64: string, transcript: string) => {
    setAudioQueue(prev => [...prev, { audio: audioBase64, transcript }]);
  }, []);

  const isIdle = audioQueue.length === 0 && !isPlaying;

  return { addAudioToQueue, isPlaying, isIdle };
};


const CallOverlay = ({ onClose }: CallOverlayProps) => {
  const [status, setStatus] = useState('connecting');
  const [isMuted, setIsMuted] = useState(false);
  const [userTranscript, setUserTranscript] = useState('');
  const [currentAiTranscript, setCurrentAiTranscript] = useState('');
  const [displayedTranscript, setDisplayedTranscript] = useState('');
  const [aiTurnEnded, setAiTurnEnded] = useState(true);
  const [recognitionLang, setRecognitionLang] = useState('id-ID'); // 'id-ID', 'ja-JP', or 'en-US'
  const [recognitionCycle, setRecognitionCycle] = useState(0);

  const onAudioStart = useCallback((transcript: string) => {
    setCurrentAiTranscript(transcript);
  }, []);

  const onAudioEnd = useCallback(() => {
    // The transcript is now cleared when the AI's turn ends, not after each chunk.
  }, []);

  const { addAudioToQueue, isPlaying: isAiSpeaking, isIdle: isAudioIdle } = useAudioQueue(onAudioStart, onAudioEnd);
  
  const recognitionRef = useRef<any>(null);
  const socketRef = useRef<WebSocket | null>(null);

  const stopRecognition = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
  }, []);

  const startRecognition = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.start();
      } catch (e) {
        // Ignore errors if it's already started
        if (e instanceof DOMException && e.name === 'InvalidStateError') {
          // This is fine, it means it's already running.
        } else {
          console.error("Could not start recognition service: ", e);
        }
      }
    }
  }, []);

  const sendTranscriptToServer = useCallback((transcript: string) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN && transcript) {
      console.log("Sending transcript:", transcript);
      setAiTurnEnded(false);
      socketRef.current.send(JSON.stringify({
        type: 'user_transcript',
        text: transcript,
        lang: recognitionLang.split('-')[0]
      }));
      setUserTranscript('');
    }
  }, [setAiTurnEnded, setUserTranscript, recognitionLang]);

  // Main State Machine Effect
  useEffect(() => {
    if (isAiSpeaking) {
      setStatus('speaking');
    } else if (aiTurnEnded && isAudioIdle) {
      setStatus('listening');
    } else if (status === 'initializing' && aiTurnEnded) {
      setStatus('listening');
    }
  }, [isAiSpeaking, aiTurnEnded, isAudioIdle, status]);

  // Speech Recognition Lifecycle Effect (Watchdog)
  useEffect(() => {
    if (status === 'listening' && !isMuted) {
      startRecognition();
    } else {
      stopRecognition();
    }
    // This effect is now also triggered by recognitionCycle, ensuring a restart if needed.
  }, [status, isMuted, recognitionCycle, startRecognition, stopRecognition, recognitionLang]);

  // WebSocket and SpeechRecognition Setup Effect
  useEffect(() => {
    const ws = new WebSocket(process.env.NEXT_PUBLIC_WEBSOCKET_URL || 'ws://localhost:8000/ws/conversation');
    socketRef.current = ws;

    ws.onopen = () => console.log('WebSocket Connected');
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'ai_audio_chunk' && data.audio_base64 && data.transcript) {
          addAudioToQueue(data.audio_base64, data.transcript);
        } else if (data.type === 'ai_turn_end') {
          setAiTurnEnded(true);
          setCurrentAiTranscript('');
          setDisplayedTranscript('');
        }
      } catch (error) {
        console.error('Error parsing socket message:', error);
      }
    };
    ws.onerror = (error) => console.error('WebSocket Error:', error);
    ws.onclose = () => console.log('WebSocket Disconnected');

    const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
    if (!SpeechRecognition) {
      setStatus('error');
      return;
    }
    recognitionRef.current = new SpeechRecognition();
    recognitionRef.current.continuous = true;
    recognitionRef.current.interimResults = true;
    recognitionRef.current.lang = recognitionLang;

    recognitionRef.current.onresult = (event: any) => {
      let final_transcript = '';
      let interim_transcript = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const transcript_part = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          final_transcript += transcript_part;
        } else {
          interim_transcript += transcript_part;
        }
      }
      setUserTranscript(interim_transcript);
      if (final_transcript.trim()) {
        sendTranscriptToServer(final_transcript.trim());
      }
    };

    recognitionRef.current.onerror = (event: any) => {
      console.error("SpeechRecognition error", event.error);
      if (event.error !== 'no-speech') {
        setStatus('error');
      }
    };

    // This is the core of the watchdog. It triggers a state update whenever recognition ends.
    recognitionRef.current.onend = () => {
      console.log("Speech recognition service ended.");
      setRecognitionCycle(c => c + 1);
    };

    navigator.mediaDevices.getUserMedia({ audio: true })
      .then(() => {
        console.log("Microphone access OK.");
        setStatus('listening');
      })
      .catch(err => {
        console.error('Microphone access error:', err);
        setStatus('error');
      });

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [addAudioToQueue, sendTranscriptToServer, recognitionLang]);

  // Effect for the typewriter animation
  useEffect(() => {
    if (currentAiTranscript && isAiSpeaking) {
      // Reset transcript immediately to prevent flashing old text
      setDisplayedTranscript('');

      // Use character-by-character for Japanese, word-by-word for others
      if (recognitionLang === 'ja-JP') {
        let index = 0;
        const interval = setInterval(() => {
          index++;
          setDisplayedTranscript(currentAiTranscript.slice(0, index));
          if (index >= currentAiTranscript.length) {
            clearInterval(interval);
          }
        }, 50); // Speed for characters
        return () => clearInterval(interval);
      } else {
        const words = currentAiTranscript.split(' ');
        let index = 0;
        const interval = setInterval(() => {
          index++;
          setDisplayedTranscript(words.slice(0, index).join(' '));
          if (index >= words.length) {
            clearInterval(interval);
          }
        }, 150); // Speed for words
        return () => clearInterval(interval);
      }
    }
  }, [currentAiTranscript, isAiSpeaking, recognitionLang]);

  const getStatusText = () => {
    switch (status) {
      case 'speaking':
        return "Aria sedang berbicara...";
      case 'listening':
        // Restore user transcript visibility
        return userTranscript ? `"${userTranscript}"` : "Mendengarkan...";
      case 'initializing':
        return "Menginisialisasi...";
      case 'error':
        return "Error: Cek izin mikrofon.";
      default:
        return "Menghubungkan...";
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-80 flex flex-col items-center justify-center z-50 text-white">
      {/* Add a higher z-index to the text container to ensure it's on top */}
      <div className="text-center relative z-10">
        <div className="relative w-48 h-48 mx-auto mb-8">
          <div className="absolute inset-0 rounded-full bg-white/10"></div>

          {status === 'speaking' && (
            <div className="absolute inset-0 rounded-full bg-gradient-to-r from-purple-500 via-pink-500 to-orange-500 animate-pulse"></div>
          )}

          {status === 'listening' && (
            <div className="absolute inset-0 flex items-center justify-center gap-2">
              <span className={`w-4 h-4 bg-white rounded-full ${isMuted ? '' : 'animate-bounce [animation-delay:-0.3s]'}`}></span>
              <span className={`w-4 h-4 bg-white rounded-full ${isMuted ? '' : 'animate-bounce [animation-delay:-0.15s]'}`}></span>
              <span className={`w-4 h-4 bg-white rounded-full ${isMuted ? '' : 'animate-bounce'}`}></span>
            </div>
          )}
           {(status === 'connecting' || status === 'initializing') && (
            <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-24 h-24 border-4 border-t-transparent border-white rounded-full animate-spin"></div>
            </div>
          )}
        </div>
        <p
          className="text-xl font-medium mt-4 h-8 flex items-center justify-center"
          style={{ color: 'white' }}
        >
          {getStatusText()}
        </p>
        <div
          className="text-base mt-2 h-16 overflow-y-auto px-4 text-center"
          style={{ minHeight: '4rem', color: '#CCCCCC' }}
        >
          {status === 'speaking' && displayedTranscript}
        </div>
      </div>

      <div className="absolute bottom-16 flex items-center gap-6">
        <button
          onClick={() => setRecognitionLang(prev => {
            if (prev === 'id-ID') return 'ja-JP';
            if (prev === 'ja-JP') return 'en-US';
            return 'id-ID';
          })}
          className="p-4 rounded-full bg-white/20 hover:bg-white/30 text-white transition-colors flex items-center justify-center w-16 h-16"
          aria-label="Switch Language"
        >
          <span className="text-lg font-bold">{recognitionLang.split('-')[0].toUpperCase()}</span>
        </button>

        <button
          onClick={() => setIsMuted(!isMuted)}
          className={`p-4 rounded-full ${isMuted ? 'bg-yellow-500 hover:bg-yellow-600' : 'bg-white/20 hover:bg-white/30'} text-white transition-colors`}
          aria-label={isMuted ? "Unmute" : "Mute"}
        >
          {isMuted ? (
            <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="1" y1="1" x2="23" y2="23"></line>
              <path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6"></path>
              <path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23"></path>
              <line x1="12" y1="19" x2="12" y2="23"></line>
              <line x1="8" y1="23" x2="16" y2="23"></line>
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
              <line x1="12" y1="19" x2="12" y2="23"></line>
              <line x1="8" y1="23" x2="16" y2="23"></line>
            </svg>
          )}
        </button>

        <button onClick={onClose} className="p-4 rounded-full bg-red-600 text-white hover:bg-red-700 transition-colors" aria-label="End Call">
          <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.63A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path>
            <line x1="23" y1="1" x2="17" y2="7"></line>
            <line x1="17" y1="1" x2="23" y2="7"></line>
          </svg>
        </button>
      </div>
    </div>
  );
};

export default CallOverlay;
