import chromadb

DB_PATH = "./data/chroma_db"


def main():
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_collection("customers")

    print(f"Records in database: {collection.count()}\n")

    query = "customer with high salary from Warsaw"
    results = collection.query(query_texts=[query], n_results=3)

    print(f"Query: '{query}'\n")
    for i, doc in enumerate(results["documents"][0], 1):
        print(f"--- Result {i} ---")
        print(doc)
        print()


if __name__ == "__main__":
    main()
