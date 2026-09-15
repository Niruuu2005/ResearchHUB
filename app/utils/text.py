import re
from typing import List, Tuple


def clean_text(text: str) -> str:
    """Normalize whitespace and strip spurious control characters."""
    if not text:
        return ""
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def detect_section(line: str) -> str:
    """Heuristic section header detection for academic papers."""
    line_clean = line.strip()
    if not line_clean or len(line_clean) > 80:
        return ""

    headers = [
        "abstract",
        "introduction",
        "background",
        "related work",
        "methodology",
        "method",
        "system architecture",
        "experimental setup",
        "experiments",
        "evaluation",
        "results",
        "discussion",
        "limitations",
        "future work",
        "conclusion",
        "references",
        "acknowledgments",
    ]

    # Pattern for numbered headers: 1. Introduction or I. INTRODUCTION
    clean_lower = line_clean.lower()
    clean_lower = re.sub(r"^[0-9ivx]+\.?\s*", "", clean_lower).strip()

    for h in headers:
        if clean_lower == h or clean_lower.startswith(h + " ") or clean_lower.startswith(h + ":"):
            return line_clean.title()

    return ""


def chunk_text(
    pages_text: List[Tuple[int, str]],
    chunk_size: int = 600,
    overlap: int = 100,
) -> List[dict]:
    """
    Split per-page academic text into overlapping chunks with page and section metadata.
    """
    chunks: List[dict] = []
    chunk_index = 0
    current_section = "Introduction"

    for page_num, raw_text in pages_text:
        text = clean_text(raw_text)
        if not text:
            continue

        lines = text.split("\n")
        page_chunks_buffer = []
        current_buffer = ""

        for line in lines:
            detected = detect_section(line)
            if detected:
                current_section = detected

            current_buffer += " " + line.strip()
            if len(current_buffer) >= chunk_size:
                page_chunks_buffer.append(current_buffer.strip())
                # Sliding window overlap
                words = current_buffer.strip().split()
                overlap_words = words[-max(1, overlap // 6):] if len(words) > 20 else []
                current_buffer = " ".join(overlap_words)

        if current_buffer.strip():
            page_chunks_buffer.append(current_buffer.strip())

        for c_text in page_chunks_buffer:
            if len(c_text) < 40:
                continue
            chunks.append({
                "page_number": page_num,
                "section": current_section,
                "chunk_index": chunk_index,
                "content": c_text,
            })
            chunk_index += 1

    return chunks
