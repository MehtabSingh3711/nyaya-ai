import pytest
from pydantic import ValidationError
from nyaya_ai.schemas import ClauseExtraction, RiskFinding, RiskAssessment, ContractScanResult

def test_clause_extraction_valid():
    clause = ClauseExtraction(
        contract_id="c123",
        contract_name="test.pdf",
        clause_number="1.1",
        clause_text="This is a test clause.",
        page=1,
        clause_type="payment_term",
        clause_type_detail="30 days",
    )
    assert clause.contract_id == "c123"
    assert clause.clause_type == "payment_term"

def test_clause_extraction_invalid_type():
    with pytest.raises(ValidationError):
        ClauseExtraction(
            contract_id="c123",
            contract_name="test.pdf",
            clause_number="1.1",
            clause_text="This is a test clause.",
            page=1,
            clause_type="invalid_type",  # not in the Literal
        )

def test_risk_finding_valid():
    finding = RiskFinding(
        clause_number="2.1",
        clause_text="Employee will not compete.",
        page=3,
        clause_type="non_compete",
        risk_level="high",
        conflicting_act="Indian Contract Act 1872",
        conflicting_section="27",
        conflicting_law_quote="Agreements in restraint of trade void.",
        explanation="Void non-compete.",
        recommended_action="Remove clause.",
        confidence=0.95,
    )
    assert finding.risk_level == "high"

def test_risk_finding_invalid_level():
    with pytest.raises(ValidationError):
        RiskFinding(
            clause_number="2.1",
            clause_text="Employee will not compete.",
            page=3,
            clause_type="non_compete",
            risk_level="none",  # 'none' not allowed in RiskFinding, only high/medium/low
            conflicting_act="Indian Contract Act 1872",
            conflicting_section="27",
            conflicting_law_quote="Agreements in restraint of trade void.",
            explanation="Void non-compete.",
            recommended_action="Remove clause.",
            confidence=0.95,
        )

def test_risk_assessment_none_risk():
    assessment = RiskAssessment(
        risk_level="none",
        explanation="No conflict identified with context.",
        confidence=0.8,
        clause_type="payment_term",
    )
    assert assessment.risk_level == "none"
    assert assessment.conflicting_act is None

def test_risk_assessment_high_risk_missing_fields():
    # If risk is high, conflicting_act and other fields are required by validator
    with pytest.raises(ValidationError):
        RiskAssessment(
            risk_level="high",
            explanation="This clause is void under Section 27.",
            confidence=0.9,
            clause_type="non_compete",
            # missing conflicting_act, conflicting_section, conflicting_law_quote, recommended_action
        )

def test_risk_assessment_high_risk_valid():
    assessment = RiskAssessment(
        risk_level="high",
        conflicting_act="Indian Contract Act 1872",
        conflicting_section="27",
        conflicting_law_quote="Agreements in restraint of trade void.",
        explanation="This clause is void under Section 27.",
        recommended_action="Remove clause.",
        confidence=0.9,
        clause_type="non_compete",
    )
    assert assessment.risk_level == "high"
    assert assessment.conflicting_act == "Indian Contract Act 1872"
