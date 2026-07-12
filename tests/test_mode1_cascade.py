import json
import pytest
from unittest.mock import patch, MagicMock

from nyaya_ai.llm.cascade import cascade_risk_assessment
from nyaya_ai.schemas import RiskAssessment

# Valid mock responses matching the RiskAssessment schema
VALID_RISK_JSON = json.dumps({
    "risk_level": "high",
    "conflicting_act": "Indian Contract Act 1872",
    "conflicting_section": "27",
    "conflicting_law_quote": "Agreements in restraint of trade void.",
    "explanation": "Clause is void because of non-compete.",
    "recommended_action": "Remove the non-compete.",
    "confidence": 0.95,
    "clause_type": "non_compete",
    "clause_type_detail": "2 year duration",
})

NO_RISK_JSON = json.dumps({
    "risk_level": "none",
    "conflicting_act": None,
    "conflicting_section": None,
    "conflicting_law_quote": None,
    "explanation": "No conflict found.",
    "recommended_action": None,
    "confidence": 0.88,
    "clause_type": "payment_term",
    "clause_type_detail": "30 days",
})

SAMPLE_CONTEXT = [
    {
        "act_name": "Indian Contract Act 1872",
        "section_number": "27",
        "text": "Every agreement by which any one is restrained...",
        "score": 0.9,
    }
]


@patch("nyaya_ai.llm.cascade._call_groq")
def test_cascade_risk_assessment_tier1_success(mock_groq):
    mock_groq.return_value = VALID_RISK_JSON
    res = cascade_risk_assessment("Employee shall not compete.", SAMPLE_CONTEXT, "non_compete")
    
    assert isinstance(res, RiskAssessment)
    assert res.risk_level == "high"
    assert res.conflicting_act == "Indian Contract Act 1872"
    assert res.conflicting_section == "27"
    mock_groq.assert_called_once()


@patch("nyaya_ai.llm.cascade._call_gemini")
@patch("nyaya_ai.llm.cascade._call_groq")
def test_cascade_risk_assessment_escalation(mock_groq, mock_gemini):
    mock_groq.side_effect = ConnectionError("Groq down")
    mock_gemini.return_value = NO_RISK_JSON

    res = cascade_risk_assessment("Payment due in 30 days.", SAMPLE_CONTEXT, "payment_term")
    assert isinstance(res, RiskAssessment)
    assert res.risk_level == "none"
    mock_groq.assert_called_once()
    mock_gemini.assert_called_once()


@patch("nyaya_ai.llm.cascade._call_openrouter")
@patch("nyaya_ai.llm.cascade._call_gemini")
@patch("nyaya_ai.llm.cascade._call_groq")
def test_cascade_risk_assessment_all_fail(mock_groq, mock_gemini, mock_openrouter):
    mock_groq.side_effect = ConnectionError("Groq down")
    mock_gemini.side_effect = ConnectionError("Gemini down")
    mock_openrouter.side_effect = ConnectionError("OpenRouter down")

    res = cascade_risk_assessment("Arbitration clause.", SAMPLE_CONTEXT, "arbitration")
    assert isinstance(res, RiskAssessment)
    assert res.risk_level == "none"
    assert "Cascade failed to run" in res.explanation
    assert res.confidence == 0.0
    assert res.clause_type == "arbitration"


@patch("nyaya_ai.llm.cascade._call_gemini")
@patch("nyaya_ai.llm.cascade._call_groq")
def test_cascade_circuit_breaker(mock_groq, mock_gemini):
    from nyaya_ai.llm.cascade import _DISABLED_TIERS
    _DISABLED_TIERS.clear()

    # Groq returns a rate limit exception on the first call
    mock_groq.side_effect = Exception("Rate limit reached: TPM 429")
    mock_gemini.return_value = NO_RISK_JSON

    # First call: triggers circuit breaker on Tier 1 (Groq) and escalates to Tier 2 (Gemini)
    res1 = cascade_risk_assessment("Clause 1", SAMPLE_CONTEXT, "non_compete")
    assert mock_groq.call_count == 1
    assert mock_gemini.call_count == 1
    assert "Tier 1" in _DISABLED_TIERS

    # Second call: skips Tier 1 (Groq) entirely and routes directly to Tier 2 (Gemini)
    res2 = cascade_risk_assessment("Clause 2", SAMPLE_CONTEXT, "non_compete")
    assert mock_groq.call_count == 1  # Still 1, did not call Groq again!
    assert mock_gemini.call_count == 2

