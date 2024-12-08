import json
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
import requests
from dotenv import load_dotenv
from loguru import logger
from tools import tool_schemas, execute_tool_call
from with_retries import with_retries
from types_local import ChatRequest
import csv
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
orders_endpoint = os.getenv('ORDERS_ENDPOINT', "http://localhost:8001/data")

# TODO try except
def get_all_orders_data():
    response = requests.get(orders_endpoint)
    return response.json()[:3] # it's going to be too much to pass to openai if we don't limit it

def get_orders_by_customer_id(customer_id): # example customer_id = 37077
    response = requests.get(f"{orders_endpoint}/customer/{customer_id}")
    return response.json()[:3] # it's going to be too much to pass to openai if we don't limit it

current_agent = {
    "name": "Anderson",
    "tools": [get_all_orders_data,get_orders_by_customer_id],
    "instructions": "You are a helpful assistant. You are here to help with orders data and products data. "
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

@with_retries
def select_messages(user_id):
    logger.info(f"Selecting messages for user: {user_id}")
    messages = []
    # return messages # delete this line to turn on memory # need memory if getting orders by a certain filter
    with open('messages.csv', mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if True:
            # if int(row['user_id']) == user_id:
                messages.append(
                    {
                        **row,
                        "tool_calls": json.loads(row["tool_calls"]) if row["tool_calls"] else None
                    }
                )
    return messages

@with_retries
def select_messages_by_conversation_id(conversation_id):
    logger.info(f"Selecting messages for conversation: {conversation_id}")
    messages = []
    with open('messages.csv', mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['conversation_id'] == conversation_id:
                messages.append(
                    {
                        **row,
                        "tool_calls": json.loads(row["tool_calls"]) if row["tool_calls"] else None
                    }
                )
    return messages

@with_retries
def insert_message(conversation_id, message):
    logger.info(f"Inserting message: {message}")
    message_id = str(uuid.uuid4())
    with open('messages.csv', mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['conversation_id', 'message_id', 'role', 'content',"tool_calls", "tool_call_id"])
        writer.writerow(
            {
                "conversation_id": conversation_id,
                "message_id": message_id,
                **message,
                "content": json.dumps(message.get('content')) if message.get('content') else None,
                "tool_calls": json.dumps([tool_call.dict() for tool_call in message.get('tool_calls')]) if message.get('tool_calls') else None
            }
        )
    return message_id # not really used

@app.get('/health')
def health_check():
    return {"status": "ok"}

@app.get("/api/messages/")
def get_all_messages():
    logger.info(f"Getting all messages for user 1")
    messages = select_messages(1)
    filtered_messages = [message for message in messages if message['role'] in ['user', 'assistant'] and not message.get('tool_calls')]
    print('''*Example filtered_messages:\n''', filtered_messages)
    return {"messages": filtered_messages}

@app.post("/")
def chat_completions_create(request: ChatRequest):
    print(f"Received: {request.message.content[0].text}")
    conversation_id = request.message.conversationId
    print('''*Example conversation_id:\n''', conversation_id)
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
        response = openai_chat_completion_create(
            messages=messages,
            tools=tool_schemas
        )
        logger.debug(response.choices[0].message)
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
        logger.debug(response_message)
        messages.append(response_message)
        insert_message(conversation_id, response_message)


        if response.choices[0].finish_reason == "tool_calls":
            # Loop through all tool calls and execute
            for tool_call in response.choices[0].message.tool_calls:
                response = execute_tool_call(
                    tool_call, 
                    tools, 
                    current_agent["name"]
                )
                logger.debug(response)

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
                insert_message(1, tool_message)
        else:
            logger.info(response.choices[0].message.content)
            return {"message": response_message}