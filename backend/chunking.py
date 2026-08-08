# langchain's recursive character text splitter — Strategy 6 built-in
from langchain_text_splitters import RecursiveCharacterTextSplitter
import json
import os
import uuid
from typing import List, Dict
from pydantic import BaseModel
from parsing import ParsedPage

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
SEPARATORS = ["\n\n", "\n", ".", " ", ""]

CACHE_FILE = "chunks.jsonl"

class Chunk(BaseModel):

    chunk_id: str

    chunk_text: str

    page_number: int

    chunk_index: int

    source: str

    image_url: str | None

    has_image: bool

    token_estimate: int

    # character count of this chunk
    char_count: int


# ─── Helper: Combine text and tables into one string ─────────────────────────

def combine_page_content(page: ParsedPage) -> str:
    # start with the raw extracted text from this page
    content = page.text
    if page.tables:
        for table in page.tables:
            content += "\n\n" + table

    return content


# ─── Main Chunking Function ───────────────────────────────────────────────────

def chunk_pages(pages: List[ParsedPage], source_name: str = "Astronomy_Basics.pdf") -> List[Chunk]:

    # check if cached chunks already exist on disk
    # if yes — load them instead of re-chunking (saves time on repeated runs)
    if os.path.exists(CACHE_FILE):
        print(f"Cache found — loading chunks from {CACHE_FILE}")
        chunks = []

        # open the JSONL file and read one line at a time
        # each line is one chunk as a JSON string
        with open(CACHE_FILE, "r") as f:
            for line in f:
                # parse the JSON line back into a dictionary
                data = json.loads(line)

                # reconstruct the Pydantic Chunk object from the dictionary
                chunks.append(Chunk(**data))

        print(f"Loaded {len(chunks)} chunks from cache.")
        return chunks


    print("No cache found — running chunker...")

    # initialize LangChain's RecursiveCharacterTextSplitter
    # this is Strategy 6 — tries separators in order, recurses on oversized pieces
    splitter = RecursiveCharacterTextSplitter(

        # maximum characters per chunk — matches your CHUNK_SIZE constant
        chunk_size=CHUNK_SIZE,

        # characters of overlap between consecutive chunks
        # LangChain handles the overlap logic internally — no manual merge needed
        chunk_overlap=CHUNK_OVERLAP,

        # separator hierarchy — paragraph → line → sentence → word → character
        separators=SEPARATORS,

        # measure chunk size in characters not tokens
        # consistent and fast — no tokenizer needed at this stage
        length_function=len,

        # if True, adds length metadata to each chunk automatically
        # False keeps output clean — we add our own metadata below
        add_start_index=False
    )

    # master list that collects every chunk from every page
    all_chunks: List[Chunk] = []

    # loop through every parsed page from parsing.py
    for page in pages:

        # combine text and markdown tables into one string for splitting
        content = combine_page_content(page)

        # skip pages with no meaningful content
        # strip() removes whitespace — a page with only spaces is also skipped
        if not content.strip():
            print(f"Skipping page {page.page_number} — no content")
            continue

        # use LangChain splitter to split this page's content into chunks
        # returns a plain list of strings — one string per chunk
        # LangChain handles the recursion and overlap internally
        raw_chunks: List[str] = splitter.split_text(content)

        # loop through each chunk LangChain produced
        for chunk_index, chunk_text in enumerate(raw_chunks):

            # clean leading and trailing whitespace from the chunk
            chunk_text = chunk_text.strip()

            # skip empty chunks — safety guard against edge cases
            if not chunk_text:
                continue

            # merge tiny remainder chunks into the previous chunk
            # anything under 150 chars is too small to embed meaningfully
            # 150 chars ≈ 2-3 sentences minimum for a useful vector
            if len(chunk_text) < 150:

                # if there's a previous chunk on the SAME page — merge into it
                # same page check prevents merging across page boundaries
                if all_chunks and all_chunks[-1].page_number == page.page_number:
                    # append the tiny chunk to the previous chunk's text
                    merged_text = all_chunks[-1].chunk_text + " " + chunk_text

                    # update the previous chunk with merged content
                    # pydantic models are immutable so we rebuild with model_copy
                    all_chunks[-1] = all_chunks[-1].model_copy(update={
                        "chunk_text": merged_text,
                        "char_count": len(merged_text),
                        "token_estimate": len(merged_text) // 4
                    })

                # if no previous chunk on this page — skip the tiny chunk entirely
                continue

            # generate a unique ID for this chunk
            # uuid4() generates a random UUID — guaranteed unique across all chunks
            # format: chunk_{uuid} — easy to identify in Pinecone metadata
            chunk_id = f"chunk_{uuid.uuid4().hex[:12]}"

            # get the image URL from this page — None if page had no image
            # page.images is a list — take first image if list is not empty
            image_url = page.images[0] if page.images else None

            # build the Chunk Pydantic object — validates all fields automatically
            chunk = Chunk(
                chunk_id=chunk_id,
                chunk_text=chunk_text,
                page_number=page.page_number,
                chunk_index=chunk_index,
                source=source_name,
                image_url=image_url,
                has_image=page.has_image,

                # rough token estimate — divide chars by 4 for English text
                # useful for verifying we stay under the 256 token embedding limit
                token_estimate=len(chunk_text) // 4,

                char_count=len(chunk_text)
            )

            # add this chunk to the master list
            all_chunks.append(chunk)

    # ── Save chunks to JSONL cache ─────────────────────────────────────────────

    print(f"\nSaving {len(all_chunks)} chunks to {CACHE_FILE}...")

    # open JSONL file for writing — one chunk per line
    with open(CACHE_FILE, "w") as f:
        for chunk in all_chunks:
            # model_dump_json() converts Pydantic object to JSON string
            # + "\n" puts each chunk on its own line — that's the JSONL format
            f.write(chunk.model_dump_json() + "\n")

    print(f"Saved to {CACHE_FILE}")
    return all_chunks


