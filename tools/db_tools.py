import logging

from langchain_core.tools import tool
import chromadb

logger = logging.getLogger(__name__)

_db_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "chroma_db"
)


def _get_collection():
    client = chromadb.PersistentClient(path=_db_path)
    return client.get_collection("customers")


@tool
def search_customers(query: str, max_results: int = 5) -> str:
    """Search customer database by description (e.g. 'high salary', 'from Warsaw')."""
    collection = _get_collection()

    results = collection.query(query_texts=[query], n_results=max_results)

    docs = results["documents"][0]
    if not docs:
        return f"No customers matching: {query}"

    output = [f"Found {len(docs)} result(s):\n"]
    for i, doc in enumerate(docs, 1):
        output.append(f"[{i}]\n{doc}\n")

    return "\n".join(output)


@tool
def get_customer_by_email(email: str) -> str:
    """Look up a specific customer by their email address."""
    collection = _get_collection()

    results = collection.get(where={"email": email})

    if not results["documents"]:
        return f"No customer found with email: {email}"

    return results["documents"][0]


@tool
def count_customers() -> str:
    """Return the total number of customers in the database."""
    collection = _get_collection()
    return f"Total customers in database: {collection.count()}"
