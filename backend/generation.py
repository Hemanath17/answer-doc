from openai import OpenAI, AsyncOpenAI
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional, AsyncGenerator
import json

load_dotenv()

openai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=30.0
)

# Async client for SSE streaming — sync iteration inside an async
# generator blocks the event loop and can delay/buffer tokens to the client.
async_openai_client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=30.0
)

GENERATION_MODEL = "gpt-4o-mini"
TEMPERATURE = 0
MIN_CONTEXT_SCORE = 0.15

IMAGE_INTENT_KEYWORDS = [
    "show", "diagram", "image", "picture", "illustration",
    "what does", "looks like", "design of", "draw", "photo",
    "visual", "see a", "see the"
]

NO_ANSWER_PHRASE = "i don't have enough information"

PROMPT_FILE = os.path.join(os.path.dirname(__file__), "prompt.txt")


def load_system_prompt() -> str:
    if not os.path.exists(PROMPT_FILE):
        raise FileNotFoundError(
            f"prompt.txt not found at {PROMPT_FILE}. "
            f"This file must exist alongside generation.py."
        )

    with open(PROMPT_FILE, "r") as f:
        prompt = f.read().strip()

    if not prompt:
        raise ValueError("prompt.txt exists but is empty.")

    return prompt


SYSTEM_PROMPT = load_system_prompt()


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
    context_blocks = []
    for chunk in chunks:
        block = f"[Page {chunk['page_number']}]\n{chunk['chunk_text']}"
        context_blocks.append(block)

    context_text = "\n\n---\n\n".join(context_blocks)

    user_prompt = f"""Context from the textbook:

{context_text}

Question: {query}

Answer (cite page numbers):"""

    return SYSTEM_PROMPT, user_prompt


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


# ─── Non-streaming generation (unchanged, kept for /query and testing) ───

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


def generate(query: str, chunks: List[Dict]) -> Dict:
    """
    Non-streaming version — kept as-is. Used by /query (plain JSON
    endpoint) and by the __main__ test block below. Also useful as
    a simple way to test pipeline correctness without dealing with
    streaming mechanics.
    """
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


# ─── Streaming generation (new) ───

async def call_llm_stream(system_prompt: str, user_prompt: str) -> AsyncGenerator[str, None]:
    """
    Streaming variant of call_llm(). Uses AsyncOpenAI + stream=True so
    tokens are awaited without blocking the event loop — required for
    SSE to flush to the browser as tokens arrive.
    """
    try:
        stream = await async_openai_client.chat.completions.create(
            model=GENERATION_MODEL,
            temperature=TEMPERATURE,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            stream=True
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    except Exception as e:
        print(f"Streaming generation failed: {e}")
        yield "Sorry, I wasn't able to generate an answer right now. Please try again."


async def generate_stream(query: str, chunks: List[Dict]) -> AsyncGenerator[Dict, None]:
    """
    Public streaming entry point — what main.py's /query/stream
    endpoint will call. Yields a sequence of small dicts, each
    tagged with a "type" field so main.py (and eventually React)
    can tell them apart:

      {"type": "token", "content": "The"}
      {"type": "token", "content": " image"}
      ...
      {"type": "done", "sources": [...], "has_image": bool, "image_url": ...}

    The image/sources decision logic is IDENTICAL to generate() —
    it still has to wait until the full answer text is known before
    it can check llm_declined, decide_image, and build_sources. This
    is why those three things only appear in the final "done" event,
    never interleaved with the token stream — that decision was
    discussed and agreed on before writing this function.
    """
    print(f"\n{'='*50}")
    print(f"GENERATION STEP (streaming)")
    print(f"{'='*50}")
    print(f"Query: {query}")

    if not has_sufficient_context(chunks):
        print("Context too weak — skipping LLM call")
        fallback_answer = "I don't have enough information in this document to answer that."

        # still stream it as a single token event so the frontend's
        # rendering logic doesn't need a separate code path for this case
        yield {"type": "token", "content": fallback_answer}
        yield {
            "type"      : "done",
            "sources"   : [],
            "has_image" : False,
            "image_url" : None
        }
        return

    system_prompt, user_prompt = build_prompt(query, chunks)

    # accumulate the full answer as tokens stream in — needed for the
    # llm_declined check, which can only run once the full text is known
    full_answer = ""

    async for token in call_llm_stream(system_prompt, user_prompt):
        full_answer += token
        yield {"type": "token", "content": token}

    llm_declined = NO_ANSWER_PHRASE in full_answer.lower()

    if llm_declined:
        print("LLM declined to answer despite passing context gate — suppressing image/sources")
        image_url = None
        sources = []
    else:
        image_url = decide_image(query, chunks)
        sources = build_sources(chunks)

    print(f"\nStream complete:")
    print(f"  LLM declined : {llm_declined}")
    print(f"  Sources      : {[s['page'] for s in sources]}")
    print(f"  Has image    : {image_url is not None}")
    print(f"  Image URL    : {image_url or 'none'}")
    print(f"  Answer       : {(full_answer[:200] + '...') if len(full_answer) > 200 else full_answer}")

    yield {
        "type"      : "done",
        "sources"   : sources,
        "has_image" : image_url is not None,
        "image_url" : image_url
    }


if __name__ == "__main__":
    import asyncio
    from retrieval import retrieve
    from reranker import rerank

    test_queries = [
        "what is the north star",
        "show me a diagram of a telescope",
    ]

    async def run_streaming_tests():
        for query in test_queries:
            print(f"\n{'#'*60}")
            print(f"STREAMING TEST: {query}")

            candidates = retrieve(query)
            final_chunks = rerank(query, candidates)

            print(f"\n--- Streamed output ---")
            full_text = ""
            async for event in generate_stream(query, final_chunks):
                if event["type"] == "token":
                    print(event["content"], end="", flush=True)
                    full_text += event["content"]
                elif event["type"] == "done":
                    print(f"\n\n--- Done event ---")
                    print(f"Sources   : {event['sources']}")
                    print(f"Has image : {event['has_image']}")
                    print(f"Image URL : {event['image_url']}")

    asyncio.run(run_streaming_tests())