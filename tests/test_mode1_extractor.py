from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from nyaya_ai.contracts.extractor import extract_contract_text


@patch("fitz.open")
def test_extract_contract_text_pdf_success(mock_fitz):
    # Mock PyMuPDF page and doc
    mock_page = MagicMock()
    mock_page.get_text.return_value = "This is a contract clause. It contains enough characters to be successfully parsed as text."
    mock_doc = MagicMock()
    mock_doc.__iter__.return_value = [mock_page]
    mock_fitz.return_value = mock_doc

    with patch.object(Path, "exists", return_value=True):
        res = extract_contract_text(Path("dummy.pdf"))
        assert res.status == "success"
        assert len(res.pages) == 1
        assert res.pages[0].page_number == 1
        assert "contract clause" in res.pages[0].text


@patch("fitz.open")
def test_extract_contract_text_pdf_ocr_required(mock_fitz):
    # Mock PyMuPDF page returning no text (scanned PDF)
    mock_page = MagicMock()
    mock_page.get_text.return_value = "   \n "
    mock_doc = MagicMock()
    mock_doc.__iter__.return_value = [mock_page]
    mock_fitz.return_value = mock_doc

    with patch.object(Path, "exists", return_value=True):
        res = extract_contract_text(Path("scanned.pdf"))
        assert res.status == "ocr_required"
        assert len(res.pages) == 1


@patch("docx.Document")
def test_extract_contract_text_docx_success(mock_docx):
    # Mock docx paragraphs
    p1 = MagicMock()
    p1.text = "This is paragraph 1 of the docx contract."
    p2 = MagicMock()
    p2.text = "This is paragraph 2 of the docx contract with extra text."
    mock_doc = MagicMock()
    mock_doc.paragraphs = [p1, p2]
    mock_docx.return_value = mock_doc

    with patch.object(Path, "exists", return_value=True):
        res = extract_contract_text(Path("dummy.docx"))
        assert res.status == "success"
        assert len(res.paragraphs) == 2
        assert res.paragraphs[0] == "This is paragraph 1 of the docx contract."


def test_extract_contract_text_unsupported():
    with patch.object(Path, "exists", return_value=True):
        res = extract_contract_text(Path("dummy.xyz"))
        assert res.status == "failure"
        assert "Unsupported file format" in res.error_message


def test_extract_contract_text_txt_success():
    # Mock read_text to simulate successful text file extraction
    with patch.object(Path, "exists", return_value=True):
        with patch.object(Path, "read_text", return_value="Paragraph 1\n\nParagraph 2"):
            res = extract_contract_text(Path("dummy.txt"))
            assert res.status == "success"
            assert len(res.paragraphs) == 2
            assert res.paragraphs[0] == "Paragraph 1"
            assert res.paragraphs[1] == "Paragraph 2"


def test_extract_contract_text_not_found():
    res = extract_contract_text(Path("nonexistent.pdf"))
    assert res.status == "failure"
    assert "File not found" in res.error_message
