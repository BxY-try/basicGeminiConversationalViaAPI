import os
import json
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from google.genai import types

router = APIRouter()

CHAT_SESSIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "chat_sessions")
if not os.path.exists(CHAT_SESSIONS_DIR):
    os.makedirs(CHAT_SESSIONS_DIR)

class Chat(BaseModel):
    id: str
    history: List[Dict[str, Any]] # Allow for more complex history objects

class ChatCreationResponse(BaseModel):
    chat_id: str

def convert_history_to_json(history: List[types.Content]) -> List[Dict[str, Any]]:
    """
    Converts a Google GenAI conversation history (list of types.Content)
    into a JSON-serializable list of dictionaries.
    """
    json_history = []
    for content in history:
        # Skip the initial system instructions, which are not part of the saved history
        if content.role == "user" and "You are a helpful AI assistant" in content.parts[0].text:
            continue
        if content.role == "model" and "Okay, I understand" in content.parts[0].text:
            continue

        part_json_list = []
        for part in content.parts:
            part_json = {}
            if hasattr(part, 'text') and part.text:
                part_json['text'] = part.text
            elif hasattr(part, 'function_call'):
                part_json['function_call'] = {
                    'name': part.function_call.name,
                    'args': dict(part.function_call.args)
                }
            elif hasattr(part, 'function_response'):
                 part_json['function_response'] = {
                    'name': part.function_response.name,
                    'response': part.function_response.response
                }
            if part_json:
                part_json_list.append(part_json)

        if part_json_list:
            json_history.append({
                "role": content.role, # Preserve the actual role (user, model, or tool)
                "parts": part_json_list
            })
    return json_history

def save_history(chat_id: str, history: List[types.Content]):
    """
    Saves the entire conversation history to a chat session's JSON file.
    This overwrites the previous history to ensure consistency.
    """
    file_path = os.path.join(CHAT_SESSIONS_DIR, f"{chat_id}.json")
    serializable_history = convert_history_to_json(history)

    with open(file_path, "w") as f:
        json.dump({"history": serializable_history}, f, indent=2)

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