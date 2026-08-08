import pdfplumber
import pymupdf as fitz
import os
import io
import json                          # NEW
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from tqdm import tqdm
from typing import List
from pydantic import BaseModel       # NEW

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)


# NEW — Pydantic model for one parsed page
class ParsedPage(BaseModel):
    page_number: int
    text: str
    tables: List[str]
    images: List[str]
    has_image: bool
    char_count: int


CACHE_FILE = "parsed_pages.jsonl"   # NEW


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
    doc = fitz.open(pdf_path)
    page = doc[page_number]
    image_urls = []

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
            image_urls.append(image_url)

    doc.close()
    return image_urls


def parse_pdf(file_path: str) -> List[ParsedPage]:

    # NEW — load from cache if it exists
    if os.path.exists(CACHE_FILE):
        print(f"Cache found — loading from {CACHE_FILE}")
        pages = []
        with open(CACHE_FILE, "r") as f:
            for line in f:
                data = json.loads(line)
                pages.append(ParsedPage(**data))
        print(f"Loaded {len(pages)} pages from cache in seconds.")
        return pages

    # if no cache — run full parsing
    print("No cache found — running full parser...")
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

            image_urls = extract_images_from_page(file_path, page_number)

            # NEW — Pydantic model instead of raw dict
            page_data = ParsedPage(
                page_number=page_number + 1,
                text=text.strip(),
                tables=markdown_tables,
                images=image_urls,
                has_image=len(image_urls) > 0,   # NEW field
                char_count=len(text.strip())      # NEW field
            )

            pages.append(page_data)

    # NEW — save to JSONL cache after parsing
    print(f"\nSaving to cache: {CACHE_FILE}")
    with open(CACHE_FILE, "w") as f:
        for page in pages:
            f.write(page.model_dump_json() + "\n")
    print(f"Saved {len(pages)} pages to cache.")

    return pages


if __name__ == "__main__":
    pages = parse_pdf("Astronomy Basics.pdf")

    print(f"\nTotal pages: {len(pages)}")

    for page in pages:
        print(f"\n{'='*50}")
        print(f"Page       : {page.page_number}")
        print(f"Characters : {page.char_count}")
        print(f"Tables     : {len(page.tables)}")
        print(f"Has image  : {page.has_image}")
        print(f"Images     : {len(page.images)}")

        if page.tables:
            print(f"\n  --- Table Preview ---")
            print(page.tables[0])

        if page.images:
            print(f"\n  --- Image URLs ---")
            for url in page.images:
                print(f"    {url}")