import pytest
import csv
import io
import logging
from unittest.mock import MagicMock

from pydantic import ValidationError as PydanticValidationError

from src.data_models.ec_models import Supplier
from src.ingestion.ingest_suppliers import process_suppliers_csv
from src.neo4j_utils.connector import Neo4jConnector
from neo4j.exceptions import Neo4jError, ServiceUnavailable


# --- Unit Tests ---

@pytest.fixture
def mock_neo4j_connector(mocker): # Consistent fixture name
    """Fixture to mock Neo4jConnector for supplier ingestion unit tests."""
    mock_conn = MagicMock(spec=Neo4jConnector)
    mock_conn.execute_query.return_value = [{"id": "mock_neo4j_id"}]
    return mock_conn

def create_suppliers_csv_mock_content(headers, rows_as_dicts):
    """Helper to create in-memory CSV content for suppliers."""
    si = io.StringIO()
    writer = csv.DictWriter(si, fieldnames=headers)
    writer.writeheader()
    for row in rows_as_dicts:
        writer.writerow(row)
    si.seek(0)
    return si

SUPPLIER_CSV_HEADERS = ["SupplierID","SupplierName","ContactPerson","Email","PhoneNumber"]

VALID_SUPPLIER_ROW_1 = {"SupplierID":"201","SupplierName":"ElectroSource Inc.","ContactPerson":"Sarah Connor, Procurement","Email":"sarah.connor@electrosource.com","PhoneNumber":"555-100-2010"}
VALID_SUPPLIER_ROW_2 = {"SupplierID":"202","SupplierName":"FarmFresh Goods Co.","ContactPerson":"Mike Rivera","Email":"mike.r@farmfresh.co","PhoneNumber":"555-200-3020"}


def test_process_valid_suppliers_no_neo4j(mocker, caplog):
    """Test processing valid supplier CSV data without Neo4j interaction."""
    caplog.set_level(logging.INFO)
    csv_rows = [VALID_SUPPLIER_ROW_1, VALID_SUPPLIER_ROW_2]
    mock_csv_file = create_suppliers_csv_mock_content(SUPPLIER_CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)

    summary = process_suppliers_csv("dummy_suppliers.csv", connector=None)

    assert summary["processed_rows"] == 2
    assert summary["validated_suppliers_count"] == 2
    assert summary["loaded_suppliers_count"] == 0 # No connector
    assert summary["validation_errors"] == 0
    assert summary["type_conversion_errors"] == 0
    assert summary["neo4j_errors"] == 0
    assert "Supplier validated: 201" in caplog.text
    assert "Supplier validated: 202" in caplog.text

def test_process_suppliers_pydantic_validation_errors(mocker, caplog):
    """Test CSV with data causing Pydantic validation errors (bad email, non-positive ID)."""
    caplog.set_level(logging.ERROR)
    csv_rows = [
        VALID_SUPPLIER_ROW_1, # Valid
        {"SupplierID":"-203","SupplierName":"Error Supplies","ContactPerson":"Invalid ID","Email":"contact@errors.com","PhoneNumber":"555-BAD-ID"}, # Invalid SupplierID
        {"SupplierID":"204","SupplierName":"Bad Email Inc.","ContactPerson":"No Mail","Email":"bad-email-format","PhoneNumber":"555-NO-MAIL"}, # Invalid Email
    ]
    mock_csv_file = create_suppliers_csv_mock_content(SUPPLIER_CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)

    summary = process_suppliers_csv("dummy_suppliers.csv", connector=None)

    assert summary["processed_rows"] == 3
    assert summary["validated_suppliers_count"] == 1 # Only the first one
    assert summary["validation_errors"] == 2
    assert "Validation error" in caplog.text

def test_process_suppliers_type_conversion_error_supplierid(mocker, caplog):
    """Test CSV data causing type conversion error for SupplierID."""
    caplog.set_level(logging.WARNING) # Capture parsing warnings
    csv_rows = [
        {"SupplierID":"not-an-int","SupplierName":"Type Error Supplies","ContactPerson":"Mr. String","Email":"string@id.com","PhoneNumber":"555-STR-ID"},
    ]
    mock_csv_file = create_suppliers_csv_mock_content(SUPPLIER_CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)

    # The first call to process_suppliers_csv will log the WARNING for parsing
    # and then an ERROR for Pydantic validation if CustomerID becomes None.
    summary = process_suppliers_csv("dummy_suppliers.csv", connector=None)

    assert summary["validation_errors"] == 1 # SupplierID is required, becomes None, Pydantic error
    assert "Validation error" in caplog.text # Check for Pydantic validation error log
    assert "Could not parse integer string: 'not-an-int'" in caplog.text # Check for parsing warning


def test_process_empty_suppliers_csv(mocker, caplog):
    caplog.set_level(logging.INFO)
    mock_csv_file = create_suppliers_csv_mock_content(SUPPLIER_CSV_HEADERS, [])
    mocker.patch('builtins.open', return_value=mock_csv_file)
    summary = process_suppliers_csv("dummy_empty.csv", connector=None)
    assert summary["processed_rows"] == 0
    assert summary["validated_suppliers_count"] == 0

