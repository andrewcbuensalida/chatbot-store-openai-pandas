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
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_columns",
            "description": "Get the columns of the product data so you know what to sort by.",
        },
    },    
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search for products. You can specify a query, sort column, sort order, and limit. IMPORTANT! If you can't find what you're looking for, try 2 more times, but with a different query, maybe with less keywords.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query.",
                    },
                    "sort_column": {
                        "type": "string",
                        "description": "The column to sort by.",
                    },
                    "sort_order": {
                        "type": "string",
                        "description": "The order to sort by.",
                        "enum": ["asc", "desc"],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "The maximum number of results to return. If the user says a number more than 10, mention the limit and ask for a smaller number.",
                    },
                },
                "required": ["query", "sort_column", "sort_order", "limit"],
                "additionalProperties": False,
            }
        },
    },
]