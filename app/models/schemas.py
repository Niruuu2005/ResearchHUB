from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class ResearchRequest(BaseModel):
    """Input payload for research queries."""

    topic: str = Field(
        ...,
        description="The research topic or subject to query.",
        min_length=1,
        max_length=200,
        examples=["Quantum Computing"],
    )

    @field_validator("topic", mode="before")
    @classmethod
    def validate_and_strip_topic(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Topic must be a string.")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Topic must not be empty.")
        return cleaned


class Paper(BaseModel):
    """Academic publication metadata model."""

    title: str = Field(..., description="Title of the research paper.")
    authors: List[str] = Field(
        default_factory=list, description="List of author names."
    )
    year: Optional[int] = Field(
        default=None, description="Year of publication."
    )
    source: str = Field(
        ..., description="Academic repository source (e.g., OpenAlex, Crossref)."
    )
    url: Optional[str] = Field(
        default=None, description="Direct URL or DOI resolver link to the paper."
    )
    doi: Optional[str] = Field(
        default=None, description="Digital Object Identifier (DOI)."
    )


class Source(BaseModel):
    """Reference citation source."""

    name: str = Field(..., description="Provider name (e.g. Wikipedia).")
    title: str = Field(..., description="Document or article title.")
    url: str = Field(..., description="Source link URL.")


class ResearchResponse(BaseModel):
    """Aggregated research response payload."""

    topic: str = Field(..., description="The query topic.")
    summary: str = Field(
        ..., description="Introductory topic summary synthesized from sources."
    )
    key_points: List[str] = Field(
        default_factory=list,
        description="Core takeaways and key concepts derived from the summary.",
    )
    papers: List[Paper] = Field(
        default_factory=list,
        description="Normalized and deduplicated list of academic papers.",
    )
    sources: List[Source] = Field(
        default_factory=list, description="Primary sources and references consulted."
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Provider-specific warnings in case of partial failures or timeouts.",
    )


class HealthResponse(BaseModel):
    """Health check response payload."""

    status: str = Field(default="running", description="Current service health status.")
    service: str = Field(default="ResearchLite", description="Name of the microservice.")
    version: Optional[str] = Field(default="1.0.0", description="Service build version.")