def test_process_suppliers_csv_not_found(mocker, caplog):
    caplog.set_level(logging.ERROR)
    mocker.patch('builtins.open', side_effect=FileNotFoundError("File not found"))
    summary = process_suppliers_csv("non_existent.csv", connector=None)
    assert summary["status"] == "Failed"
    assert "File not found" in summary["message"]

def test_process_valid_suppliers_with_mocked_neo4j_calls(mocker, mock_neo4j_connector, caplog):
    """Test correct Neo4j calls for valid supplier data."""
    caplog.set_level(logging.INFO)
    csv_rows = [VALID_SUPPLIER_ROW_1]
    mock_csv_file = create_suppliers_csv_mock_content(SUPPLIER_CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)

    # Set the expected return value for the supplier ID being processed in this test
    # VALID_SUPPLIER_ROW_1 has SupplierID "201". The script checks for result[0]['id'].
    mock_neo4j_connector.execute_query.return_value = [{"id": 201}]
    summary = process_suppliers_csv("dummy_suppliers.csv", connector=mock_neo4j_connector)

    assert summary["loaded_suppliers_count"] == 1
    assert summary["neo4j_errors"] == 0
    mock_neo4j_connector.execute_query.assert_called_once()
    args, kwargs = mock_neo4j_connector.execute_query.call_args
    assert "MERGE (s:Supplier {supplierID: $supplierID_param})" in args[0]
    assert "SET s = $props" in args[0]
    assert args[1]['supplierID_param'] == 201 # Parameters are in args[1]
    assert args[1]['props']['SupplierName'] == "ElectroSource Inc."
    assert args[1]['props']['supplierID'] == 201 # supplierID also in props
    assert kwargs['tx_type'] == 'write' # tx_type is a keyword arg

def test_process_suppliers_with_neo4j_errors(mocker, mock_neo4j_connector, caplog):
    """Test handling of Neo4j errors during supplier loading."""
    caplog.set_level(logging.ERROR)
    csv_rows = [VALID_SUPPLIER_ROW_1]
    mock_csv_file = create_suppliers_csv_mock_content(SUPPLIER_CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)
    mock_neo4j_connector.execute_query.side_effect = Neo4jError("Simulated DB error")

    summary = process_suppliers_csv("dummy_suppliers.csv", connector=mock_neo4j_connector)

    assert summary["loaded_suppliers_count"] == 0
    assert summary["neo4j_errors"] == 1
    assert "Neo4j error merging Supplier 201" in caplog.text


# --- Integration Tests ---
# Require a running Neo4j instance. Run with: pytest -m integration

@pytest.fixture(scope="module")
def neo4j_supplier_module_connector():
    """
    Pytest fixture for supplier ingestion integration tests.
    Provides a Neo4jConnector instance and handles cleanup of test Supplier nodes.
    """
    # caplog.set_level(logging.INFO) # Removed: caplog is function-scoped
    connector = None
    # Use a specific range or prefix for test SupplierIDs for easier cleanup
    test_supplier_id_prefix_int = 9900
    created_supplier_ids_in_test = []

    try:
        connector = Neo4jConnector()
        connector.execute_query("RETURN 1", tx_type='read') # Verify connection
        logging.info("Neo4jConnector initialized for supplier integration test module.")
        yield connector # Provide connector to tests

    except ServiceUnavailable:
        logging.warning("Neo4j instance not available. Skipping supplier integration tests.")
        pytest.skip("Neo4j instance not available for supplier integration tests.")
    except Exception as e:
        logging.error(f"Failed to initialize Neo4jConnector for supplier integration tests: {e}", exc_info=True)
        pytest.fail(f"Failed to initialize Neo4jConnector: {e}")
    finally:
        if connector:
            try:
                logging.info("Cleaning up Neo4j data after supplier integration test module...")
                # A more robust cleanup would collect all IDs created by tests.
                # For this example, deleting any supplier with ID >= prefix.
                # Ensure this doesn't clash with other data if DB is shared.
                cleanup_query = f"MATCH (s:Supplier) WHERE s.supplierID >= {test_supplier_id_prefix_int} DETACH DELETE s"
                connector.execute_query(cleanup_query, tx_type='write')
                logging.info(f"Supplier integration test cleanup successful (Suppliers with ID >= {test_supplier_id_prefix_int} deleted).")
            except Exception as e:
                logging.error(f"Error during supplier integration test Neo4j cleanup: {e}", exc_info=True)
            finally:
                connector.close()

