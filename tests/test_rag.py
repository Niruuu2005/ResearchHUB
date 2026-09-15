import pytest
from app.services.embedding_service import EmbeddingService
from app.utils.text import chunk_text, clean_text, detect_section
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_chunking_and_section_detection():
    sample_pages = [
        (1, "1. Introduction\nLarge language models present novel security vulnerabilities."),
        (2, "2. Methodology\nWe evaluate tool invocation policies using adversarial test cases.\n3. Results\nEmpirical failure rate dropped by 42%."),
    ]
    chunks = chunk_text(sample_pages, chunk_size=50, overlap=10)
    assert len(chunks) >= 2
    assert chunks[0]["page_number"] == 1
    assert "section" in chunks[0]
    assert chunks[0]["content"] is not None


def test_embedding_service_cosine_similarity():
    service = EmbeddingService()
    vec1 = service.embed_text("Deep neural networks for computer vision")
    vec2 = service.embed_text("Convolutional architectures for image classification")
    vec3 = service.embed_text("Macroeconomics monetary policy and inflation")

    sim_related = service.cosine_similarity(vec1, vec2)
    sim_unrelated = service.cosine_similarity(vec1, vec3)

    assert sim_related > -1.0 and sim_related <= 1.0
    assert sim_unrelated > -1.0 and sim_unrelated <= 1.0


def test_library_chat_endpoint():
    res = client.post("/api/chat/library", json={"question": "What is agentic AI security?"})
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert "citations" in data
    assert len(data["answer"]) > 10
