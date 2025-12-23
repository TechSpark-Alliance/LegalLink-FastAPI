from typing import List, Optional
from pydantic import BaseModel, Field


class SendMessageInput(BaseModel):
    conversation_id: Optional[str] = Field(default=None, description="Existing conversation id, if any")
    to_user_id: Optional[str] = Field(default=None, description="Recipient user id when starting a new conversation")
    text: str = Field(..., min_length=1, max_length=4000)


class MessageOut(BaseModel):
    id: str
    conversation_id: str
    sender_id: str
    text: str
    created_at: str


class ConversationOut(BaseModel):
    id: str
    participants: List[str]
    last_message: Optional[str] = None
    last_message_at: Optional[str] = None
    unread_count: Optional[int] = 0


class ClearHistoryInput(BaseModel):
    conversation_id: str


class PresenceUpdate(BaseModel):
    status: Optional[str] = Field(default="online", description="online/away")


class PresenceOut(BaseModel):
    user_id: str
    online: bool
    last_seen: Optional[str] = None
