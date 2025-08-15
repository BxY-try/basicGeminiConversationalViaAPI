from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.generate_text import router as generate_text_router
from api.process_audio import router as process_image_router # Corrected router name
from api.full_conversation import router as full_conversation_router
from api.chat_history import router as chat_history_router
from api.conversation_ws import router as conversation_ws_router
import os

# Import config to ensure environment variables are loaded
from api import text_to_speech
import config

app = FastAPI(title="Gemini Conversational AI Python Backend", version="1.0.0")

# Add CORS middleware to allow requests from the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:8000"],  # Allow Next.js and FastAPI Docs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API routers
app.include_router(generate_text_router)
app.include_router(process_image_router) # Corrected router name
app.include_router(full_conversation_router)
app.include_router(chat_history_router)
app.include_router(text_to_speech.router)
app.include_router(conversation_ws_router)

@app.get("/")
async def root():
    return {"message": "Gemini Conversational AI Python Backend API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
