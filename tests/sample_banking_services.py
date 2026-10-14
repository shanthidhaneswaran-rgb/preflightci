
import requests
import httpx

def process_payment(transaction_id, amount):
    fraud_response = requests.post(
        "https://fraud-service.internal/check",
        json={"transaction_id": transaction_id, "amount": amount}
    )

    customer_response = httpx.get(
        "https://customer-service.internal/profile"
    )

    return fraud_response.status_code, customer_response.status_code
