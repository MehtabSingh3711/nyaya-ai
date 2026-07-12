from __future__ import annotations

from pathlib import Path
from typing import List, Literal, Optional
from pydantic import BaseModel

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import docx
except ImportError:
    docx = None


class ExtractedPage(BaseModel):
    """Represent a single extracted page from a PDF contract."""
    page_number: int  # 1-indexed
    text: str


class ExtractedContract(BaseModel):
    """Represent the result of text extraction from a contract."""
    contract_name: str
    pages: List[ExtractedPage] = []
    paragraphs: List[str] = []
    status: Literal["success", "ocr_required", "failure"]
    error_message: Optional[str] = None


def extract_contract_text(file_path: Path) -> ExtractedContract:
    """Extract text from PDF or DOCX contract.

    If cumulative extracted text is empty or under 50 characters,
    returns status='ocr_required'.

    Args:
        file_path: Absolute or relative Path to the contract file.

    Returns:
        ExtractedContract object containing extracted content and status.
    """
    path = Path(file_path)
    contract_name = path.name
    suffix = path.suffix.lower()

    if not path.exists():
        return ExtractedContract(
            contract_name=contract_name,
            status="failure",
            error_message=f"File not found: {path}",
        )

    if suffix == ".pdf":
        if fitz is None:
            return ExtractedContract(
                contract_name=contract_name,
                status="failure",
                error_message="PyMuPDF is not installed. Install with: pip install pymupdf",
            )
        try:
            doc = fitz.open(path)
            pages = []
            total_char_count = 0
            for i, page in enumerate(doc):
                text = page.get_text()
                total_char_count += len(text.strip())
                pages.append(ExtractedPage(page_number=i + 1, text=text))

            if total_char_count < 50:
                return ExtractedContract(
                    contract_name=contract_name,
                    pages=pages,
                    status="ocr_required",
                    error_message="Extracted text is under 50 characters; PDF might be scanned and require OCR.",
                )

            return ExtractedContract(
                contract_name=contract_name,
                pages=pages,
                status="success",
            )
        except Exception as e:
            return ExtractedContract(
                contract_name=contract_name,
                status="failure",
                error_message=f"Failed to parse PDF: {e}",
            )

    elif suffix in [".docx", ".doc"]:
        if docx is None:
            return ExtractedContract(
                contract_name=contract_name,
                status="failure",
                error_message="python-docx is not installed. Install with: pip install python-docx",
            )
        try:
            doc = docx.Document(path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            total_char_count = sum(len(p) for p in paragraphs)

            if total_char_count < 50:
                return ExtractedContract(
                    contract_name=contract_name,
                    status="ocr_required",
                    error_message="Extracted text is under 50 characters; document might be empty.",
                )

            return ExtractedContract(
                contract_name=contract_name,
                paragraphs=paragraphs,
                status="success",
            )
        except Exception as e:
            return ExtractedContract(
                contract_name=contract_name,
                status="failure",
                error_message=f"Failed to parse DOCX: {e}",
            )

    else:
        return ExtractedContract(
            contract_name=contract_name,
            status="failure",
            error_message=f"Unsupported file format: {suffix}. Only PDF and DOCX are supported.",
        )
