from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import os
import requests
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

app = FastAPI(title="E-commerce Dataset API", description="API for querying e-commerce sales data")

class Content(BaseModel):
    type: str
    text: str

class Message(BaseModel):
    content: Content

class ChatRequest(BaseModel):
    message: Message

orders_endpoint = "http://localhost:8001/data"

message_history = []

@app.post("/")
def chat_completions_create(request: ChatRequest):
    print(f"Received: {request.message.content.text}")
    response = requests.get(orders_endpoint)
    if response.status_code == 200:
      orders_data = response.json()
    else:
      orders_data = {"error": "Failed to fetch data"}
    return {"message": f"Received: {request.message.content.text}"}
