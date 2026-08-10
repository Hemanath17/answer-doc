from openai import OpenAI
from pinecone import Pinecone
import os
import json
import time 
from dotenv import load_dotenv
from typing import List, Dict
from tqdm import tqdm


load_dotenv()
openai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=30.0
)
pinecone_client = Pinecone(api_key = os.getenv("PINECONE_API_KEY"))

index = pinecone_client.Index(os.getenv("PINECONE_INDEX"))

EMBEDDING_MODEL = "text-embedding-3-small"

EMBEDDING_DIMENSIONS = 1536

BATCH_SIZE = 100

CHUNKS_FILE = "chunks.jsonl"

from vector_storage import delete_all
delete_all()

def load_chunks(file_path:str) -> List[Dict]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"chunks.jsonl file not found at {file_path}"
            f"Run chunking.py first."
        )
    chunks = []
    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            chunks.append(json.loads(line))
    print(f"Loaded {len(chunks)} chunks from {file_path}")
    return chunks 

def embed_text(text: str) -> List[float]:
    try:
        response = openai_client.embeddings.create(
            input = text,
            model = EMBEDDING_MODEL
        )
        return response.data[0].embedding

    except Exception as e:
        print(f"embedding error: {e}")
        return None

def prepare_vector(chunk: Dict, embedding: List[float]) -> Dict:
    return{
        "id": chunk["chunk_id"],
        "values": embedding,
        "metadata": {
            "chunk_text": chunk["chunk_text"],
            "page_number": chunk["page_number"],
            "chunk_index": chunk["chunk_index"],
            "source": chunk["source"],
            "image_url": chunk["image_url"],
            "has_image": chunk["has_image"],
            "token_estimate": chunk["token_estimate"],
            "char_count": chunk["char_count"],
        }
    }

def upsert_vectors(vectors: List[dict]) -> None:
    total = len(vectors)
    uploaded = 0
    for i in range(0, total, BATCH_SIZE):
        batch = vectors[i:i + BATCH_SIZE]
        try:
            index.upsert(vectors = batch)
            uploaded +=  len(batch)
            print(f"Uploaded {uploaded}/{total} vectors")
        except Exception as e:
            print(f"Batch upload failed for batch starting at {i}: {e}")
        time.sleep(0.5)

def prepare_vector(chunk: Dict, embedding: List[float]) -> Dict:
    return {
        "id"      : chunk["chunk_id"],
        "values"  : embedding,
        "metadata": {
            "chunk_text"    : chunk["chunk_text"],
            "page_number"   : chunk["page_number"],
            "chunk_index"   : chunk["chunk_index"],
            "source"        : chunk["source"],

            # OLD — crashes when image_url is None
            # "image_url"  : chunk["image_url"],

            # NEW — replace None with empty string
            "image_url"     : chunk["image_url"] or "",

            "has_image"     : chunk["has_image"],
            "token_estimate": chunk["token_estimate"],
            "char_count"    : chunk["char_count"]
        }
    }

def embed_and_store(chunks: List[Dict]) -> None:
    print(f"\nEmbedding {len(chunks)} chunks...")
    print(f"Model: {EMBEDDING_MODEL}")
    print(f"Dimensions: {EMBEDDING_DIMENSIONS}")

    vectors_to_upload = []
    failed_chunks = []

    for chunk in tqdm(chunks, desc="Generating embeddings"):
        embedding = embed_text(chunk["chunk_text"])
        if embedding is None:
            failed_chunks.append(chunk["chunk_id"])
            continue
        vector = prepare_vector(chunk, embedding)
        vectors_to_upload.append(vector)

        time.sleep(0.05)

    print(f"\nSuccessfully embedded {len(vectors_to_upload)} chunks")
    if failed_chunks:
        print(f"\nFailed chunks: {len(failed_chunks)} chunks:")
        for chunk_id in failed_chunks:
            print(f"Chunk ID: {chunk_id}")

    if not vectors_to_upload:
        print("No vectors to upload - check embedding erros above")
        return 
    
    print(f"\nUploading to Pinecone index: {os.getenv('PINECONE_INDEX')}")
    upsert_vectors(vectors_to_upload)

    stats = index.describe_index_stats()
    print(f"\nPinecone index stats after upload:")
    print(f"  Total vectors : {stats.total_vector_count}")
    print(f"  Dimensions    : {stats.dimension}")


if __name__ == "__main__":
    chunks = load_chunks(CHUNKS_FILE)
    print(f"\nFirst chunk preview:")
    print(f"  ID    : {chunks[0]['chunk_id']}")
    print(f"  Page  : {chunks[0]['page_number']}")
    print(f"  Chars : {chunks[0]['char_count']}")
    print(f"  Text  : {chunks[0]['chunk_text'][:100]}...")

    embed_and_store(chunks)
    print("\nEmbedding complete — all vectors stored in Pinecone")