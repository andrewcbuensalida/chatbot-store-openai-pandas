import json
from loguru import logger


def execute_tool_call(tool_call, tools, agent_name, **more_args):
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    logger.debug(f"{agent_name}: {name}({args})")

    return tools[name](**args,**more_args)  # call corresponding function with provided arguments

tool_schemas = [
    {
        "type": "function",
        "function": {
            "name": "get_all_orders_data",
            "description": "Get all orders data.",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_orders_by_customer_id",
            "description": "Get orders by customer ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "The customer's ID.",
                    }
                },
                "required": ["customer_id"],
                "additionalProperties": False,
            },
        },
    }
]