# ─── Test Block ───────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # import parse_pdf only when running this file directly
    # avoids circular imports when chunking.py is imported by other files
    from parsing import parse_pdf

    print("Step 1 — Running parser...")
    # parse the PDF — loads from parsed_pages.jsonl cache if it exists
    pages = parse_pdf("Astronomy_Basics.pdf")

    print("\nStep 2 — Chunking pages...")
    # chunk all pages — loads from chunks.jsonl cache if it exists
    chunks = chunk_pages(pages)

    # ── Summary stats ──────────────────────────────────────────────────────────

    print(f"\n{'='*50}")
    print(f"Total chunks         : {len(chunks)}")
    print(f"Average chunk size   : {sum(c.char_count for c in chunks) // len(chunks)} characters")
    print(f"Average token est.   : {sum(c.token_estimate for c in chunks) // len(chunks)} tokens")
    print(f"Chunks with images   : {sum(1 for c in chunks if c.has_image)}")
    print(f"Chunks without images: {sum(1 for c in chunks if not c.has_image)}")

    # ── Preview first 3 chunks ─────────────────────────────────────────────────

    print(f"\n--- First 3 chunks ---")
    for chunk in chunks[:3]:
        print(f"\nChunk ID    : {chunk.chunk_id}")
        print(f"Page        : {chunk.page_number} | Index: {chunk.chunk_index}")
        print(f"Chars       : {chunk.char_count} | Tokens: ~{chunk.token_estimate}")
        print(f"Has image   : {chunk.has_image}")

        # show first 200 chars of chunk text — enough to verify natural boundaries
        print(f"Text preview: {chunk.chunk_text[:200]}...")

    # ── Preview one chunk with image ───────────────────────────────────────────

    print(f"\n--- Sample chunk with image ---")

    # filter to only chunks that have an image attached
    image_chunks = [c for c in chunks if c.has_image]

    if image_chunks:
        sample = image_chunks[0]
        print(f"Chunk ID  : {sample.chunk_id}")
        print(f"Page      : {sample.page_number}")
        print(f"Image URL : {sample.image_url}")
        print(f"Text      : {sample.chunk_text[:300]}...")