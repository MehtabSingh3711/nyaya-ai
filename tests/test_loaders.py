"""Unit tests for statutory corpus loaders."""

from unittest.mock import MagicMock, patch
import pytest

from nyaya_ai.ingest.dedup import DedupRegistry
from nyaya_ai.ingest.loaders import load_gsms_b
from nyaya_ai.schemas import CorpusChunk


@pytest.fixture
def registry():
    return DedupRegistry()


@patch("datasets.load_dataset")
def test_load_gsms_b_success(mock_load_dataset, registry):
    # Mock Hugging Face dataset rows
    mock_dataset = [
        {
            "act": "Bharatiya Nyaya Sanhita, 2023",
            "section_number": "1",
            "text": "1. Short title, commencement and application.—(1) This Act may be called the Bharatiya Nyaya Sanhita, 2023...",
        },
        {
            "act": "Bharatiya Nyaya Sanhita, 2023",
            "section_number": "2",
            "text": "2. Definitions.—In this Sanhita, unless the context otherwise requires...",
        },
        {
            "act": "Invalid Row",
            "section_number": "",
            "text": "",  # Empty text, should be skipped
        }
    ]
    mock_load_dataset.return_value = mock_dataset

    chunks = load_gsms_b(registry)

    # Expected: 2 valid chunks loaded (empty row skipped)
    assert len(chunks) == 2
    assert chunks[0].act_name == "Bharatiya Nyaya Sanhita, 2023"
    assert chunks[0].section_number == "1"
    assert "Short title" in chunks[0].text
    assert chunks[0].source == "GSMS-B/indian-legal-sections-bns-bnss-bsa-2023"

    assert chunks[1].section_number == "2"
    assert "Definitions" in chunks[1].text
