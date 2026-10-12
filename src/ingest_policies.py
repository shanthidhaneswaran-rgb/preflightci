
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
POLICY_DIR = PROJECT_ROOT / "data" / "policies"
DB_DIR = PROJECT_ROOT / "data" / "chroma_db"

COLLECTION_NAME = "preflight_policies"


def split_into_chunks(text, max_chars=500):
    """Split text into small, searchable chunks while preserving paragraphs."""
    paragraphs = [
        paragraph.strip()
        for paragraph in text.split("\n\n")
        if paragraph.strip()
    ]

    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""

            for start in range(0, len(paragraph), max_chars):
                chunks.append(paragraph[start:start + max_chars])
            continue

        candidate = (
            f"{current_chunk}\n\n{paragraph}"
            if current_chunk
            else paragraph
        )

        if len(candidate) > max_chars:
            chunks.append(current_chunk)
            current_chunk = paragraph
        else:
            current_chunk = candidate

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def main():
    if not POLICY_DIR.exists():
        raise FileNotFoundError(f"Policy directory not found: {POLICY_DIR}")

    policy_files = sorted(POLICY_DIR.glob("*.txt"))

    if not policy_files:
        print(f"No .txt policy files found in {POLICY_DIR}")
        return

    client = chromadb.PersistentClient(path=str(DB_DIR))
    embedding_function = DefaultEmbeddingFunction()

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function,
        metadata={"description": "Preflight-CI policy knowledge base"},
    )

    for policy_file in policy_files:
        text = policy_file.read_text(encoding="utf-8")
        chunks = split_into_chunks(text)

        for index, chunk in enumerate(chunks):
            # Stable IDs make reruns update existing chunks rather
            # than creating duplicates.
            chunk_id = f"{policy_file.stem}-chunk-{index}"

            collection.upsert(
                ids=[chunk_id],
                documents=[chunk],
                metadatas=[{
                    "source": policy_file.name,
                    "chunk_index": index,
                    "policy_type": "demonstration",
                }],
            )

        print(f"Indexed {policy_file.name}: {len(chunks)} chunks")

    print(f"\nTotal stored chunks: {collection.count()}")
    print(f"Database location: {DB_DIR}")


if __name__ == "__main__":
    main()
