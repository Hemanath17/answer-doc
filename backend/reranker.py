import cohere
import os
from dotenv import load_dotenv
from typing import List, Dict

load_dotenv()

co = cohere.Client(os.getenv("COHERE_API_KEY"))

RERANK_MODEL = "rerank-english-v3.0"
TOP_N = 3

# Placeholder — validated against real data already (0.2 correctly
# rejected the "capital of France" query with all zero scores, and
# correctly kept 2-7 candidates on real astronomy queries)
MIN_RERANK_SCORE = 0.20

TIMEOUT_SECONDS = 5

# Keywords signaling the user wants to SEE something, not just read.
# Same heuristic used in generation.py's detect_image_intent — kept
# as a separate local copy here (not imported) to avoid a circular
# import between reranker.py and generation.py.
IMAGE_INTENT_KEYWORDS = [
    "show", "diagram", "image", "picture", "illustration",
    "what does", "looks like", "design of", "draw", "photo",
    "visual", "see a", "see the"
]

# How much to boost a has_image=True chunk's rerank_score when the
# query shows visual intent. Additive, capped at 1.0. Chosen so that
# a moderately-relevant image chunk (e.g. 0.35-0.55 raw score) can
# realistically compete with and beat a text-only chunk that merely
# contains the word "diagram" (which we saw score 0.81 in testing).
IMAGE_BOOST_AMOUNT = 0.35


def detect_image_intent(query: str) -> bool:
    """
    Checks if the user's question signals they want to SEE something.
    Same logic as generation.py — duplicated locally by design.
    """
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in IMAGE_INTENT_KEYWORDS)


def rerank_candidates(query: str, candidates: List[Dict], top_n: int = TOP_N) -> List[Dict]:
    """
    Sends all candidates to Cohere's cross-encoder for scoring.
    Wrapped in try/except — falls back to retrieval order on failure.
    """
    if not candidates:
        print("No candidates to rerank")
        return []

    documents = [c["chunk_text"] for c in candidates]

    try:
        print(f"\nReranking {len(candidates)} candidates with Cohere...")

        response = co.rerank(
            query=query,
            documents=documents,
            top_n=len(candidates),
            model=RERANK_MODEL
        )

        reranked = []
        for result in response.results:
            original_candidate = candidates[result.index]
            reranked_candidate = {
                **original_candidate,
                "rerank_score": round(result.relevance_score, 4)
            }
            reranked.append(reranked_candidate)

        print(f"Rerank successful — {len(reranked)} scored candidates")
        return reranked

    except Exception as e:
        print(f"Rerank failed, falling back to retrieval order: {e}")

        fallback = []
        for c in candidates:
            fallback_candidate = {
                **c,
                "rerank_score": c.get("retrieval_score", 0)
            }
            fallback.append(fallback_candidate)

        return fallback


def boost_image_chunks(reranked: List[Dict], query: str) -> List[Dict]:
    """
    If the query shows visual intent, boost the rerank_score of any
    chunk that has_image=True. This runs AFTER Cohere scoring but
    BEFORE filtering/sorting for final selection — deliberately, so
    a boosted image chunk gets a fair chance to clear the score
    threshold and make it into the final top_n, rather than being
    dropped before the boost could help it.

    Without this, a text chunk that merely CONTAINS the word "diagram"
    can outscore an actual image-bearing chunk, because Cohere scores
    pure text relevance and has zero awareness of your has_image
    metadata field.
    """
    if not detect_image_intent(query):
        # no visual intent detected — leave scores untouched
        return reranked

    print(f"Image intent detected in query — applying boost to has_image=True chunks")

    boosted = []
    for chunk in reranked:
        new_chunk = dict(chunk)  # avoid mutating the original dict

        if chunk.get("has_image"):
            original_score = chunk["rerank_score"]
            # additive boost, capped at 1.0 so it never exceeds
            # the valid Cohere score range
            boosted_score = min(original_score + IMAGE_BOOST_AMOUNT, 1.0)
            new_chunk["rerank_score"] = round(boosted_score, 4)
            new_chunk["image_boosted"] = True

            print(f"  Boosted page {chunk['page_number']}: "
                  f"{original_score} → {new_chunk['rerank_score']}")
        else:
            new_chunk["image_boosted"] = False

        boosted.append(new_chunk)

    return boosted


def filter_by_rerank_score(reranked: List[Dict], min_score: float = MIN_RERANK_SCORE) -> List[Dict]:
    """
    Removes candidates below the rerank quality bar. Runs AFTER
    boosting, so a boosted image chunk is judged on its FINAL score,
    not its pre-boost score.
    """
    filtered = [c for c in reranked if c["rerank_score"] >= min_score]

    print(f"After rerank filtering: {len(filtered)} candidates above score {min_score}")

    if not filtered:
        print(f"All candidates below {min_score} — returning top 3 unfiltered")
        return reranked[:3]

    return filtered


def rerank(query: str, candidates: List[Dict], top_n: int = TOP_N) -> List[Dict]:
    """
    Public entry point — the only function main.py should call.
    Order of operations matters here:
      1. score      — Cohere cross-encoder scores all candidates
      2. boost      — image-intent boost applied BEFORE filtering
      3. filter     — drop weak candidates using FINAL (post-boost) scores
      4. sort + cut — take top_n by final score
    """
    print(f"\n{'='*50}")
    print(f"RERANKING STEP")
    print(f"{'='*50}")

    scored = rerank_candidates(query, candidates)

    if not scored:
        return []

    boosted = boost_image_chunks(scored, query)

    filtered = filter_by_rerank_score(boosted)

    # sort by rerank_score descending — boosting can change the order,
    # so we always re-sort here regardless of path taken above
    filtered.sort(key=lambda c: c["rerank_score"], reverse=True)

    final = filtered[:top_n]

    print(f"\nFinal top {len(final)} after reranking:")
    for i, c in enumerate(final):
        boosted_tag = " (boosted)" if c.get("image_boosted") else ""
        print(f"  {i+1}. rerank_score={c['rerank_score']}{boosted_tag} | "
              f"retrieval_score={c['retrieval_score']} | "
              f"page={c['page_number']} | has_image={c['has_image']}")

    return final


if __name__ == "__main__":
    from retrieval import retrieve

    test_queries = [
        "what is the north star",
        "how does a refractor telescope work",
        "what are meteor showers",
        "magnitude and brightness of stars",
        "show me a diagram of a telescope"   # the query that failed before
    ]

    for query in test_queries:
        print(f"\n{'#'*60}")
        print(f"QUERY: {query}")

        candidates = retrieve(query)
        final = rerank(query, candidates)

        print(f"\n--- Final Answer Context for: '{query}' ---")
        for i, chunk in enumerate(final):
            print(f"\n  Chunk {i+1}")
            print(f"    Rerank score    : {chunk['rerank_score']}")
            print(f"    Retrieval score : {chunk['retrieval_score']}")
            print(f"    Page            : {chunk['page_number']}")
            print(f"    Has image       : {chunk['has_image']}")
            print(f"    Image URL       : {chunk['image_url'] or 'none'}")
            print(f"    Text            : {chunk['chunk_text'][:150]}...")
            