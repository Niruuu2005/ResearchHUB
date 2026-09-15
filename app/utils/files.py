import os
import re
from pathlib import Path


def sanitize_filename(filename: str) -> str:
    """Sanitize user-uploaded filename to prevent directory traversal and special chars."""
    basename = os.path.basename(filename)
    # Strip dangerous characters
    cleaned = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", basename)
    return cleaned[:100] if cleaned else "document.pdf"


def validate_pdf_content(content: bytes) -> bool:
    """Validate that file starts with PDF magic number '%PDF-'."""
    return content.startswith(b"%PDF-")
