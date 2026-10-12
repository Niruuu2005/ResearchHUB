from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.database import Paper, ProjectPaper, ResearchProject, User
from app.models.schemas import ProjectAddPaper, ProjectCreate, ProjectOut, ProjectUpdate
from app.services.operations_service import OperationsService

router = APIRouter(prefix="/api/projects", tags=["Research Projects"])


@router.get("", response_model=List[ProjectOut], summary="List Research Projects")
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all research projects owned by the authenticated user."""
    projects = (
        db.query(ResearchProject)
        .filter(ResearchProject.user_id == current_user.id)
        .order_by(ResearchProject.created_at.desc())
        .all()
    )
    results = []
    for p in projects:
        paper_count = db.query(ProjectPaper).filter(ProjectPaper.project_id == p.id).count()
        results.append(
            ProjectOut(
                id=p.id,
                name=p.name,
                description=p.description,
                objective=p.objective,
                archived=p.archived,
                created_at=p.created_at,
                updated_at=p.updated_at,
                paper_count=paper_count,
            )
        )
    return results


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED, summary="Create Project")
async def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new research project workspace owned by the authenticated user."""
    project = ResearchProject(
        user_id=current_user.id,
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else "",
        objective=payload.objective.strip() if payload.objective else "",
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    OperationsService.record_audit(db, "project_created", "project", str(project.id), project.name)

    return ProjectOut(
        id=project.id,
        name=project.name,
        description=project.description,
        objective=project.objective,
        archived=project.archived,
        created_at=project.created_at,
        updated_at=project.updated_at,
        paper_count=0,
    )


@router.get("/{project_id}", summary="Get Project Workspace Details")
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve project details along with associated papers for a user-owned project."""
    project = (
        db.query(ResearchProject)
        .filter(ResearchProject.id == project_id, ResearchProject.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    papers = (
        db.query(Paper)
        .join(ProjectPaper, ProjectPaper.paper_id == Paper.id)
        .filter(ProjectPaper.project_id == project_id, Paper.user_id == current_user.id)
        .all()
    )

    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "objective": project.objective,
        "archived": project.archived,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "paper_count": len(papers),
        "papers": [
            {
                "id": p.id,
                "title": p.title,
                "authors": [a.author_name for a in p.authors],
                "year": p.year,
                "source": p.source,
                "venue": p.venue,
                "doi": p.doi,
                "open_access": p.open_access,
                "has_pdf": len(p.documents) > 0,
            }
            for p in papers
        ],
    }


@router.patch("/{project_id}", response_model=ProjectOut, summary="Update Project")
async def update_project(
    project_id: int,
    payload: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update details of a research project owned by the user."""
    project = (
        db.query(ResearchProject)
        .filter(ResearchProject.id == project_id, ResearchProject.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    if payload.name is not None:
        project.name = payload.name.strip()
    if payload.description is not None:
        project.description = payload.description.strip()
    if payload.objective is not None:
        project.objective = payload.objective.strip()
    if payload.archived is not None:
        project.archived = payload.archived

    db.commit()
    db.refresh(project)

    paper_count = db.query(ProjectPaper).filter(ProjectPaper.project_id == project.id).count()
    return ProjectOut(
        id=project.id,
        name=project.name,
        description=project.description,
        objective=project.objective,
        archived=project.archived,
        created_at=project.created_at,
        updated_at=project.updated_at,
        paper_count=paper_count,
    )


@router.delete("/{project_id}", summary="Delete Project")
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a research project owned by the user."""
    project = (
        db.query(ResearchProject)
        .filter(ResearchProject.id == project_id, ResearchProject.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    db.delete(project)
    db.commit()
    OperationsService.record_audit(db, "project_deleted", "project", str(project_id))
    return {"message": "Project deleted successfully"}


@router.post("/{project_id}/papers", summary="Add Paper to Project")
async def add_paper_to_project(
    project_id: int,
    payload: ProjectAddPaper,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a paper to a project workspace, verifying user ownership for both resources."""
    project = (
        db.query(ResearchProject)
        .filter(ResearchProject.id == project_id, ResearchProject.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    paper = (
        db.query(Paper)
        .filter(Paper.id == payload.paper_id, Paper.user_id == current_user.id)
        .first()
    )
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")

    link = db.query(ProjectPaper).filter(
        ProjectPaper.project_id == project_id,
        ProjectPaper.paper_id == payload.paper_id,
    ).first()

    if not link:
        new_link = ProjectPaper(project_id=project_id, paper_id=payload.paper_id)
        db.add(new_link)
        db.commit()

    return {"message": "Paper assigned to project successfully"}


@router.delete("/{project_id}/papers/{paper_id}", summary="Remove Paper from Project")
async def remove_paper_from_project(
    project_id: int,
    paper_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a paper from a project workspace owned by the user."""
    project = (
        db.query(ResearchProject)
        .filter(ResearchProject.id == project_id, ResearchProject.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    link = db.query(ProjectPaper).filter(
        ProjectPaper.project_id == project_id,
        ProjectPaper.paper_id == paper_id,
    ).first()
    if link:
        db.delete(link)
        db.commit()
    return {"message": "Paper removed from project"}
