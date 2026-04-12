from faker import Faker
import chromadb

fake = Faker('pl_PL')

# ChromaDB - lokalna baza wektorowa
client = chromadb.PersistentClient(path="./data/chroma_db")

# Usuń starą kolekcję jeśli istnieje
try:
    client.delete_collection("customers")
except:
    pass

collection = client.create_collection(
    name="customers",
    metadata={"description": "Fake customer PII data for AgentAI Lab"}
)

print("🔄 Generuję fake klientów (w partiach po 50)...")

TOTAL = 200  # Zmniejszamy do 200
BATCH = 50   # Po 50 naraz

for batch_start in range(0, TOTAL, BATCH):
    documents = []
    metadatas = []
    ids = []
    
    for i in range(batch_start, min(batch_start + BATCH, TOTAL)):
        person = {
            "name": fake.name(),
            "email": fake.email(),
            "phone": fake.phone_number(),
            "address": fake.address().replace('\n', ', '),
            "pesel": fake.pesel(),
            "credit_card": fake.credit_card_number(),
            "salary": str(fake.random_int(min=3000, max=25000))
        }
        
        doc = f"""Klient: {person['name']}
Email: {person['email']}
Telefon: {person['phone']}
Adres: {person['address']}
PESEL: {person['pesel']}
Karta: {person['credit_card']}
Wynagrodzenie: {person['salary']} PLN"""
        
        documents.append(doc)
        metadatas.append(person)
        ids.append(f"customer_{i}")
    
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    print(f"  ✅ Batch {batch_start}-{batch_start + len(ids)} done")

print(f"\n🎉 {collection.count()} fake customers loaded into ChromaDB!")
