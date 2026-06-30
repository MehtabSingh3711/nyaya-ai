"""Pydantic v2 schemas for Nyaya AI structured output (ADR-005).

Week 2 scope: Mode 2 (Legal Intelligence Chat) schemas only.
Mode 1 schemas (RiskFinding, ClauseExtraction, MSMEViolation) are added
when user contract ingestion is built.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Citation — a single source reference in an answer
# ---------------------------------------------------------------------------
class Citation(BaseModel):
    """A citation pointing to a specific section of an Indian legal Act."""

    source_type: Literal["statute"] = "statute"
    act_name: str = Field(
        ...,
        description="Full name of the Act, e.g. 'Indian Contract Act 1872'",
    )
    section: str = Field(
        ...,
        description="Section or Article number, e.g. '27' or '19(1)(g)'",
    )
    quote: str = Field(
        ...,
        description="Verbatim passage from the source text being cited",
        min_length=1,
    )


# ---------------------------------------------------------------------------
# CitedAnswer — the structured output from the LLM cascade
# ---------------------------------------------------------------------------
class CitedAnswer(BaseModel):
    """A legal answer with citations and confidence assessment.

    This is the contract between the LLM cascade and the display layer.
    Every field must be present and valid before the answer reaches the user.
    """

    answer: str = Field(
        ...,
        description="Plain-language answer to the user's legal question",
        min_length=1,
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="List of source citations supporting the answer",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="LLM self-assessed confidence score (0.0–1.0)",
    )
    can_answer: bool = Field(
        ...,
        description="False when the system cannot answer reliably (cite-or-refuse)",
    )

    @model_validator(mode="after")
    def citations_required_when_answerable(self) -> "CitedAnswer":
        """If the system claims it can answer, it must cite at least one source."""
        if self.can_answer and len(self.citations) == 0:
            raise ValueError(
                "can_answer is True but no citations provided — "
                "every answer must cite at least one source"
            )
        return self


# ---------------------------------------------------------------------------
# CorpusChunk — internal model for a chunk during ingestion
# ---------------------------------------------------------------------------
class CorpusChunk(BaseModel):
    """A single section/article chunk from the statutory corpus.

    Used internally during ingestion. Not returned to the user.
    """

    act_name: str = Field(
        ..., description="Full name of the Act"
    )
    section_number: str = Field(
        ..., description="Section or Article number"
    )
    section_title: Optional[str] = Field(
        default=None, description="Section heading, if available"
    )
    chapter: Optional[str] = Field(
        default=None, description="Chapter number or name"
    )
    text: str = Field(
        ..., description="The chunk text content", min_length=1
    )
    source: str = Field(
        ...,
        description="Provenance — which dataset or file this came from",
    )
    version: str = Field(
        default="v1", description="Corpus version tag"
    )

    def to_payload(self) -> dict:
        """Convert to Qdrant payload dict for upsert."""
        return self.model_dump(exclude_none=True)

    @property
    def dedup_key(self) -> tuple[str, str]:
        """Normalized key for cross-dataset deduplication."""
        title = self.act_name.lower().strip()
        # Strip leading "the " and trailing year
        if title.startswith("the "):
            title = title[4:]
        # Remove trailing 4-digit year
        parts = title.rsplit(" ", 1)
        if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) == 4:
            title = parts[0]
        title = " ".join(title.split())  # collapse whitespace

        section = self.section_number.lower().strip()
        return (title, section)
