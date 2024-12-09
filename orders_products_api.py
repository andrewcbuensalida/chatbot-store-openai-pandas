import requests
import os
from loguru import logger

from with_retries import with_retries

orders_endpoint = os.getenv('ORDERS_ENDPOINT', "http://localhost:8001/data")

@with_retries
def get_all_orders_data():
    logger.info(f"Getting all orders data")
    response = requests.get(orders_endpoint)
    return response.json()[:3] # it's going to be too much to pass to openai if we don't limit it

@with_retries
def get_orders_by_customer_id(customer_id): # example customer_id = 37077
    logger.info(f"Getting orders for customer: {customer_id}")
    response = requests.get(f"{orders_endpoint}/customer/{customer_id}")
    return response.json()[:3] # it's going to be too much to pass to openai if we don't limit it

@with_retries
def get_product_columns():
    logger.info(f"Getting product columns")
    response = requests.get(f"{orders_endpoint}/product-columns")
    return response.json()