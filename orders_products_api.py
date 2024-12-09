import requests
import os

orders_endpoint = os.getenv('ORDERS_ENDPOINT', "http://localhost:8001/data")

# TODO try except
def get_all_orders_data():
    response = requests.get(orders_endpoint)
    return response.json()[:3] # it's going to be too much to pass to openai if we don't limit it

def get_orders_by_customer_id(customer_id): # example customer_id = 37077
    response = requests.get(f"{orders_endpoint}/customer/{customer_id}")
    return response.json()[:3] # it's going to be too much to pass to openai if we don't limit it