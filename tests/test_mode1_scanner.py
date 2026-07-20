from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from nyaya_ai.contracts.extractor import ExtractedContract, ExtractedPage
from nyaya_ai.contracts.scanner import scan_contract, verify_grounding
from nyaya_ai.schemas import ContractScanResult, RiskAssessment, ClauseExtraction

# ===================================================================
# verify_grounding unit tests
# ===================================================================

def test_verify_grounding_success():
    retrieved = [
        {
            "act_name": "The Indian Contract Act, 1872",
            "section_number": "27",
            "text": "Every agreement by which any one is restrained from trade is void.",
        }
    ]
    assessment = RiskAssessment(
        risk_level="high",
        conflicting_act="Indian Contract Act 1872",
        conflicting_section="27",
        conflicting_law_quote="restrained from trade is void",
        explanation="Void non-compete.",
        recommended_action="Remove.",
        confidence=0.9,
        clause_type="non_compete",
    )
    assert verify_grounding(assessment, retrieved) is True


def test_verify_grounding_act_mismatch():
    retrieved = [
        {
            "act_name": "Information Technology Act 2000",
            "section_number": "43A",
            "text": "Where a body corporate fails to protect data...",
        }
    ]
    # LLM hallucinates Companies Act
    assessment = RiskAssessment(
        risk_level="medium",
        conflicting_act="Companies Act 2013",
        conflicting_section="43A",
        conflicting_law_quote="fails to protect data",
        explanation="Hallucination.",
        recommended_action="Remove.",
        confidence=0.9,
        clause_type="liability",
    )
    assert verify_grounding(assessment, retrieved) is False


def test_verify_grounding_quote_mismatch():
    retrieved = [
        {
            "act_name": "Indian Contract Act 1872",
            "section_number": "27",
            "text": "Every agreement in restraint of trade is void.",
        }
    ]
    # LLM quotes a law that is not in the text
    assessment = RiskAssessment(
        risk_level="high",
        conflicting_act="Indian Contract Act 1872",
        conflicting_section="27",
        conflicting_law_quote="all non-competes are criminal offences in India",
        explanation="Quote not grounded.",
        recommended_action="Remove.",
        confidence=0.9,
        clause_type="non_compete",
    )
    assert verify_grounding(assessment, retrieved) is False


# ===================================================================
# scan_contract integration-style mock tests
# ===================================================================

@pytest.fixture
def mock_pipeline():
    with patch("nyaya_ai.contracts.scanner.extract_contract_text") as mock_extract, \
         patch("nyaya_ai.contracts.scanner.Embedder") as mock_embed_cls, \
         patch("nyaya_ai.contracts.scanner.Reranker") as mock_reranker_cls, \
         patch("nyaya_ai.contracts.scanner.qdrant") as mock_qdrant, \
         patch("nyaya_ai.contracts.scanner.cascade_risk_assessment") as mock_cascade:
        
        # Setup Embedder with hybrid support
        embedder = MagicMock()
        embedder.embed_query.return_value = [0.1] * 1024
        # Mock hybrid query output
        hybrid_result = MagicMock()
        hybrid_result.dense = [0.1] * 1024
        hybrid_result.sparse = {1: 0.5, 10: 0.3}
        embedder.embed_query_hybrid.return_value = hybrid_result
        mock_embed_cls.return_value = embedder

        # Setup Reranker — identity rerank (pass through candidates as-is, ensuring rerank_score is set)
        def mock_rerank_side_effect(query, candidates, top_k, **kw):
            res = []
            for c in candidates[:top_k]:
                enriched = dict(c)
                if "rerank_score" not in enriched:
                    enriched["rerank_score"] = enriched.get("score", 0.5)
                res.append(enriched)
            return res

        reranker = MagicMock()
        reranker.rerank.side_effect = mock_rerank_side_effect
        mock_reranker_cls.return_value = reranker
        
        yield mock_extract, mock_qdrant, mock_cascade


def test_scan_contract_non_compete_case(mock_pipeline):
    mock_extract, mock_qdrant, mock_cascade = mock_pipeline
    
    # 1. Mock Extractor returning success
    mock_extract.return_value = ExtractedContract(
        contract_name="employment.pdf",
        pages=[ExtractedPage(page_number=1, text="1. Non-compete: Employee shall not compete for 2 years.")],
        status="success",
    )
    
    # 2. Mock Qdrant returning relevant ICA 1872 chunk
    mock_qdrant.search.return_value = [
        {
            "act_name": "Indian Contract Act 1872",
            "section_number": "27",
            "text": "Every agreement in restraint of trade is void.",
            "score": 0.85,  # Above threshold
        }
    ]
    
    # 3. Mock LLM cascade returning high risk non-compete finding
    mock_cascade.return_value = RiskAssessment(
        risk_level="high",
        conflicting_act="Indian Contract Act 1872",
        conflicting_section="27",
        conflicting_law_quote="restraint of trade is void",
        explanation="Void under section 27.",
        recommended_action="Remove.",
        confidence=0.95,
        clause_type="non_compete",
    )
    
    res = scan_contract(Path("employment.pdf"), relevance_threshold=0.4)
    
    assert res.status == "risks_found"
    assert len(res.findings) == 1
    assert res.findings[0].conflicting_act == "Indian Contract Act 1872"
    assert res.findings[0].conflicting_section == "27"
    assert res.total_clauses_scanned == 1


