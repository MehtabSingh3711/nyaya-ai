from nyaya_ai.contracts.classifier import classify_clause


def test_classify_non_compete():
    text = "Employee agrees that they shall not engage in any non-compete activity for a duration of 2 years."
    clause_type, detail = classify_clause(text)
    assert clause_type == "non_compete"
    assert "2 years" in detail


def test_classify_payment_term():
    text = "Payment must be completed within 90 days after receiving the invoice."
    clause_type, detail = classify_clause(text)
    assert clause_type == "payment_term"
    assert "90 days" in detail


def test_classify_termination():
    text = "Either party may terminate this agreement upon 30 days notice to the other party."
    clause_type, detail = classify_clause(text)
    assert clause_type == "termination"
    assert "30 days notice" in detail


def test_classify_other():
    text = "This contract is executed in two originals by the authorized representatives."
    clause_type, detail = classify_clause(text)
    assert clause_type == "other"
    assert detail is None