@pytest.mark.integration
def test_ingest_suppliers_full_pipeline(neo4j_supplier_module_connector, tmp_path, caplog):
    """Integration test for supplier ingestion: CSV -> Pydantic -> Neo4j."""
    caplog.set_level(logging.INFO)
    connector = neo4j_supplier_module_connector

    # Using SupplierIDs in a test-specific range
    test_id_1 = 9901
    test_id_2 = 9902

    csv_rows = [
        {"SupplierID":str(test_id_1),"SupplierName":"Test Supplier Alpha","ContactPerson":"Alpha Contact","Email":"alpha@testsup.com","PhoneNumber":"555-ALPHA"},
        {"SupplierID":str(test_id_2),"SupplierName":"Test Supplier Beta","ContactPerson":"Beta Contact, Sales","Email":"beta.sales@testsup.com","PhoneNumber":"555-BETA"},
    ]
    temp_csv_file = tmp_path / "integration_sample_suppliers.csv"
    with open(temp_csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=SUPPLIER_CSV_HEADERS)
        writer.writeheader()
        for row in csv_rows:
            writer.writerow(row)

    summary = process_suppliers_csv(str(temp_csv_file), connector)

    assert summary["status"] == "Completed"
    assert summary["processed_rows"] == 2
    assert summary["validated_suppliers_count"] == 2
    assert summary["loaded_suppliers_count"] == 2
    assert summary["neo4j_errors"] == 0

    # Verify data in Neo4j
    sup1_data = connector.execute_query(f"MATCH (s:Supplier {{supplierID: {test_id_1}}}) RETURN s.supplierName as name, s.email as email", tx_type='read')
    assert len(sup1_data) == 1
    assert sup1_data[0]["name"] == "Test Supplier Alpha"
    assert sup1_data[0]["email"] == "alpha@testsup.com"

    sup2_data = connector.execute_query(f"MATCH (s:Supplier {{supplierID: {test_id_2}}}) RETURN s.contactPerson as contact, s.phoneNumber as phone", tx_type='read')
    assert len(sup2_data) == 1
    assert sup2_data[0]["contact"] == "Beta Contact, Sales" # Check comma handling
    assert sup2_data[0]["phone"] == "555-BETA"

    # Idempotency Check
    logging.info("Running supplier ingestion again for idempotency check...")
    summary_idem = process_suppliers_csv(str(temp_csv_file), connector)
    assert summary_idem["loaded_suppliers_count"] == 2 # Should MERGE (update) existing

    count_res = connector.execute_query(f"MATCH (s:Supplier) WHERE s.supplierID IN [{test_id_1}, {test_id_2}] RETURN count(s) as total", tx_type='read')
    assert count_res[0]["total"] == 2 # No duplicates

@pytest.mark.integration
def test_ingest_suppliers_mixed_valid_invalid(neo4j_supplier_module_connector, tmp_path, caplog):
    """Test ingestion of mixed valid/invalid supplier rows."""
    caplog.set_level(logging.INFO) # Include INFO for successful loads, ERROR for issues
    connector = neo4j_supplier_module_connector

    test_id_valid = 9903
    test_id_invalid_str = "not-a-supplier-id"

    csv_rows = [
        {"SupplierID":str(test_id_valid),"SupplierName":"Valid Test Supplier","ContactPerson":"Valid Contact","Email":"valid@testsup.com","PhoneNumber":"555-VALID"},
        {"SupplierID":test_id_invalid_str,"SupplierName":"Invalid ID Supplier","ContactPerson":"Error Contact","Email":"error@testsup.com","PhoneNumber":"555-ERROR"}, # Invalid SupplierID format
        {"SupplierID":"9904","SupplierName":"Bad Email Supplier","ContactPerson":"Email Fail","Email":"bademail","PhoneNumber":"555-EMAILFAIL"}, # Invalid Email
    ]
    temp_csv_file = tmp_path / "integration_mixed_suppliers.csv"
    with open(temp_csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=SUPPLIER_CSV_HEADERS)
        writer.writeheader()
        for row in csv_rows:
            writer.writerow(row)

    summary = process_suppliers_csv(str(temp_csv_file), connector)

    assert summary["status"] == "Completed"
    assert summary["processed_rows"] == 3
    assert summary["validated_suppliers_count"] == 1 # Only one is fully valid by Pydantic
    assert summary["loaded_suppliers_count"] == 1
    assert summary["validation_errors"] == 2 # Two rows should fail Pydantic validation
    assert summary["neo4j_errors"] == 0 # No Neo4j errors as invalid data isn't loaded

    # Verify valid one is in Neo4j
    res_valid = connector.execute_query(f"MATCH (s:Supplier {{supplierID: {test_id_valid}}}) RETURN s.supplierName as name", tx_type='read')
    assert len(res_valid) == 1
    assert res_valid[0]["name"] == "Valid Test Supplier"

    # Verify invalid ones are NOT in Neo4j
    # Pydantic rejects "not-a-supplier-id" before it gets to Neo4j
    res_invalid_id_str = connector.execute_query(f"MATCH (s:Supplier {{supplierName: 'Invalid ID Supplier'}}) RETURN s.supplierID", tx_type='read')
    assert len(res_invalid_id_str) == 0

    res_invalid_email = connector.execute_query(f"MATCH (s:Supplier {{supplierID: 9904}}) RETURN s.supplierID", tx_type='read')
    assert len(res_invalid_email) == 0

    assert "Validation error" in caplog.text # Check logs for validation errors
    # Example check for one of the errors (more specific checks can be added)
    assert f"SupplierID: {test_id_invalid_str}" in caplog.text or "bademail" in caplog.text
