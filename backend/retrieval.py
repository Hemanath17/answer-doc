from openai import OpenAI
from pinecone import Pinecone
import os
import re
from dotenv import load_dotenv
from typing import List, Dict, Optional

load_dotenv()

openai_client   = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pinecone_client = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index           = pinecone_client.Index(os.getenv("PINECONE_INDEX"))

EMBEDDING_MODEL = "text-embedding-3-small"

# CHANGED: 10 → 20
# Retrieval's job is to cast a WIDE net and hand candidates to the reranker.
# Cohere Rerank batches up to 100 docs per billing unit, so going from 10 → 20
# candidates costs nothing extra, but meaningfully reduces the risk that the
# single best chunk for a query sits just outside the cutoff and never gets
# a chance to be re-scored by the cross-encoder.
TOP_K = 20

# CHANGED: 0.40 → 0.15
# This filter now only exists to drop CLEARLY unrelated noise (near-zero
# similarity), not to make relevance judgments. Cosine similarity is the
# weaker signal — the reranker (cross-encoder) is the strong signal and
# should be the one deciding what's actually relevant. A high pre-filter
# here (like the old 0.40) risks silently deleting a chunk that scores low
# on cosine but would have scored very high on the reranker — exactly the
# class of error reranking exists to catch. Keep this low and let
# reranker.py apply its OWN, separately-calibrated threshold after scoring.
MIN_SCORE = 0.15


def clean_query(query: str) -> str:
    """
    Cleans raw user input before embedding.
    Strips whitespace, collapses newlines/tabs into single spaces,
    and caps length to avoid wasted tokens on oversized queries.
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    query = query.strip()
    query = re.sub(r'\s+', ' ', query)
    query = query[:500]

    return query


def embed_query(query: str) -> List[float]:
    """
    Converts the cleaned query into a 1536-dim vector using the SAME
    model used to embed chunks in embedding.py. Model consistency here
    is non-negotiable — mismatched models produce incompatible vector
    spaces and cosine similarity becomes meaningless.
    """
    try:
        response = openai_client.embeddings.create(
            input=query,
            model=EMBEDDING_MODEL
        )
        embedding = response.data[0].embedding
        print(f"Query embedded successfully — {len(embedding)} dimensions")
        return embedding

    except Exception as e:
        print(f"Embedding failed: {e}")
        raise


def search_pinecone(query_vector: List[float], top_k: int = TOP_K) -> List[Dict]:
    """
    Runs the bi-encoder similarity search against Pinecone.
    Returns raw matches — unfiltered, unranked beyond cosine order.
    """
    try:
        results = index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True
        )
        matches = results.get("matches", [])
        print(f"Pinecone returned {len(matches)} raw matches")
        return matches

    except Exception as e:
        print(f"Pinecone search failed: {e}")
        raise


def filter_matches(matches: List[Dict], min_score: float = MIN_SCORE) -> List[Dict]:
    """
    Removes only the clearly irrelevant tail — NOT a relevance decision.
    With MIN_SCORE now at 0.15, this should rarely remove anything from
    a well-formed query; it exists mainly as a safety net against
    pathological cases (empty index region, malformed vector, etc.)
    """
    filtered = [
        match for match in matches
        if match.get("score", 0) >= min_score
    ]
    print(f"After filtering: {len(filtered)} matches above score {min_score}")
    return filtered


def format_for_reranker(matches: List[Dict]) -> List[Dict]:
    """
    Converts raw Pinecone match objects into clean, consistent dicts.
    This is the exact shape reranker.py will consume — retrieval_score
    is kept separate from the future rerank_score so the two signals
    are never accidentally mixed or compared directly.
    """
    formatted = []

    for match in matches:
        metadata = match.get("metadata", {})

        formatted.append({
            "chunk_id"       : match.get("id", ""),
            "retrieval_score": round(match.get("score", 0), 4),
            "chunk_text"     : metadata.get("chunk_text", ""),
            "page_number"    : metadata.get("page_number", 0),
            "source"         : metadata.get("source", ""),
            "has_image"      : metadata.get("has_image", False),
            "image_url"      : metadata.get("image_url", ""),
            "chunk_index"    : metadata.get("chunk_index", 0)
        })

    return formatted


def retrieve(query: str, top_k: int = TOP_K) -> List[Dict]:
    """
    Public entry point — the only function main.py / reranker.py should call.
    Orchestrates: clean → embed → search → light-filter → format.
    Deliberately permissive by design — final relevance judgment happens
    downstream in reranker.py, not here.
    """
    print(f"\n{'='*50}")
    print(f"RETRIEVAL STEP")
    print(f"{'='*50}")
    print(f"Query: {query[:100]}")

    cleaned_query = clean_query(query)
    print(f"Cleaned query: {cleaned_query}")

    query_vector = embed_query(cleaned_query)

    raw_matches = search_pinecone(query_vector, top_k=top_k)

    if not raw_matches:
        print("No matches found — index may be empty")
        return []

    filtered_matches = filter_matches(raw_matches)

    # Safety fallback — if even the low 0.15 bar removes everything
    # (extremely unusual query or near-empty index), don't return nothing.
    # Fall back to raw top 3 so downstream stages always have something.
    if not filtered_matches:
        print(f"All matches below minimum score {MIN_SCORE}")
        print("Returning unfiltered top 3 to avoid empty result")
        filtered_matches = raw_matches[:3]

    candidates = format_for_reranker(filtered_matches)

    print(f"\nRetrieval complete:")
    print(f"  Raw matches      : {len(raw_matches)}")
    print(f"  After filtering  : {len(filtered_matches)}")
    print(f"  Candidates ready : {len(candidates)}")
    if candidates:
        print(f"\nTop candidate (by retrieval score, pre-rerank):")
        print(f"  Score : {candidates[0]['retrieval_score']}")
        print(f"  Page  : {candidates[0]['page_number']}")
        print(f"  Text  : {candidates[0]['chunk_text'][:100]}...")

    return candidates


if __name__ == "__main__":
    test_queries = [
        "what is the north star",
        "how does a refractor telescope work",
        "what are meteor showers",
        "magnitude and brightness of stars",
        "show me a diagram of a telescope"
    ]

    for query in test_queries:
        print(f"\n{'#'*60}")
        candidates = retrieve(query)

        print(f"\nResults for: '{query}'")
        print(f"Total candidates: {len(candidates)}")

        for i, candidate in enumerate(candidates):
            print(f"\n  Candidate {i+1}")
            print(f"    Retrieval score : {candidate['retrieval_score']}")
            print(f"    Page            : {candidate['page_number']}")
            print(f"    Has image       : {candidate['has_image']}")
            print(f"    Image URL       : {candidate['image_url'] or 'none'}")
            print(f"    Text preview    : {candidate['chunk_text'][:150]}...")