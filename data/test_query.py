import chromadb

client = chromadb.PersistentClient(path="./data/chroma_db")
collection = client.get_collection("customers")

print(f"📊 Rekordów w bazie: {collection.count()}\n")

# Szukaj semantycznie
results = collection.query(
    query_texts=["klient z wysoką pensją z Warszawy"],
    n_results=3
)

print("🔍 Query: 'klient z wysoką pensją z Warszawy'\n")
for i, doc in enumerate(results['documents'][0]):
    print(f"--- Wynik {i+1} ---")
    print(doc)
    print()
