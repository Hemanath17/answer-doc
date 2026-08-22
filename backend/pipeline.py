from typing import List, Dict, AsyncGenerator
from retrieval import retrieve
from reranker import rerank
from generation import generate, generate_stream
import asyncio


def get_context(query: str) -> List[Dict]:
    """
    Shared retrieval + reranking step, used by both the sync and
    streaming answer paths below. Extracted here so both paths are
    guaranteed to retrieve identical context for identical queries,
    and so retrieval/reranking logic is never duplicated.

    Does NOT catch exceptions from retrieve() — a retrieval failure
    (e.g. Pinecone or OpenAI embedding API down) is allowed to
    propagate upward. This layer's job is orchestration, not error
    handling; that responsibility belongs to whatever calls this
    pipeline (main.py), which can turn it into a proper HTTP error.
    """
    candidates = retrieve(query)
    reranked = rerank(query, candidates)
    return reranked


def answer_question(query: str) -> Dict:
    """
    Public synchronous entry point. Runs the full pipeline —
    retrieval → reranking → generation — and returns the complete
    structured answer. This is what a plain JSON endpoint
    (e.g. /query) should call.
    """
    chunks = get_context(query)
    result = generate(query, chunks)
    return result


async def answer_question_stream(query: str) -> AsyncGenerator[Dict, None]:
    """
    Public streaming entry point. Runs the same retrieval + reranking
    as answer_question(), but generates the answer via generate_stream(),
    yielding token events followed by one final "done" event carrying
    sources/image metadata. This is what an SSE endpoint
    (e.g. /query/stream) should call.

    Retrieval/rerank run in a thread so the async event loop stays free
    to flush SSE frames once generation starts.
    """
    chunks = await asyncio.to_thread(get_context, query)

    async for event in generate_stream(query, chunks):
        yield event


if __name__ == "__main__":
    test_query = "what is the north star"

    print(f"{'='*50}")
    print("SYNC PIPELINE TEST")
    print(f"{'='*50}")

    result = answer_question(test_query)
    print(f"\nAnswer    : {result['answer']}")
    print(f"Sources   : {result['sources']}")
    print(f"Has image : {result['has_image']}")

    print(f"\n{'='*50}")
    print("STREAMING PIPELINE TEST")
    print(f"{'='*50}")

    async def run_stream_test():
        async for event in answer_question_stream(test_query):
            if event["type"] == "token":
                print(event["content"], end="", flush=True)
            elif event["type"] == "done":
                print(f"\n\nSources   : {event['sources']}")
                print(f"Has image : {event['has_image']}")

    asyncio.run(run_stream_test())