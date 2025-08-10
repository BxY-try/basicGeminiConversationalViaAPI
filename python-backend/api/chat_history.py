
import json
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from supabase import Client
from postgrest import APIError
from database import get_db_connection
from google.genai import types as genai_types
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

def insert_message(session_id: str, role: str, content: str, db: Client):
    """
    Insert a single chat message to Supabase for a given session.
    """
    if not session_id:
        logger.warning("No session_id provided. Message will not be saved.")
        return
    try:
        logger.info(f"Insert params: session_id={session_id}, role={role}, content={content}")
        response = db.table('chat_messages').insert({
            "session_id": session_id,
            "role": role,
            "content": content
        }).execute()
        logger.info(f"Supabase insert response: {response}")
        if hasattr(response, 'error') and response.error:
            logger.error(f"Supabase error: {response.error}")
        if hasattr(response, 'data') and response.data:
            logger.info(f"Inserted data: {response.data}")
        else:
            logger.warning(f"No data returned from Supabase insert for session {session_id}")
    except Exception as e:
        logger.error(f"Error inserting message for session {session_id}: {e}", exc_info=True)

router = APIRouter()
logger = logging.getLogger(__name__)

class ChatSession(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str

class ChatMessage(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    created_at: str

class ChatHistory(BaseModel):
    session: ChatSession
    messages: List[ChatMessage]

@router.post("/api/chats", response_model=ChatSession, status_code=201)
async def create_chat_session(
    authorization: Optional[str] = Header(None),
    db: Client = Depends(get_db_connection)
):
    """
    Creates a new chat session, associating it with the authenticated user.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    jwt_token = authorization.split("Bearer ")[1]

    try:
        # Get user from token
        user_response = db.auth.get_user(jwt_token)
        user = user_response.user
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token or user not found")

        # A default title is created, the user can change it later
        response = db.table('chat_sessions').insert({
            "title": "New Chat",
            "user_id": user.id
        }).execute()
        
        new_session = response.data[0]
        return new_session
    except APIError as e:
        logger.error(f"Supabase API Error in create_chat_session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        logger.error(f"Generic error in create_chat_session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/chats", response_model=List[str])
async def get_all_chat_sessions(db: Client = Depends(get_db_connection)):
    """
    Returns a list of all chat session IDs.
    """
    try:
        response = db.table('chat_sessions').select("id").order("created_at", desc=True).execute()
        data = response.data
        return [session['id'] for session in data]
    except APIError as e:
        logger.error(f"Supabase API Error in get_all_chat_sessions: {e}", exc_info=True)
        raise HTTPException(status_code=e.code, detail=e.message)
    except Exception as e:
        logger.error(f"Generic error in get_all_chat_sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

@router.get("/api/chats/{session_id}", response_model=ChatHistory)
async def get_chat_history(session_id: str, db: Client = Depends(get_db_connection)):
    """
    Retrieves a specific chat session and all its messages.
    """
    try:
        # Get session details
        session_res = db.table('chat_sessions').select("*").eq('id', session_id).single().execute()
        session_data = session_res.data

        # Get all messages for the session
        messages_res = db.table('chat_messages').select("*").eq('session_id', session_id).order("created_at", desc=False).execute()
        messages_data = messages_res.data

        return ChatHistory(session=session_data, messages=messages_data)
    except APIError as e:
        if "PGRST116" in e.message: # "PGRST116" is the code for "Not Found"
            raise HTTPException(status_code=404, detail="Chat session not found")
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/chats/{session_id}", status_code=204)
async def delete_chat_session(session_id: str, db: Client = Depends(get_db_connection)):
    """
    Deletes a specific chat session and all its messages (due to ON DELETE CASCADE).
    """
    try:
        response = db.table('chat_sessions').delete().eq('id', session_id).execute()
        
        # Check if any row was actually deleted
        if not response.data:
             raise HTTPException(status_code=404, detail="Chat session not found or already deleted")

    except APIError as e:
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# This function is no longer directly exposed via an endpoint,
# but would be used internally when a new message is generated.
# It needs to be called from the part of your app that handles new messages.
def add_message_to_history(session_id: str, role: str, content: str, db: Client):
    """
    Adds a new message to a chat session's history.
    """
    try:
        response = db.table('chat_messages').insert({
            "session_id": session_id,
            "role": role,
            "content": content
        }).execute()
        return response.data[0]
    except APIError as e:
        print(f"Error adding message to history: {e.message}")
        return None
    except Exception as e:
        print(f"An exception occurred: {e}")
        return None


