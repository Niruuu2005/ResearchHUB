import hashlib


def compute_sha256(content: bytes) -> str:
    """Compute hex SHA-256 checksum for document validation and deduplication."""
    hasher = hashlib.sha256()
    hasher.update(content)
    return hasher.hexdigest()
