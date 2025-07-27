# Gemini Conversational AI Frontend

This is the Next.js frontend for the Gemini Conversational AI application that interfaces with the Python backend.

## Setup and Installation

1. Ensure you have Node.js v18+ and npm installed
2. Make sure the Python backend is running (port 8000):
   ```bash
   cd python-backend
   uvicorn main:app --reload --port 8000
   ```
3. Install frontend dependencies:
   ```bash
   cd frontend
   npm install
   ```
4. Start the development server:
   ```bash
   npm run dev
   ```

## Usage

1. Access the application at `http://localhost:3000`
2. Click the "Start Recording" button to begin recording audio
3. Speak your query into the microphone
4. The application will:
   - Record your audio
   - Send it to the backend for processing
   - Play back the AI-generated audio response
5. Use the Image Analysis section to upload an image and provide a text prompt for analysis. The application will:
   - Process the image and text prompt
   - Generate a text response
   - Play back the AI-generated audio response

## Project Structure

```
frontend/
├── public/            # Static assets
├── src/
│   └── app/           # Next.js App Router
│       ├── layout.tsx # Main layout
│       └── page.tsx   # Main application page
├── package.json       # Dependencies
└── README.md          # This file
```

## Key Features

- Web Audio API for microphone access
- Real-time audio recording interface
- Integration with Python backend API
- Image analysis with text and audio responses
- Responsive UI with Tailwind CSS
- Loading states and error handling
- Audio playback of AI responses

## Requirements

- Modern browser with Web Audio API support
- Microphone access permission
- Python backend running on port 8000
