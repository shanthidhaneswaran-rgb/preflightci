
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_DIR = PROJECT_ROOT / "data" / "chroma_db"
COLLECTION_NAME = "preflight_policies"


def retrieve_policies(query, top_k=3):
    client = chromadb.PersistentClient(path=str(DB_DIR))

    embedding_function = DefaultEmbeddingFunction()

    collection = client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function,
    )

    results = collection.query(
        query_texts=[query],
        n_results=min(top_k, collection.count()),
    )

    retrieved = []

    for document, metadata, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        retrieved.append({
            "source": metadata["source"],
            "chunk_index": metadata["chunk_index"],
            "text": document,
            "distance": round(distance, 4),
        })

    return retrieved


if __name__ == "__main__":
    question = (
        "The application logs a customer's full payment card number. "
        "What security policy applies?"
    )

    matches = retrieve_policies(question)

    print(f"Query: {question}\n")
    print("Retrieved policy evidence:")
    print("-" * 60)

    for match in matches:
        print(f"\nSource: {match['source']}")
        print(f"Chunk: {match['chunk_index']}")
        print(f"Distance: {match['distance']}")
        print(f"Text:\n{match['text']}")
