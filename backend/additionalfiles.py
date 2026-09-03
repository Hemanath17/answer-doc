"""
additionalfiles.py

Extractors for non-PDF ingestion sources: pasted text, web links, and
YouTube videos. Each function returns a list of {"text": str, "metadata": dict}
records in the same shape your PDF pipeline already produces, so they can be
fed directly into your existing chunk -> embed -> upsert code.
"""

import re
import httpx
import trafilatura
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound


def extract_from_text(title: str, content: str) -> list[dict]:
    if not content or not content.strip():
        raise ValueError("Pasted text is empty.")

    return [{
        "text": content.strip(),
        "metadata": {
            "source_type": "text",
            "title": title or "Pasted Text",
        },
    }]


def _pick_best_image(html: str, base_url: str) -> str | None:
    """
    Returns the single best image URL for a web page, using a priority chain:
      1. og:image / twitter:image meta tag  — author-chosen, usually high quality
      2. trafilatura metadata .image field  — same og:image via trafilatura's parser
      3. First meaningful <img src> in the body — fallback for sites without OG tags

    Returns None when no suitable image is found.
    """
    # Priority 1 & 2: trafilatura's metadata (reads og:image, twitter:image, etc.)
    meta = trafilatura.extract_metadata(html)
    if meta and getattr(meta, "image", None):
        return meta.image

    # Priority 3: lxml walk for in-body <img> tags
    try:
        from lxml import html as lhtml
        doc = lhtml.fromstring(html, base_url=base_url)
        skip_patterns = ("icon", "logo", "avatar", "badge", "button",
                         "1x1", "pixel", "ad", "tracking", ".svg", "data:")
        for src in doc.xpath("//img/@src | //img/@data-src"):
            src = src.strip()
            if not src:
                continue
            # Make relative URLs absolute
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                from urllib.parse import urlparse
                p = urlparse(base_url)
                src = f"{p.scheme}://{p.netloc}{src}"
            if not src.startswith("http"):
                continue
            if any(pat in src.lower() for pat in skip_patterns):
                continue
            return src
    except Exception:
        pass

    return None


def extract_from_url(url: str, timeout: float = 20.0) -> list[dict]:
    # Use a realistic browser UA — bot UAs are blocked by many sites (e.g. 403)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
    }

    try:
        response = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
    except httpx.TimeoutException:
        raise ValueError(f"The URL timed out after {timeout}s — the site may be slow or unreachable.")
    except httpx.HTTPError as e:
        raise ValueError(f"Failed to fetch URL: {e}")

    if response.status_code == 403:
        raise ValueError(
            "This site blocked the request (HTTP 403). "
            "It may require login or actively blocks scrapers."
        )
    if response.status_code == 404:
        raise ValueError("Page not found (HTTP 404). Check the URL and try again.")
    if not response.is_success:
        raise ValueError(f"The site returned HTTP {response.status_code}. Try a different URL.")

    extracted = trafilatura.extract(
        response.text,
        include_comments=False,
        include_tables=True,
        favor_precision=True,
    )

    if not extracted or not extracted.strip():
        raise ValueError(
            "Could not extract readable content from this URL "
            "(it may be JS-rendered or behind a paywall)."
        )

    meta = trafilatura.extract_metadata(response.text)
    page_title = meta.title if meta and meta.title else url

    # Best image for this page (og:image preferred, body img as fallback)
    image_url = _pick_best_image(response.text, base_url=str(response.url))

    record_metadata = {
        "source_type": "url",
        "title": page_title,
        "source_url": url,
    }
    if image_url:
        record_metadata["image_url"] = image_url

    return [{
        "text": extracted.strip(),
        "metadata": record_metadata,
    }]


def _extract_video_id(youtube_url: str) -> str:
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
        r"shorts\/([0-9A-Za-z_-]{11})",
        r"embed\/([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not parse a video ID from: {youtube_url}")


def extract_from_youtube(youtube_url: str, languages: list[str] | None = None) -> list[dict]:
    video_id = _extract_video_id(youtube_url)
    languages = languages or ["en"]

    try:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id, languages=languages)
        transcript = list(fetched)
    except TranscriptsDisabled:
        raise ValueError("Captions are disabled for this video.")
    except NoTranscriptFound:
        raise ValueError(
            f"No transcript found in languages {languages}. "
            "This video may need audio transcription instead (not yet supported)."
        )

    if not transcript:
        raise ValueError("Transcript came back empty.")

    records = []
    buffer_text = []
    buffer_start = transcript[0].start
    window_seconds = 30

    for entry in transcript:
        if entry.start - buffer_start > window_seconds and buffer_text:
            records.append({
                "text": " ".join(buffer_text).strip(),
                "metadata": {
                    "source_type": "youtube",
                    "title": youtube_url,
                    "video_id": video_id,
                    "start_time": buffer_start,
                },
            })
            buffer_text = []
            buffer_start = entry.start

        buffer_text.append(entry.text)

    if buffer_text:
        records.append({
            "text": " ".join(buffer_text).strip(),
            "metadata": {
                "source_type": "youtube",
                "title": youtube_url,
                "video_id": video_id,
                "start_time": buffer_start,
            },
        })

    return records


def ingest_source(source_type: str, **kwargs) -> list[dict]:
    """
    Single entry point your FastAPI routes can call regardless of source type.

    Usage:
        ingest_source("text", title="My Notes", content="...")
        ingest_source("url", url="https://example.com/article")
        ingest_source("youtube", youtube_url="https://youtube.com/watch?v=...")
    """
    if source_type == "text":
        return extract_from_text(kwargs["title"], kwargs["content"])
    elif source_type == "url":
        return extract_from_url(kwargs["url"])
    elif source_type == "youtube":
        return extract_from_youtube(kwargs["youtube_url"])
    else:
        raise ValueError(f"Unknown source_type: {source_type}")
