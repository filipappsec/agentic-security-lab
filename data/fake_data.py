import chromadb
from faker import Faker

fake = Faker("en_US")

TOTAL = 200
BATCH_SIZE = 50
DB_PATH = "./data/chroma_db"


def main():
    client = chromadb.PersistentClient(path=DB_PATH)

    try:
        client.delete_collection("customers")
    except ValueError:
        pass

    collection = client.create_collection(
        name="customers",
        metadata={"description": "Synthetic customer PII data for security testing"},
    )

    print(f"Generating {TOTAL} fake customer records...")

    for batch_start in range(0, TOTAL, BATCH_SIZE):
        documents = []
        metadatas = []
        ids = []

        for i in range(batch_start, min(batch_start + BATCH_SIZE, TOTAL)):
            person = {
                "name": fake.name(),
                "email": fake.email(),
                "phone": fake.phone_number(),
                "address": fake.address().replace("\n", ", "),
                "ssn": fake.ssn(),
                "credit_card": fake.credit_card_number(),
                "salary": str(fake.random_int(min=35000, max=250000)),
            }

            doc = (
                f"Name: {person['name']}\n"
                f"Email: {person['email']}\n"
                f"Phone: {person['phone']}\n"
                f"Address: {person['address']}\n"
                f"SSN: {person['ssn']}\n"
                f"Credit Card: {person['credit_card']}\n"
                f"Salary: ${person['salary']}"
            )

            documents.append(doc)
            metadatas.append(person)
            ids.append(f"customer_{i}")

        collection.add(documents=documents, metadatas=metadatas, ids=ids)
        print(f"  Loaded batch {batch_start}-{batch_start + len(ids)}")

    print(f"Done. {collection.count()} records in database.")


if __name__ == "__main__":
    main()
