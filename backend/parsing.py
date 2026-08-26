import pdfplumber
import pymupdf as fitz
import os
import io
import json
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from tqdm import tqdm
from typing import List, Optional
from pydantic import BaseModel
from openai import OpenAI

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# NEW — OpenAI client for Vision descriptions. Same key you already
# use for embeddings and generation — no new API account needed.
openai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=30.0
)


class ParsedPage(BaseModel):
    page_number: int
    text: str
    tables: List[str]
    images: List[str]
    has_image: bool
    char_count: int
    # NEW — one description per image in `images`, same order/index.
    # Empty string if a description failed to generate for that image.
    image_descriptions: List[str]


CACHE_FILE = "parsed_pages.jsonl"


def upload_image_to_cloudinary(image_bytes, filename):
    try:
        image_file = io.BytesIO(image_bytes)
        response = cloudinary.uploader.upload(
            image_file,
            public_id=filename,
            folder="pdf_rag_images",
            overwrite=True
        )
        return response["secure_url"]
    except Exception as e:
        print(f"Image upload failed for {filename}: {e}")
        return None


def describe_image_with_vision(image_url: str) -> str:
    """
    Sends an already-uploaded Cloudinary image URL to GPT-4o mini's
    vision capability and asks for a detailed text description.

    This is the core of Path 2 — the description gets embedded as
    regular text alongside the chunk, making the image's CONTENT
    (not just its existence) searchable and answerable.

    Wrapped in try/except — a failed description for one image
    should not stop parsing the rest of the PDF. Returns empty
    string on failure, same pattern used elsewhere in this file.
    """
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url}
                        },
                        {
                            "type": "text",
                            "text": (
                                "Describe this image from an astronomy textbook "
                                "in detail. If it is a diagram (e.g. a telescope "
                                "design, mount type, or sky chart), describe its "
                                "components, labels, and how they are arranged. "
                                "If it is a photograph (e.g. a planet, nebula, or "
                                "the Moon), describe what is visible in it. "
                                "Be specific and factual — this description will "
                                "be used to answer questions about the image, so "
                                "include any labeled parts, shapes, or notable "
                                "visual details. Keep it to 3-5 sentences."
                            )
                        }
                    ]
                }
            ],
            max_tokens=300
        )

        description = response.choices[0].message.content.strip()
        print(f"  Vision description generated ({len(description)} chars)")
        return description

    except Exception as e:
        print(f"  Vision description failed for {image_url}: {e}")
        return ""


def table_to_markdown(table):
    if not table or len(table) == 0:
        return ""

    header = table[0]
    header = [cell if cell else "" for cell in header]

    markdown = "| " + " | ".join(header) + " |\n"
    markdown += "| " + " | ".join(["---"] * len(header)) + " |\n"

    for row in table[1:]:
        row = [cell if cell else "" for cell in row]
        markdown += "| " + " | ".join(row) + " |\n"

    return markdown


def extract_images_from_page(pdf_path, page_number):
    """
    CHANGED — now returns a tuple of (image_urls, image_descriptions)
    instead of just image_urls. Each image gets uploaded to Cloudinary
    AND immediately described via Vision, keeping both lists in the
    same order so image_urls[i] always corresponds to
    image_descriptions[i].
    """
    doc = fitz.open(pdf_path)
    page = doc[page_number]
    image_urls = []
    image_descriptions = []

    image_list = page.get_images(full=True)

    for img_index, img in enumerate(image_list):
        xref = img[0]
        base_image = doc.extract_image(xref)

        image_bytes = base_image["image"]
        width = base_image["width"]
        height = base_image["height"]

        if width < 100 or height < 100:
            continue

        filename = f"page{page_number + 1}_img{img_index + 1}"
        image_url = upload_image_to_cloudinary(image_bytes, filename)

        if image_url:
            print(f"  Describing image: {filename}")
            description = describe_image_with_vision(image_url)

            image_urls.append(image_url)
            image_descriptions.append(description)

    doc.close()
    return image_urls, image_descriptions


def parse_pdf(file_path: str) -> List[ParsedPage]:

    if os.path.exists(CACHE_FILE):
        print(f"Cache found — loading from {CACHE_FILE}")
        pages = []
        with open(CACHE_FILE, "r") as f:
            for line in f:
                data = json.loads(line)
                pages.append(ParsedPage(**data))
        print(f"Loaded {len(pages)} pages from cache in seconds.")
        return pages

    print("No cache found — running full parser (with Vision descriptions)...")
    pages = []

    with pdfplumber.open(file_path) as pdf:
        for page_number, page in enumerate(tqdm(pdf.pages, desc="Processing pages")):
            print(f"Processing page {page_number + 1} of {len(pdf.pages)}...")

            text = page.extract_text()
            if text is None:
                text = ""

            tables = page.extract_tables()
            markdown_tables = []
            for table in tables:
                markdown = table_to_markdown(table)
                if markdown:
                    markdown_tables.append(markdown)

            # CHANGED — unpack the tuple now returned by extract_images_from_page
            image_urls, image_descriptions = extract_images_from_page(file_path, page_number)

            page_data = ParsedPage(
                page_number=page_number + 1,
                text=text.strip(),
                tables=markdown_tables,
                images=image_urls,
                has_image=len(image_urls) > 0,
                char_count=len(text.strip()),
                image_descriptions=image_descriptions
            )

            pages.append(page_data)

    print(f"\nSaving to cache: {CACHE_FILE}")
    with open(CACHE_FILE, "w") as f:
        for page in pages:
            f.write(page.model_dump_json() + "\n")
    print(f"Saved {len(pages)} pages to cache.")

    return pages


def parse_txt(file_path: str) -> List[ParsedPage]:
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read().strip()

    return [ParsedPage(
        page_number=1,
        text=text,
        tables=[],
        images=[],
        has_image=False,
        char_count=len(text),
        image_descriptions=[]
    )]


def parse_csv(file_path: str) -> List[ParsedPage]:
    import csv

    rows = []
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        return [ParsedPage(page_number=1, text="", tables=[], images=[], has_image=False, char_count=0, image_descriptions=[])]

    headers = rows[0]
    markdown = "| " + " | ".join(headers) + " |\n"
    markdown += "| " + " | ".join(["---"] * len(headers)) + " |\n"
    for row in rows[1:]:
        padded = row + [""] * max(0, len(headers) - len(row))
        markdown += "| " + " | ".join(padded[:len(headers)]) + " |\n"

    raw_text = "\n".join([", ".join(row) for row in rows])
    combined = f"{markdown}\n\n{raw_text}"

    return [ParsedPage(
        page_number=1,
        text=combined,
        tables=[markdown],
        images=[],
        has_image=False,
        char_count=len(combined),
        image_descriptions=[]
    )]


def parse_file(file_path: str, ext: str) -> List[ParsedPage]:
    ext = ext.lower()
    if ext == ".pdf":
        return parse_pdf(file_path)
    elif ext == ".txt":
        return parse_txt(file_path)
    elif ext == ".csv":
        return parse_csv(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


if __name__ == "__main__":
    pages = parse_pdf("Astronomy Basics.pdf")

    print(f"\nTotal pages: {len(pages)}")

    for page in pages: 
        if page.has_image:
            print(f"\n{'='*50}")
            print(f"Page {page.page_number} — has {len(page.images)} image(s)")
            for i, (url, desc) in enumerate(zip(page.images, page.image_descriptions)):
                print(f"\n  Image {i+1}: {url}")
                print(f"  Description: {desc}")