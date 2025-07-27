# Gemini Conversational AI Python Backend

This is the Python backend implementation for the Gemini Conversational AI project. It provides API endpoints that replicate the functionality of the original JavaScript API routes.

## Project Structure

```
python-backend/
├── requirements.txt
├── main.py
├── config.py
├── test_google_genai.py
├── api/
│   ├── __init__.py
│   ├── generate_text.py
│   ├── process_audio.py
│   └── full_conversation.py
└── utils/
    ├── __init__.py
    └── audio_utils.py
```

## Setup Instructions

1. **Navigate to the python-backend directory**:
   ```bash
   cd python-backend
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
   
   If you encounter issues with the above commands, please refer to our [Setup Troubleshooting Guide](setup-troubleshooting.md) for system-specific instructions.

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   Create a `.env` file in the `python-backend` directory with your Google API key:
   ```
   GOOGLE_API_KEY=your-google-api-key-here
   ```

5. **Run the server**:
   ```bash
   python main.py
   ```

The server will start on `http://localhost:8000`.

## Documentation

- [Getting Started Guide](getting-started.md) - Step-by-step setup instructions
- [Setup Troubleshooting Guide](setup-troubleshooting.md) - Solutions to common setup issues
- [Testing Guide](testing-guide.md) - Instructions for testing with the Next.js frontend
- [API Documentation](http://localhost:8000/docs) - Auto-generated API documentation (available when server is running)

## API Endpoints

### Text Generation
- **Endpoint**: `POST /api/generateText`
- **Description**: Generates text using the Gemini model based on a text prompt
- **Request Body**:
  ```json
  {
    "text": "string"
  }
  ```
- **Response**:
  ```json
  {
    "text": "string"
  }
  ```

### Image Processing
- **Endpoint**: `POST /api/processAudio`
- **Description**: Processes an image with a text prompt using the Gemini model and returns text with audio response
- **Request**: Multipart form data with:
  - `image`: Image file
  - `prompt`: Text prompt
- **Response**:
  ```json
  {
    "text": "string",
    "audio_base64": "string"
  }
  ```

### Full Conversation
- **Endpoint**: `POST /api/full-conversation`
- **Description**: Complete audio-to-audio pipeline
- **Request**: Multipart form data with:
  - `audio`: Audio file
- **Response**: Audio file (WAV format)

## Integration with Next.js Frontend

The Python backend runs on port 8000, while the Next.js frontend runs on port 3000. CORS is configured to allow requests from the Next.js frontend.

Make sure to update the API endpoint URLs in your Next.js frontend to point to `http://localhost:8000` instead of the original Node.js API.
