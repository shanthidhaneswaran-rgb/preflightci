def verify_payment(transaction_id):
    response = requests.post(
        "https://payment-service.internal/payments",
        json={"transaction_id": transaction_id},
    )
    return response.status_code