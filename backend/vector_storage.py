from pinecone import Pinecone
from openai import OpenAI
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional

load_dotenv()

openai_client  = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pinecone_client = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index          = pinecone_client.Index(os.getenv("PINECONE_INDEX"))

EMBEDDING_MODEL = "text-embedding-3-small"
TOP_K_DEFAULT   = 3


def embed_query(text: str) -> List[float]:
    response = openai_client.embeddings.create(
        input=text,
        model=EMBEDDING_MODEL
    )
    return response.data[0].embedding


def search(query_text: str, top_k: int = TOP_K_DEFAULT) -> List[Dict]:
    print(f"\nSearching Pinecone for: '{query_text[:50]}...'")

    query_vector = embed_query(query_text)

    results = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True
    )

    matches = results["matches"]

    if not matches:
        print("No matches found in Pinecone")
        return []

    print(f"Found {len(matches)} matches")
    for i, match in enumerate(matches):
        print(f"  Match {i+1}: score={match['score']:.4f} | "
              f"page={match['metadata']['page_number']} | "
              f"has_image={match['metadata']['has_image']}")

    return matches


def format_results(matches: List[Dict]) -> List[Dict]:
    formatted = []

    for match in matches:
        metadata = match["metadata"]

        result = {
            "chunk_id"   : match["id"],
            "score"      : round(match["score"], 4),
            "chunk_text" : metadata.get("chunk_text", ""),
            "page_number": metadata.get("page_number", 0),
            "source"     : metadata.get("source", ""),
            "has_image"  : metadata.get("has_image", False),
            "image_url"  : metadata.get("image_url", ""),
            "chunk_index": metadata.get("chunk_index", 0)
        }

        formatted.append(result)

    return formatted


def upsert_vectors(vectors: List[Dict], batch_size: int = 100) -> bool:
    if not vectors:
        print("No vectors to upsert")
        return False

    total    = len(vectors)
    uploaded = 0
    success  = True

    for i in range(0, total, batch_size):
        batch = vectors[i : i + batch_size]
        try:
            index.upsert(vectors=batch)
            uploaded += len(batch)
            print(f"Uploaded {uploaded}/{total} vectors")
        except Exception as e:
            print(f"Batch upload failed at index {i}: {e}")
            success = False

    return success


def delete_all() -> bool:
    try:
        index.delete(delete_all=True)
        print("All vectors deleted from index")
        return True
    except Exception as e:
        print(f"Delete failed: {e}")
        return False


def get_stats() -> Dict:
    try:
        stats = index.describe_index_stats()
        return {
            "total_vectors": stats.total_vector_count,
            "dimension"    : stats.dimension,
            "metric"       : stats.metric,
            "index_name"   : os.getenv("PINECONE_INDEX")
        }
    except Exception as e:
        print(f"Stats failed: {e}")
        return {}


if __name__ == "__main__":
    print("=== Pinecone Index Stats ===")
    stats = get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n=== Test Search ===")
    test_queries = [
        "what is the north star",
        "how does a refractor telescope work",
        "what are meteor showers",
        "magnitude and brightness of stars"
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        matches = search(query)
        results = format_results(matches)

        for i, result in enumerate(results):
            print(f"\n  Result {i+1}")
            print(f"    Score      : {result['score']}")
            print(f"    Page       : {result['page_number']}")
            print(f"    Has image  : {result['has_image']}")
            print(f"    Image URL  : {result['image_url'] or 'none'}")
            print(f"    Text       : {result['chunk_text'][:120]}...")
            