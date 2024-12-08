from pydantic import BaseModel

class Content(BaseModel):
    type: str
    text: str

class Message(BaseModel):
  content: list[Content]
  conversationId: str

class ChatRequest(BaseModel):
    message: Message