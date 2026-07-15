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

    Amendment fields (ADR-012):
        amendment_status: Tracks whether this section is the original text,
            has been amended, omitted, or the parent Act repealed.
        amended_by: Name of the amending Act (e.g. "IT (Amendment) Act, 2008").
        amendment_year: Year the amendment was enacted.
        last_verified_source: URL or name of the authoritative source used
            to verify this text (e.g. "indiacode.nic.in").
        last_verified_date: ISO date string of when the text was last verified.
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

    # --- Amendment metadata (ADR-012) ---
    amendment_status: Literal[
        "original", "amended", "omitted", "repealed"
    ] = Field(
        default="original",
        description=(
            "Lifecycle status of this section: "
            "'original' = unamended text from initial corpus, "
            "'amended' = text updated by a subsequent amendment Act, "
            "'omitted' = section removed/omitted by amendment, "
            "'repealed' = entire parent Act repealed"
        ),
    )
    amended_by: Optional[str] = Field(
        default=None,
        description="Name of the amending Act, e.g. 'IT (Amendment) Act, 2008'",
    )
    amendment_year: Optional[int] = Field(
        default=None,
        description="Year the amendment was enacted",
    )
    last_verified_source: Optional[str] = Field(
        default=None,
        description="Authoritative source URL or name, e.g. 'indiacode.nic.in'",
    )
    last_verified_date: Optional[str] = Field(
        default=None,
        description="ISO date (YYYY-MM-DD) when the text was last verified",
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


# ---------------------------------------------------------------------------
# ClauseExtraction — structure of a single clause extracted from a contract
# ---------------------------------------------------------------------------
class ClauseExtraction(BaseModel):
    """Represent a structured clause extracted from a user's contract."""

    contract_id: str = Field(..., description="Unique ID for the contract")
    contract_name: str = Field(..., description="Name of the contract file")
    clause_number: str = Field(..., description="Clause section number or key")
    clause_text: str = Field(..., description="Verbatim text of the clause")
    page: int = Field(..., description="1-indexed page number (0 if not applicable)")
    clause_type: Literal[
        "payment_term",
        "termination",
        "liability",
        "IP",
        "non_compete",
        "indemnity",
        "arbitration",
        "other",
    ] = Field(..., description="Primary category of the clause")
    clause_type_detail: Optional[str] = Field(
        default=None, description="Sub-type or specific clause details"
    )

    def to_payload(self) -> dict:
        """Convert to Qdrant payload dict for contract storage."""
        return self.model_dump(exclude_none=True)


# ---------------------------------------------------------------------------
# RiskFinding — an identified risk or conflict with statutory law
# ---------------------------------------------------------------------------
class RiskFinding(BaseModel):
    """A grounded contract risk finding pointing to a conflict with statutory law."""

    clause_number: str = Field(..., description="Clause section number")
    clause_text: str = Field(..., description="Verbatim contract clause text")
    page: int = Field(..., description="1-indexed page number of the clause")
    clause_type: str = Field(..., description="Category of the clause")
    risk_level: Literal["high", "medium", "low"] = Field(..., description="Identified risk level")
    conflicting_act: str = Field(
        ..., description="Name of the conflicting Act (e.g. 'Indian Contract Act 1872')"
    )
    conflicting_section: str = Field(
        ..., description="Section number of the conflicting statute (e.g. '27')"
    )
    conflicting_law_quote: str = Field(
        ..., description="Verbatim statutory quote that conflicts with the clause"
    )
    explanation: str = Field(
        ..., description="Detailed explanation of the conflict and risk reasoning"
    )
    recommended_action: str = Field(
        ..., description="Recommended mitigation step or negotiation advice"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Self-assessed analysis confidence"
    )


# ---------------------------------------------------------------------------
# RiskAssessment — internal model for LLM risk assessment response
# ---------------------------------------------------------------------------
class RiskAssessment(BaseModel):
    """Internal model for structured LLM contract risk assessment."""

    risk_level: Literal["high", "medium", "low", "none"] = Field(
        ..., description="Assessed risk level, or 'none' if no conflict exists"
    )
    conflicting_act: Optional[str] = Field(
        default=None, description="Conflicting Act name, required if risk exists"
    )
    conflicting_section: Optional[str] = Field(
        default=None, description="Conflicting section number, required if risk exists"
    )
    conflicting_law_quote: Optional[str] = Field(
        default=None, description="Verbatim quote from conflicting statute, required if risk exists"
    )
    explanation: str = Field(
        ..., description="Detailed reasoning explaining the assessment"
    )
    recommended_action: Optional[str] = Field(
        default=None, description="Actionable recommendation, required if risk exists"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Self-assessed confidence (0.0 to 1.0)"
    )
    clause_type: Literal[
        "payment_term",
        "termination",
        "liability",
        "IP",
        "non_compete",
        "indemnity",
        "arbitration",
        "other",
    ] = Field(..., description="Refined category of the clause")
    clause_type_detail: Optional[str] = Field(
        default=None, description="Refined sub-type detail"
    )

    @model_validator(mode="after")
    def validate_risk_fields_present_when_risky(self) -> "RiskAssessment":
        """Verify that conflicting law fields are populated when risk_level is not 'none'."""
        if self.risk_level != "none":
            missing = []
            if not self.conflicting_act:
                missing.append("conflicting_act")
            if not self.conflicting_section:
                missing.append("conflicting_section")
            if not self.conflicting_law_quote:
                missing.append("conflicting_law_quote")
            if not self.recommended_action:
                missing.append("recommended_action")

            if missing:
                raise ValueError(
                    f"Risk level is '{self.risk_level}', but the following "
                    f"required fields are missing: {', '.join(missing)}"
                )
        return self


# ---------------------------------------------------------------------------
# ContractScanResult — final scan report returned to the user
# ---------------------------------------------------------------------------
class ContractScanResult(BaseModel):
    """The final contract scan result containing findings and analysis metadata."""

    contract_name: str = Field(..., description="Name of the scanned contract file")
    total_clauses_scanned: int = Field(..., description="Total count of contract clauses parsed")
    findings: List[RiskFinding] = Field(
        default_factory=list, description="List of identified statutory risks"
    )
    scan_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Overall scan confidence score"
    )
    status: Literal[
        "risks_found",
        "no_material_risks_found",
        "insufficient_evidence",
        "ocr_required",
    ] = Field(..., description="Consolidated scanning status")
    message: str = Field(..., description="Summary status message for the user")

