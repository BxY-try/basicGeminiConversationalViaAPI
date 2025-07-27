'use client'

import { useState, useRef } from 'react';

// Utility to convert base64 to ArrayBuffer
function base64ToArrayBuffer(base64: string): ArrayBuffer {
  // Clean up base64 string (remove whitespace, ensure proper padding)
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

export default function Home() {
  const [isRecording, setIsRecording] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [inputText, setInputText] = useState('');
  const [image, setImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [chatHistory, setChatHistory] = useState<Array<{role: string, content: string, audioUrl?: string, imageUrl?: string}>>([]);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const mimeTypeRef = useRef<string>('');

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];
      
      mimeTypeRef.current = mediaRecorder.mimeType;
      
      mediaRecorder.ondataavailable = (event) => {
        chunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        setIsLoading(true);
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/wav' });
        const formData = new FormData();
        formData.append('audio', audioBlob, `recording.wav`);

        try {
          const response = await fetch('http://localhost:8000/api/full-conversation', {
            method: 'POST',
            body: formData,
          });

          if (response.ok) {
            const audioData = await response.arrayBuffer();
            const audioBlob = new Blob([audioData], { type: 'audio/wav' });
            const url = URL.createObjectURL(audioBlob);
            setAudioUrl(url);
          } else {
            throw new Error('Backend processing failed');
          }
        } catch (error) {
          console.error('API Error:', error);
          alert('Failed to process audio. Please try again.');
        } finally {
          setIsLoading(false);
        }
      };

      mediaRecorder.start(1000);
      setIsRecording(true);
    } catch (error) {
      console.error('Microphone access denied:', error);
      alert('Please allow microphone access to use this feature');
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
    mediaRecorderRef.current?.stream.getTracks().forEach(track => track.stop());
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setImage(file);
      
      // Create preview
      const reader = new FileReader();
      reader.onload = (e) => {
        setImagePreview(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleImageSubmit = async () => {
    if (!image || !inputText.trim() || isLoading) return;

    try {
      setIsLoading(true);
      
      // Add user message with image to chat history
      const userMessage = { 
        role: 'user', 
        content: inputText,
        imageUrl: imagePreview || URL.createObjectURL(image)
      };
      setChatHistory(prev => [...prev, userMessage]);
      
      // Prepare form data
      const formData = new FormData();
      formData.append('image', image);
      formData.append('prompt', inputText);
      
      // Clear input
      setInputText('');
      setImagePreview(null);
      setImage(null);

      // Send to backend
      const response = await fetch('http://localhost:8000/api/processAudio', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        
        // Create audio URL from base64
        const audioBlob = new Blob([base64ToArrayBuffer(data.audio_base64)], { type: 'audio/wav' });
        const audioUrl = URL.createObjectURL(audioBlob);
        
        // Add AI response to chat history with audio
        setChatHistory(prev => [...prev, 
          { role: 'ai', content: data.text, audioUrl }
        ]);
      } else {
        throw new Error('Backend processing failed');
      }
    } catch (error) {
      console.error('API Error:', error);
      alert('Failed to process image and text. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleTextSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isLoading) return;

    try {
      setIsLoading(true);
      
      // Add user message to chat history
      const userMessage = { role: 'user', content: inputText };
      setChatHistory(prev => [...prev, userMessage]);
      
      // Clear input
      setInputText('');
      
      // Send to backend
      const response = await fetch('http://localhost:8000/api/generateText', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: inputText }),
      });

      if (response.ok) {
        const data = await response.json();
        
        // Create audio URL from base64
        const audioBlob = new Blob([base64ToArrayBuffer(data.audio_base64)], { type: 'audio/wav' });
        const audioUrl = URL.createObjectURL(audioBlob);
        
        // Add AI response to chat history with audio
        setChatHistory(prev => [...prev, 
          { role: 'ai', content: data.text, audioUrl }
        ]);
      } else {
        throw new Error('Backend processing failed');
      }
    } catch (error) {
      console.error('API Error:', error);
      alert('Failed to process text. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-md bg-white rounded-xl shadow-md p-6">
        <h1 className="text-2xl font-bold text-center mb-6 text-gray-800">
          Gemini Conversational AI
        </h1>
        
        <div className="mb-6 text-center">
          <p className="text-gray-600">
            {isRecording 
              ? 'Recording... Tap the button to stop' 
              : 'Tap the button below to start recording'}
          </p>
          {isLoading && (
            <p className="text-blue-500 mt-2">Processing your request...</p>
          )}
        </div>
        
        <button
          onClick={isRecording ? stopRecording : startRecording}
          disabled={isLoading}
          className={`
            w-full py-4 rounded-full font-semibold text-white transition-all
            ${isRecording 
              ? 'bg-red-500 hover:bg-red-600' 
              : 'bg-blue-500 hover:bg-blue-600'}
            ${isLoading && 'opacity-50 cursor-not-allowed'}
          `}
        >
          {isLoading ? (
            'Processing...'
          ) : isRecording ? (
            '● Stop Recording'
          ) : (
            '🎤 Start Recording'
          )}
        </button>
        
        {audioUrl && (
          <div className="mt-8">
            <h2 className="text-lg font-semibold mb-2 text-gray-700 text-center">
              AI Response
            </h2>
            <audio 
              src={audioUrl} 
              autoPlay 
              className="w-full h-12 rounded-lg"
            />
          </div>
        )}
        
        {/* Image Upload Section */}
        <div className="mt-8 pt-6 border-t border-gray-200">
          <h2 className="text-xl font-bold text-center mb-4 text-gray-800">
            Image Analysis
          </h2>
          
          <div className="flex items-center justify-center w-full">
            <label className={`
              flex flex-col items-center justify-center w-full h-32 border-2 border-gray-300 border-dashed rounded-lg cursor-pointer
              ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}
            `}>
              <div className="flex flex-col items-center justify-center pt-5 pb-6">
                <svg aria-hidden="true" className="w-10 h-10 mb-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
                </svg>
                <p className="mb-2 text-sm text-gray-500"><span className="font-semibold">Click to upload</span> or drag and drop</p>
                <p className="text-xs text-gray-500">PNG, JPG, GIF up to 10MB</p>
              </div>
              <input 
                type="file" 
                className="hidden" 
                accept="image/*"
                onChange={handleImageUpload}
                disabled={isLoading}
              />
            </label>
          </div>
          
          {imagePreview && (
            <div className="mt-4">
              <img 
                src={imagePreview} 
                alt="Preview" 
                className="max-h-60 mx-auto rounded-lg"
              />
            </div>
          )}
          
          <form onSubmit={(e) => { e.preventDefault(); handleImageSubmit(); }} className="mt-4 flex">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Describe what you see..."
              disabled={isLoading || !image}
              className={`flex-1 px-4 py-2 border border-gray-300 rounded-l-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                !image ? 'bg-gray-100' : ''
              }`}
            />
            <button
              type="submit"
              disabled={isLoading || !inputText.trim() || !image}
              className={`
                px-4 py-2 rounded-r-lg font-semibold text-white transition-all
                ${isLoading || !inputText.trim() || !image
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-purple-500 hover:bg-purple-600'}
              `}
            >
              Analyze
            </button>
          </form>
        </div>
        
        {/* Text Chat Section */}
        <div className="mt-8 pt-6 border-t border-gray-200">
          <h2 className="text-xl font-bold text-center mb-4 text-gray-800">
            Text Chat
          </h2>
          
          {/* Chat History */}
          <div className="mb-4 max-h-60 overflow-y-auto">
            {chatHistory.map((message, index) => (
              <div 
                key={index} 
                className={`mb-3 p-3 rounded-lg ${
                  message.role === 'user' 
                    ? 'bg-blue-100 text-blue-800 ml-4' 
                    : 'bg-gray-100 text-gray-800 mr-4'
                }`}
              >
                <strong>{message.role === 'user' ? 'You: ' : 'AI: '}</strong>
                {message.content}
                
                {message.imageUrl && (
                  <div className="mt-2">
                    <img 
                      src={message.imageUrl} 
                      alt="User uploaded" 
                      className="max-h-40 rounded"
                    />
                  </div>
                )}
                
                {message.audioUrl && (
                  <audio 
                    src={message.audioUrl} 
                    autoPlay 
                    className="w-full h-12 rounded-lg mt-2"
                  />
                )}
              </div>
            ))}
          </div>
          
          {/* Text Input Form */}
          <form onSubmit={handleTextSubmit} className="flex">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Type your message..."
              disabled={isLoading}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-l-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              disabled={isLoading || !inputText.trim()}
              className={`
                px-4 py-2 rounded-r-lg font-semibold text-white transition-all
                ${isLoading || !inputText.trim()
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-green-500 hover:bg-green-600'}
              `}
            >
              Send
            </button>
          </form>
        </div>
        
        <div className="mt-6 text-center text-sm text-gray-500">
          <p>Backend: Python FastAPI • Port 8000</p>
          <p>Frontend: Next.js • Port 3000</p>
        </div>
      </div>
    </div>
  );
}