def test_scan_contract_msme_payment_case(mock_pipeline):
    mock_extract, mock_qdrant, mock_cascade = mock_pipeline
    
    mock_extract.return_value = ExtractedContract(
        contract_name="vendor.docx",
        paragraphs=["1. Payment: Fees shall be paid within 90 days of receipt of invoice."],
        status="success",
    )
    
    mock_qdrant.search.return_value = [
        {
            "act_name": "Micro, Small and Medium Enterprises Development Act 2006",
            "section_number": "15",
            "text": "Payment shall be made within forty-five days.",
            "score": 0.80,  # Above threshold
        }
    ]
    
    mock_cascade.return_value = RiskAssessment(
        risk_level="medium",
        conflicting_act="Micro, Small and Medium Enterprises Development Act 2006",
        conflicting_section="15",
        conflicting_law_quote="within forty-five days",
        explanation="Exceeds 45 days statutory limit.",
        recommended_action="Change to 45 days.",
        confidence=0.90,
        clause_type="payment_term",
    )
    
    res = scan_contract(Path("vendor.docx"), relevance_threshold=0.4)
    
    assert res.status == "risks_found"
    assert len(res.findings) == 1
    assert res.findings[0].conflicting_section == "15"


def test_scan_contract_clean_confidentiality_case(mock_pipeline):
    mock_extract, mock_qdrant, mock_cascade = mock_pipeline
    
    mock_extract.return_value = ExtractedContract(
        contract_name="nda.pdf",
        pages=[ExtractedPage(page_number=1, text="1. Confidentiality: Each party shall keep information confidential.")],
        status="success",
    )
    
    mock_qdrant.search.return_value = [
        {
            "act_name": "Indian Contract Act 1872",
            "section_number": "1",
            "text": "Short title and commencement.",
            "score": 0.45,  # Above threshold (triggers LLM call)
        }
    ]
    
    mock_cascade.return_value = RiskAssessment(
        risk_level="none",
        explanation="Standard NDA clause, no conflicts.",
        confidence=0.92,
        clause_type="other",
    )
    
    res = scan_contract(Path("nda.pdf"), relevance_threshold=0.4)
    
    assert res.status == "no_material_risks_found"
    assert len(res.findings) == 0


def test_scan_contract_relevance_gate_skips(mock_pipeline):
    mock_extract, mock_qdrant, mock_cascade = mock_pipeline
    
    mock_extract.return_value = ExtractedContract(
        contract_name="nda.pdf",
        pages=[ExtractedPage(page_number=1, text="1. Confidentiality: Keep secret.")],
        status="success",
    )
    
    # Qdrant returns low scores
    mock_qdrant.search.return_value = [
        {
            "act_name": "Indian Contract Act 1872",
            "section_number": "1",
            "text": "Short title.",
            "score": 0.25,  # Under 0.40 threshold
        }
    ]
    
    res = scan_contract(Path("nda.pdf"), relevance_threshold=0.4)
    
    # Since score < threshold, LLM should not be called and status is insufficient_evidence
    mock_cascade.assert_not_called()
    assert res.status == "insufficient_evidence"
    assert len(res.findings) == 0


def test_scan_contract_ungrounded_finding_dropped(mock_pipeline):
    mock_extract, mock_qdrant, mock_cascade = mock_pipeline
    
    mock_extract.return_value = ExtractedContract(
        contract_name="employment.pdf",
        pages=[ExtractedPage(page_number=1, text="1. Non-compete: Employee shall not compete.")],
        status="success",
    )
    
    # Qdrant returns ICA 1872 chunk
    mock_qdrant.search.return_value = [
        {
            "act_name": "Indian Contract Act 1872",
            "section_number": "27",
            "text": "Every agreement in restraint of trade is void.",
            "score": 0.85,
        }
    ]
    
    # LLM returns a hallucinated Companies Act 2013 citation
    mock_cascade.return_value = RiskAssessment(
        risk_level="high",
        conflicting_act="Companies Act 2013",  # Mismatch with retrieved ICA Act
        conflicting_section="180",              # Mismatch with section 27
        conflicting_law_quote="restraint of trade is void",
        explanation="Hallucinated Act.",
        recommended_action="Remove.",
        confidence=0.90,
        clause_type="non_compete",
    )
    
    res = scan_contract(Path("employment.pdf"), relevance_threshold=0.4)
    
    # Finding should be dropped due to failing grounding check
    assert len(res.findings) == 0
    assert res.status == "no_material_risks_found"


def test_scan_contract_returns_precedents(mock_pipeline):
    mock_extract, mock_qdrant, mock_cascade = mock_pipeline

    mock_extract.return_value = ExtractedContract(
        contract_name="employment.pdf",
        pages=[ExtractedPage(page_number=1, text="1. Non-compete: Employee shall not compete.")],
        status="success",
    )

    mock_qdrant.search.return_value = [
        {
            "act_name": "Indian Contract Act 1872",
            "section_number": "27",
            "text": "Every agreement in restraint of trade is void.",
            "score": 0.85,
        }
    ]

    from nyaya_ai.schemas import PrecedentCitation
    mock_cascade.return_value = RiskAssessment(
        risk_level="high",
        conflicting_act="Indian Contract Act 1872",
        conflicting_section="27",
        conflicting_law_quote="restraint of trade is void",
        explanation="Void under section 27.",
        recommended_action="Remove.",
        confidence=0.95,
        clause_type="non_compete",
        relevant_precedents=[
            PrecedentCitation(
                case_name="Superintendence Company of India v. Krishan Murgai",
                citation="AIR 1980 SC 1717",
                core_holding="Post-employment non-compete covenants are void ab initio."
            )
        ]
    )

    res = scan_contract(Path("employment.pdf"), relevance_threshold=0.4)

    assert res.status == "risks_found"
    assert len(res.findings) == 1
    assert len(res.findings[0].relevant_precedents) == 1
    assert res.findings[0].relevant_precedents[0].case_name == "Superintendence Company of India v. Krishan Murgai"

