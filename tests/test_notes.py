import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_notes_full_crud_lifecycle():
    # 1. Create a project
    proj_res = client.post(
        "/api/projects",
        json={"name": "Notes Verification Project", "description": "Testing note linkage"},
    )
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]

    # 2. Create note linked to project
    note_res = client.post(
        "/api/notes",
        json={
            "title": "Transformer Attention Scaling Note",
            "content": "Attention matrix computation scales quadratically unless sparse mechanisms are applied.",
            "project_id": proj_id,
            "tags": ["transformers", "attention", "complexity"],
        },
    )
    assert note_res.status_code == 201
    note = note_res.json()
    assert note["id"] is not None
    assert note["title"] == "Transformer Attention Scaling Note"
    assert "transformers" in note["tags"]
    note_id = note["id"]

    # 3. List notes filtered by project_id
    list_res = client.get(f"/api/notes?project_id={proj_id}")
    assert list_res.status_code == 200
    notes = list_res.json()
    assert len(notes) >= 1
    assert any(n["id"] == note_id for n in notes)

    # 4. Update note
    patch_res = client.patch(
        f"/api/notes/{note_id}",
        json={"title": "Transformer Attention Scaling (Revised)"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Transformer Attention Scaling (Revised)"

    # 5. Delete note
    del_res = client.delete(f"/api/notes/{note_id}")
    assert del_res.status_code == 200

    # 6. Verify 404 after deletion
    verify_del = client.delete(f"/api/notes/{note_id}")
    assert verify_del.status_code == 404
