from nyaya_ai.contracts.extractor import ExtractedContract, ExtractedPage
from nyaya_ai.contracts.chunker import chunk_contract


def test_chunk_contract_structural_pdf():
    page1 = ExtractedPage(page_number=1, text="1. Scope of work details.\nSome description of scope.\n")
    page2 = ExtractedPage(page_number=2, text="2. Payment terms:\nThe fee shall be paid in 30 days.\nClause 3. Termination details.")
    extraction = ExtractedContract(
        contract_name="test.pdf",
        pages=[page1, page2],
        status="success",
    )

    clauses = chunk_contract(extraction)
    # Expected: clause 1 (starts page 1), clause 2 (starts page 2), clause 3 (starts page 2)
    assert len(clauses) == 3
    
    assert clauses[0].clause_number == "1"
    assert clauses[0].page == 1
    assert "Scope of work" in clauses[0].clause_text

    assert clauses[1].clause_number == "2"
    assert clauses[1].page == 2
    assert "Payment terms" in clauses[1].clause_text

    assert clauses[2].clause_number == "3"
    assert clauses[2].page == 2
    assert "Termination details" in clauses[2].clause_text


def test_chunk_contract_fallback_docx():
    extraction = ExtractedContract(
        contract_name="test.docx",
        paragraphs=[
            "Paragraph one describing scope.",
            "Paragraph two describing payment.",
        ],
        status="success",
    )

    clauses = chunk_contract(extraction)
    # No structural clause numbering detected → fallback to paragraphs
    assert len(clauses) == 2
    assert clauses[0].clause_number == "1"
    assert clauses[0].page == 0
    assert clauses[1].clause_number == "2"
    assert clauses[1].page == 0


def test_chunk_contract_heuristics():
    page1 = ExtractedPage(
        page_number=1,
        text="§ 1 Definitions\nStatus: Safe\nThis is definition text.\n\n"
             "§ 2.3 Non-Compete Restriction\nStatus: Void\nDo not compete.\n\n"
             "CONFIDENTIALITY\nThis is mutual confidentiality."
    )
    extraction = ExtractedContract(
        contract_name="nda_heuristic.pdf",
        pages=[page1],
        status="success",
    )

    clauses = chunk_contract(extraction)
    
    # Expected: 3 clauses
    # 1. § 1 Definitions (numbered with § symbol)
    # 2. § 2.3 Non-Compete (numbered sub-clause with § symbol)
    # 3. CONFIDENTIALITY (unnumbered uppercase header)
    assert len(clauses) == 3
    
    assert clauses[0].clause_number == "1"
    assert "Definitions" in clauses[0].clause_text
    
    assert clauses[1].clause_number == "2.3"
    assert "Non-Compete" in clauses[1].clause_text
    
    assert clauses[2].clause_number == "Confidentiality"
    assert "This is mutual confidentiality" in clauses[2].clause_text
