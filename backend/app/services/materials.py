from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt"}


def extract_text(filename: str, content_type: str, data: bytes) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only PDF, Markdown, and text files are supported")

    if extension == ".pdf" or content_type == "application/pdf":
        reader = PdfReader(BytesIO(data))
        pages: list[str] = []
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"[Page {index}]\n{text.strip()}")
        return "\n\n".join(pages).strip()

    return data.decode("utf-8", errors="ignore").strip()


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
            chunks.append(
                {
                    "position": position,
                    "title": title or f"Chunk {position}",
                    "content": content,
                    "locator": f"chunk-{position}",
                }
            )
            position += 1
        start = end if end > start else start + chunk_size
    return chunks
