import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.database import ResearchNote
from app.models.schemas import NoteCreate, NoteOut, NoteUpdate

router = APIRouter(prefix="/api/notes", tags=["Notes & Highlights"])


@router.get("", response_model=List[NoteOut], summary="List Notes")
async def list_notes(
    project_id: Optional[int] = None,
    paper_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = db.query(ResearchNote)
    if project_id:
        query = query.filter(ResearchNote.project_id == project_id)
    if paper_id:
        query = query.filter(ResearchNote.paper_id == paper_id)

    notes = query.order_by(ResearchNote.created_at.desc()).all()
    results = []
    for n in notes:
        results.append(
            NoteOut(
                id=n.id,
                title=n.title,
                content=n.content,
                project_id=n.project_id,
                paper_id=n.paper_id,
                page_number=n.page_number,
                tags=json.loads(n.tags_json or "[]"),
                created_at=n.created_at,
                updated_at=n.updated_at,
            )
        )
    return results


@router.post("", response_model=NoteOut, status_code=status.HTTP_201_CREATED, summary="Create Note")
async def create_note(payload: NoteCreate, db: Session = Depends(get_db)):
    note = ResearchNote(
        title=payload.title.strip(),
        content=payload.content.strip(),
        project_id=payload.project_id,
        paper_id=payload.paper_id,
        page_number=payload.page_number,
        tags_json=json.dumps(payload.tags),
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    return NoteOut(
        id=note.id,
        title=note.title,
        content=note.content,
        project_id=note.project_id,
        paper_id=note.paper_id,
        page_number=note.page_number,
        tags=payload.tags,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.patch("/{note_id}", response_model=NoteOut, summary="Update Note")
async def update_note(note_id: int, payload: NoteUpdate, db: Session = Depends(get_db)):
    note = db.query(ResearchNote).filter(ResearchNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found.")

    if payload.title is not None:
        note.title = payload.title.strip()
    if payload.content is not None:
        note.content = payload.content.strip()
    if payload.page_number is not None:
        note.page_number = payload.page_number
    if payload.tags is not None:
        note.tags_json = json.dumps(payload.tags)

    db.commit()
    db.refresh(note)

    return NoteOut(
        id=note.id,
        title=note.title,
        content=note.content,
        project_id=note.project_id,
        paper_id=note.paper_id,
        page_number=note.page_number,
        tags=json.loads(note.tags_json or "[]"),
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.delete("/{note_id}", summary="Delete Note")
async def delete_note(note_id: int, db: Session = Depends(get_db)):
    note = db.query(ResearchNote).filter(ResearchNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found.")
    db.delete(note)
    db.commit()
    return {"message": "Note deleted successfully"}
