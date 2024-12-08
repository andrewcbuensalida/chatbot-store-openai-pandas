from pydantic import BaseModel

class Content(BaseModel):
    type: str
    text: str

class Message(BaseModel):
  content: list[Content]

class ChatRequest(BaseModel):
    message: Message