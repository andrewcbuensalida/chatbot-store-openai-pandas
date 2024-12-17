import json
from db import insert_message, select_messages, select_messages_by_conversation_id
from fastapi import FastAPI
from orders_products_api import get_all_orders_data, get_orders_by_customer_id,get_product_columns,search_products
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
from dotenv import load_dotenv
from loguru import logger
from tool_schemas import tool_schemas, execute_tool_call
from with_retries import with_retries
from types_local import ChatRequest
import uuid

load_dotenv()

# Configure logger to write logs to a file
logger.add("./log/openai_api.log", rotation="10 MB", retention="10 days", level="DEBUG")

client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

app = FastAPI(title="E-commerce Dataset API", description="API for querying e-commerce sales data")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

current_agent = {
    "name": "Anderson",
    "tools": [get_all_orders_data,get_orders_by_customer_id,get_product_columns,search_products],
    "instructions": "You are a helpful assistant. You are here to help with orders data and products data. Try using the tools first before you use your own knowledge. IMPORTANT! If you can't find what you're looking for, try 2 more times, but with a different query, maybe with less keywords in the query, for example instead of 'BOYA BYM1 Microphone', your second search should be 'BOYA BYM1'."
}

tools = {tool.__name__: tool for tool in current_agent['tools']}



@with_retries
def openai_chat_completion_create(**kwargs):
  logger.info(f"Sending message to OpenAI: {kwargs['messages'][-1]['content']}")
  response = client.chat.completions.create(
    model="gpt-4o",
    parallel_tool_calls=True,
    **kwargs
  )

  return response



@app.get('/health')
def health_check():
    return {"status": "ok"}

@app.get("/api/messages/")
def get_all_messages():
    logger.info(f"Getting all messages for user 1")
    messages = select_messages(1)
    filtered_messages = [message for message in messages if message['role'] in ['user', 'assistant'] and not message.get('tool_calls')]
    return {"messages": filtered_messages}

@app.post("/")
def chat_completions_create(request: ChatRequest):
    print(f"Received: {request.message.content[0].text}")
    conversation_id = request.message.conversationId
    # only have one conversation for now
    messages = select_messages_by_conversation_id(conversation_id)

    # If it's a new conversation, add the system message
    # TODO try except
    if not messages:
        system_message = {
            "conversation_id": conversation_id,
            "message_id": str(uuid.uuid4()),
            "role": 'system',
            "content": [
                {
                    "type":"text",
                    "text":current_agent["instructions"]
                }
            ]
        }
        messages.append(system_message)
        insert_message(conversation_id, system_message) 

    new_user_message = {
      "conversation_id": conversation_id,
      "message_id": request.message.messageId,
      "role": "user",
      "content": [content.dict() for content in request.message.content]
    }
    messages.append(new_user_message)
    insert_message(conversation_id, new_user_message)

    limit = 3
    attempts = 0
    # Loop so openai can respond to tool messages
    while attempts < limit:
        logger.info(f"Attempt {attempts + 1}/{limit}")
        try:
            response = openai_chat_completion_create(
                messages=messages,
                tools=tool_schemas
            )
        except Exception as e:
            logger.error(e)
            return {"error": str(e)}
        
        response_message = {
            "role": response.choices[0].message.role,
            "content": [
                {
                    "type":"text",
                    "text":response.choices[0].message.content
                }
            ],
            "tool_calls": response.choices[0].message.tool_calls,
            "conversation_id": conversation_id,
        }
        messages.append(response_message)
        try:
            insert_message(conversation_id, response_message)
        except Exception as e:
            logger.error(e)
            return {"error": str(e)}

        if response.choices[0].finish_reason == "tool_calls":
            # Loop through all tool calls and execute
            for tool_call in response.choices[0].message.tool_calls:
                try:
                    response = execute_tool_call(
                        tool_call, 
                        tools, 
                        current_agent["name"]
                    )
                    logger.debug(response)
                except Exception as e:  
                    logger.error(e)
                    response = {
                        "error": str(e)
                    }

                tool_message = {
                    "role": "tool",
                    "content": json.dumps(
                        {
                            "tool_name": tool_call.function.name,
                            "arguments": json.loads(tool_call.function.arguments),
                            "response": response
                        }
                    ),
                    "tool_call_id": tool_call.id,
                    "conversation_id": conversation_id,
                }
                messages.append(tool_message)
                try:
                    insert_message(1, tool_message)
                except Exception as e:
                    # TODO need to delete the assistant's tool call from db
                    logger.error(e)
                    return {"error": str(e)}
        else:
            logger.info(response.choices[0].message.content)
            return {"message": response_message}