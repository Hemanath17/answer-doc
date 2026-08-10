from openai import OpenAI
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional

load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

GENERATION_MODEL = "gpt-4o-mini"
TEMPERATURE = 0
MIN_CONTEXT_SCORE = 0.15

IMAGE_INTENT_KEYWORDS = [
    "show", "diagram", "image", "picture", "illustration",
    "what does", "looks like", "design of", "draw", "photo",
    "visual", "see a", "see the"
]

# Phrase we check for to detect that GPT-4o mini itself declined
# to answer, even though it technically got called. This is the
# ONLY reliable signal for "did we actually produce a real answer" —
# has_sufficient_context() only looks at scores BEFORE generation,
# it can't know in advance whether the chunks will actually be
# enough for the model to answer confidently.
NO_ANSWER_PHRASE = "i don't have enough information"


def detect_image_intent(query: str) -> bool:
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in IMAGE_INTENT_KEYWORDS)


def decide_image(query: str, chunks: List[Dict]) -> Optional[str]:
    if not detect_image_intent(query):
        return None

    for chunk in chunks:
        if chunk.get("has_image") and chunk.get("image_url"):
            return chunk["image_url"]

    return None


def has_sufficient_context(chunks: List[Dict]) -> bool:
    if not chunks:
        return False
    top_score = chunks[0].get("rerank_score", 0)
    return top_score >= MIN_CONTEXT_SCORE


def build_prompt(query: str, chunks: List[Dict]) -> tuple:
    system_prompt = """You are an expert astronomy assistant helping users understand content from their astronomy textbook.

Rules:
1. Answer ONLY using the provided context below. Do not use any outside knowledge.
2. You may reasonably connect information ACROSS the given context chunks, but never introduce facts not present in them.
3. If the answer is not in the context, say: "I don't have enough information in this document to answer that."
4. Always cite the page number(s) your answer is based on, in the format (Page X).
5. If the context includes a markdown table, read it carefully — the answer may be a specific row or value in that table.
6. If different chunks contain conflicting information, point out the discrepancy rather than silently picking one.
7. Be concise but complete. Do not pad your answer with filler."""

    context_blocks = []
    for chunk in chunks:
        block = f"[Page {chunk['page_number']}]\n{chunk['chunk_text']}"
        context_blocks.append(block)

    context_text = "\n\n---\n\n".join(context_blocks)

    user_prompt = f"""Context from the textbook:

{context_text}

Question: {query}

Answer (cite page numbers):"""

    return system_prompt, user_prompt


def call_llm(system_prompt: str, user_prompt: str) -> str:
    try:
        response = openai_client.chat.completions.create(
            model=GENERATION_MODEL,
            temperature=TEMPERATURE,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        answer = response.choices[0].message.content

        usage = response.usage
        print(f"Tokens used — prompt: {usage.prompt_tokens}, "
              f"completion: {usage.completion_tokens}, "
              f"total: {usage.total_tokens}")

        return answer

    except Exception as e:
        print(f"Generation failed: {e}")
        return "Sorry, I wasn't able to generate an answer right now. Please try again."


def build_sources(chunks: List[Dict]) -> List[Dict]:
    sources = []
    seen_pages = set()

    for chunk in chunks:
        page = chunk["page_number"]
        if page not in seen_pages:
            sources.append({
                "page": page,
                "preview": chunk["chunk_text"][:100]
            })
            seen_pages.add(page)

    return sources


def generate(query: str, chunks: List[Dict]) -> Dict:
    print(f"\n{'='*50}")
    print(f"GENERATION STEP")
    print(f"{'='*50}")
    print(f"Query: {query}")

    if not has_sufficient_context(chunks):
        print("Context too weak — skipping LLM call")
        return {
            "answer"    : "I don't have enough information in this document to answer that.",
            "sources"   : [],
            "has_image" : False,
            "image_url" : None
        }

    system_prompt, user_prompt = build_prompt(query, chunks)

    answer = call_llm(system_prompt, user_prompt)

    # FIX — check if GPT-4o mini itself declined to answer, even
    # though the context-score gate passed. Only attach an image
    # and sources if a REAL answer was actually produced. Without
    # this check you can end up showing an image alongside "I don't
    # have enough information" — a contradictory response.
    llm_declined = NO_ANSWER_PHRASE in answer.lower()

    if llm_declined:
        print("LLM declined to answer despite passing context gate — suppressing image/sources")
        image_url = None
        sources = []
    else:
        image_url = decide_image(query, chunks)
        sources = build_sources(chunks)

    result = {
        "answer"    : answer,
        "sources"   : sources,
        "has_image" : image_url is not None,
        "image_url" : image_url
    }

    print(f"\nAnswer generated:")
    print(f"  LLM declined : {llm_declined}")
    print(f"  Sources      : {[s['page'] for s in sources]}")
    print(f"  Has image    : {result['has_image']}")
    print(f"  Image URL    : {image_url or 'none'}")
    print(f"  Answer       : {answer[:200]}...")

    return result


if __name__ == "__main__":
    from retrieval import retrieve
    from reranker import rerank

    test_queries = [
        "what is the north star",
        "how does a refractor telescope work",
        "what are meteor showers",
        "what is the limiting magnitude of an 8 inch telescope",
        "show me a diagram of a telescope",
        "what is the capital of France"
    ]

    for query in test_queries:
        print(f"\n{'#'*60}")
        print(f"FULL PIPELINE TEST: {query}")

        candidates = retrieve(query)
        final_chunks = rerank(query, candidates)
        result = generate(query, final_chunks)

        print(f"\n{'='*50}")
        print(f"FINAL RESULT")
        print(f"{'='*50}")
        print(f"Answer    : {result['answer']}")
        print(f"Sources   : {result['sources']}")
        print(f"Has image : {result['has_image']}")
        print(f"Image URL : {result['image_url']}")