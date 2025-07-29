import os
import json
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict

router = APIRouter()

CHAT_SESSIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "chat_sessions")
if not os.path.exists(CHAT_SESSIONS_DIR):
    os.makedirs(CHAT_SESSIONS_DIR)

class Chat(BaseModel):
    id: str
    history: List[Dict[str, str]]

class ChatCreationResponse(BaseModel):
    chat_id: str

@router.post("/api/chats", response_model=ChatCreationResponse)
async def create_chat_session():
    """
    Creates a new chat session and returns its unique ID.
    """
    chat_id = str(uuid.uuid4())
    file_path = os.path.join(CHAT_SESSIONS_DIR, f"{chat_id}.json")
    with open(file_path, "w") as f:
        json.dump({"history": []}, f)
    return ChatCreationResponse(chat_id=chat_id)

@router.get("/api/chats", response_model=List[str])
async def get_all_chat_sessions():
    """
    Returns a list of all chat session IDs.
    """
    files = os.listdir(CHAT_SESSIONS_DIR)
    return [f.replace(".json", "") for f in files if f.endswith(".json")]

@router.get("/api/chats/{chat_id}", response_model=Chat)
async def get_chat_session(chat_id: str):
    """
    Retrieves the history of a specific chat session.
    """
    file_path = os.path.join(CHAT_SESSIONS_DIR, f"{chat_id}.json")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Chat session not found")
    with open(file_path, "r") as f:
        data = json.load(f)
    return Chat(id=chat_id, history=data.get("history", []))

@router.delete("/api/chats/{chat_id}", status_code=204)
async def delete_chat_session(chat_id: str):
    """
    Deletes a specific chat session.
    """
    file_path = os.path.join(CHAT_SESSIONS_DIR, f"{chat_id}.json")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Chat session not found")
    os.remove(file_path)
    return {}

def save_message_to_history(chat_id: str, message: Dict):
    """
    Appends a message to a chat session's history file.
    """
    file_path = os.path.join(CHAT_SESSIONS_DIR, f"{chat_id}.json")
    if not os.path.exists(file_path):
        # If for some reason the file doesn't exist, create it.
        with open(file_path, "w") as f:
            json.dump({"history": [message]}, f, indent=2)
        return

    with open(file_path, "r+") as f:
        data = json.load(f)
        history = data.get("history", [])
        history.append(message)
        f.seek(0)
        json.dump({"history": history}, f, indent=2)
        f.truncate()