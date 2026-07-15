import sys
from pathlib import Path

# Add workspace root to sys.path so scan_contract script is resolvable
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from unittest.mock import MagicMock, patch
import pytest

from nyaya_ai.schemas import ContractScanResult
from scan_contract import main


@pytest.fixture
def mock_scan_result() -> ContractScanResult:
    return ContractScanResult(
        contract_name="test_contract.pdf",
        total_clauses_scanned=2,
        findings=[],
        scan_confidence=0.9,
        status="no_material_risks_found",
        message="All good.",
    )


@patch("scan_contract.scan_contract")
@patch("scan_contract.Path.exists", return_value=True)
def test_cli_json_output(mock_exists, mock_scan, mock_scan_result, capsys):
    mock_scan.return_value = mock_scan_result

    # Mock command line arguments: scan_contract.py test.pdf --json
    with patch.object(sys, "argv", ["scan_contract.py", "test.pdf", "--json"]):
        main()

    captured = capsys.readouterr()
    # Output should be valid JSON matching the scan result
    data = json.loads(captured.out)
    assert data["contract_name"] == "test_contract.pdf"
    assert data["status"] == "no_material_risks_found"


@patch("scan_contract.scan_contract")
@patch("scan_contract.Path.exists", return_value=True)
def test_cli_report_output(mock_exists, mock_scan, mock_scan_result, capsys):
    mock_scan.return_value = mock_scan_result

    # Mock command line arguments: scan_contract.py test.pdf
    with patch.object(sys, "argv", ["scan_contract.py", "test.pdf"]):
        main()

    captured = capsys.readouterr()
    assert "Scan Report" in captured.out
    assert "test_contract.pdf" in captured.out
    assert "NO MATERIAL RISKS FOUND" in captured.out


@patch("scan_contract.Path.exists", return_value=False)
def test_cli_file_not_found(mock_exists):
    # Mock command line arguments: scan_contract.py nonexistent.pdf
    with patch.object(sys, "argv", ["scan_contract.py", "nonexistent.pdf"]):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 1
