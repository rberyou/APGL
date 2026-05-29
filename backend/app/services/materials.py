from io import BytesIO
from pathlib import Path
import re
from dataclasses import dataclass

from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt"}


@dataclass(frozen=True)
class ParsedMaterial:
    text: str
    page_count: int = 0
    text_page_count: int = 0
    character_count: int = 0


def extract_text(filename: str, content_type: str, data: bytes) -> str:
    return extract_material(filename, content_type, data).text


def extract_material(filename: str, content_type: str, data: bytes) -> ParsedMaterial:
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only PDF, Markdown, and text files are supported")

    if extension == ".pdf" or content_type == "application/pdf":
        reader = PdfReader(BytesIO(data))
        pages: list[str] = []
        text_pages = 0
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                text_pages += 1
                pages.append(f"[Page {index}]\n{text.strip()}")
        combined = "\n\n".join(pages).strip()
        return ParsedMaterial(
            text=combined,
            page_count=len(reader.pages),
            text_page_count=text_pages,
            character_count=len(combined),
        )

    text = data.decode("utf-8", errors="ignore").strip()
    return ParsedMaterial(text=text, character_count=len(text))


def chunk_text(text: str, chunk_size: int = 3200) -> list[dict[str, str | int]]:
    normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if not normalized:
        return []

    chunks: list[dict[str, str | int]] = []
    start = 0
    position = 1
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        if end < len(normalized):
            split_at = normalized.rfind("\n\n", start, end)
            if split_at > start + 400:
                end = split_at
        content = normalized[start:end].strip()
        if content:
            first_line = content.splitlines()[0].strip("# ").strip()
            title = first_line[:80] if first_line else f"Chunk {position}"
            page_match = re.search(r"\[Page\s+(\d+)\]", content)
            locator = f"page-{page_match.group(1)}" if page_match else f"chunk-{position}"
            chunks.append(
                {
                    "position": position,
                    "title": title or f"Chunk {position}",
                    "content": content,
                    "locator": locator,
                }
            )
            position += 1
        start = end if end > start else start + chunk_size
    return chunks
