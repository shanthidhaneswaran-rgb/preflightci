
def store_customer_data(db, customer):
    db.save({
        "pan": customer.pan,
        "account_number": customer.account_number,
    })


def log_payment(logger, card_number):
    logger.info("Processing card: " + card_number)
