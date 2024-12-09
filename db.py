import csv
import json
import uuid
from with_retries import with_retries
from loguru import logger

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