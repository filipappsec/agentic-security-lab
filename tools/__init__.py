from .gmail_tools import read_emails, send_email, search_emails
from .db_tools import search_customers, get_customer_by_email, count_customers

ALL_TOOLS = [
    read_emails,
    send_email,
    search_emails,
    search_customers,
    get_customer_by_email,
    count_customers,
]
