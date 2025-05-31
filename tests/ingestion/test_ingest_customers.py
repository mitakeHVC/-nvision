import pytest
import csv
import io
import logging
from unittest.mock import MagicMock
from datetime import datetime

from pydantic import ValidationError as PydanticValidationError

from src.data_models.ec_models import Customer
from src.ingestion.ingest_customers import process_customers_csv # Assuming this is the main function
from src.neo4j_utils.connector import Neo4jConnector
from neo4j.exceptions import Neo4jError, ServiceUnavailable


# --- Unit Tests ---

@pytest.fixture
def mock_neo4j_connector_unit(mocker):
    """Fixture to mock Neo4jConnector for unit tests, passed explicitly to tests needing it."""
    mock_connector = MagicMock(spec=Neo4jConnector)
    # Simulate successful Neo4j query execution by default for most unit tests testing calls
    mock_connector.execute_query.return_value = [{"id": "mock_id"}]
    return mock_connector

def create_customer_csv_mock_content(headers, rows_as_dicts):
    """Helper to create in-memory CSV content for customers."""
    si = io.StringIO()
    writer = csv.DictWriter(si, fieldnames=headers)
    writer.writeheader()
    for row in rows_as_dicts:
        writer.writerow(row)
    si.seek(0)
    return si

CUSTOMER_CSV_HEADERS = ["CustomerID","FirstName","LastName","Email","PhoneNumber","ShippingAddress","BillingAddress","RegistrationDate","LastLoginDate"]

def test_process_valid_customers_no_neo4j(mocker, caplog):
    """Test processing valid customer CSV data without Neo4j interaction."""
    caplog.set_level(logging.INFO)
    csv_rows = [
        {"CustomerID":"1","FirstName":"John","LastName":"Doe","Email":"john.doe@example.com","PhoneNumber":"555-001","ShippingAddress":"1 Main St","BillingAddress":"1 Main St","RegistrationDate":"2023-01-01 10:00:00","LastLoginDate":"2023-01-10 10:00:00"},
        {"CustomerID":"2","FirstName":"Jane","LastName":"Doe","Email":"jane.doe@example.com","PhoneNumber":"555-002","ShippingAddress":"2 Oak St","BillingAddress":"2 Oak St","RegistrationDate":"2023-01-02 11:00:00","LastLoginDate":"2023-01-11 11:00:00"},
    ]
    mock_csv_file = create_customer_csv_mock_content(CUSTOMER_CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)

    summary = process_customers_csv("dummy_customers.csv", connector=None)

    assert summary["processed_rows"] == 2
    assert summary["validated_customers_count"] == 2
    assert summary["loaded_customers_count"] == 0 # No connector
    assert summary["validation_errors"] == 0
    assert summary["type_conversion_errors"] == 0
    assert summary["neo4j_errors"] == 0
    assert "Customer validated: 1" in caplog.text
    assert "Customer validated: 2" in caplog.text

def test_process_customers_pydantic_validation_errors(mocker, caplog):
    """Test CSV with data causing Pydantic validation errors (e.g., bad email, non-positive ID)."""
    caplog.set_level(logging.ERROR)
    csv_rows = [
        {"CustomerID":"1","FirstName":"John","LastName":"Doe","Email":"john.doe@example.com","PhoneNumber":"555-001","ShippingAddress":"1 Main St","BillingAddress":"1 Main St","RegistrationDate":"2023-01-01 10:00:00","LastLoginDate":"2023-01-10 10:00:00"}, # Valid
        {"CustomerID":"-2","FirstName":"Jane","LastName":"Doe","Email":"jane.doe@example.com","PhoneNumber":"555-002","ShippingAddress":"2 Oak St","BillingAddress":"2 Oak St","RegistrationDate":"2023-01-02 11:00:00","LastLoginDate":"2023-01-11 11:00:00"}, # Invalid CustomerID
        {"CustomerID":"3","FirstName":"Peter","LastName":"Pan","Email":"not-an-email","PhoneNumber":"555-003","ShippingAddress":"3 Neverland","BillingAddress":"3 Neverland","RegistrationDate":"2023-01-03 12:00:00","LastLoginDate":"2023-01-12 12:00:00"}, # Invalid Email
    ]
    mock_csv_file = create_customer_csv_mock_content(CUSTOMER_CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)

    summary = process_customers_csv("dummy_customers.csv", connector=None)

    assert summary["processed_rows"] == 3
    assert summary["validated_customers_count"] == 1
    assert summary["validation_errors"] == 2
    assert "Validation error" in caplog.text

def test_process_customers_type_conversion_warnings(mocker, caplog):
    """Test CSV data causing type conversion warnings (malformed date, non-integer ID string for optional fields)."""
    caplog.set_level(logging.WARNING)
    csv_rows = [
        # RegistrationDate is Optional, so None from bad parse is fine by Pydantic
        {"CustomerID":"100","FirstName":"Test","LastName":"User","Email":"test@example.com","PhoneNumber":"555-004","ShippingAddress":"4 Test St","BillingAddress":"4 Test St","RegistrationDate":"bad-date-format","LastLoginDate":"2023-01-13 10:00:00"},
    ]
    mock_csv_file = create_customer_csv_mock_content(CUSTOMER_CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)

    summary = process_customers_csv("dummy_customers.csv", connector=None)

    assert summary["processed_rows"] == 1
    assert summary["validated_customers_count"] == 1 # Still valid as RegistrationDate is Optional
    assert summary["validation_errors"] == 0
    assert "Could not parse datetime string: bad-date-format" in caplog.text

def test_process_customers_required_field_unparsable(mocker, caplog):
    """Test Pydantic error if a required field (CustomerID) is unparsable."""
    caplog.set_level(logging.ERROR)
    csv_rows = [
        {"CustomerID":"not-an-int","FirstName":"Bad","LastName":"ID","Email":"bad.id@example.com","PhoneNumber":"555-005","ShippingAddress":"5 Error Ln","BillingAddress":"5 Error Ln","RegistrationDate":"2023-01-04 10:00:00","LastLoginDate":"2023-01-14 10:00:00"},
    ]
    mock_csv_file = create_customer_csv_mock_content(CUSTOMER_CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)

    summary = process_customers_csv("dummy_customers.csv", connector=None)
    assert summary["validation_errors"] == 1
    assert "Validation error" in caplog.text # Pydantic error because CustomerID became None

def test_process_empty_customers_csv(mocker, caplog):
    caplog.set_level(logging.INFO)
    mock_csv_file = create_customer_csv_mock_content(CUSTOMER_CSV_HEADERS, [])
    mocker.patch('builtins.open', return_value=mock_csv_file)
    summary = process_customers_csv("dummy_empty.csv", connector=None)
    assert summary["processed_rows"] == 0
    assert summary["validated_customers_count"] == 0

def test_process_customers_csv_not_found(mocker, caplog):
    caplog.set_level(logging.ERROR)
    mocker.patch('builtins.open', side_effect=FileNotFoundError("File not found"))
    summary = process_customers_csv("non_existent.csv", connector=None)
    assert summary["status"] == "Failed"
    assert "File not found" in summary["message"]

def test_process_valid_customers_with_mocked_neo4j_calls(mocker, mock_neo4j_connector_unit, caplog):
    """Test correct Neo4j calls for valid customer data."""
    caplog.set_level(logging.INFO)
    csv_rows = [
        {"CustomerID":"1","FirstName":"John","LastName":"Doe","Email":"john.doe@example.com","PhoneNumber":"555-001","ShippingAddress":"1 Main St","BillingAddress":"1 Main St","RegistrationDate":"2023-01-01 10:00:00","LastLoginDate":"2023-01-10 10:00:00"},
    ]
    mock_csv_file = create_customer_csv_mock_content(CUSTOMER_CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)

    summary = process_customers_csv("dummy_customers.csv", connector=mock_neo4j_connector_unit)

    assert summary["loaded_customers_count"] == 1
    assert summary["neo4j_errors"] == 0
    mock_neo4j_connector_unit.execute_query.assert_called_once()
    args, kwargs = mock_neo4j_connector_unit.execute_query.call_args
    assert "MERGE (c:ECCustomer {customerID: $customerID})" in args[0]
    assert kwargs['params']['customerID'] == 1
    assert kwargs['params']['props']['FirstName'] == "John"
    assert kwargs['tx_type'] == 'write'

def test_process_customers_with_neo4j_errors(mocker, mock_neo4j_connector_unit, caplog):
    """Test handling of Neo4j errors during customer loading."""
    caplog.set_level(logging.ERROR)
    csv_rows = [
        {"CustomerID":"1","FirstName":"John","LastName":"Doe","Email":"john.doe@example.com","PhoneNumber":"555-001","ShippingAddress":"1 Main St","BillingAddress":"1 Main St","RegistrationDate":"2023-01-01 10:00:00","LastLoginDate":"2023-01-10 10:00:00"},
    ]
    mock_csv_file = create_customer_csv_mock_content(CUSTOMER_CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)
    mock_neo4j_connector_unit.execute_query.side_effect = Neo4jError("Simulated DB error")

    summary = process_customers_csv("dummy_customers.csv", connector=mock_neo4j_connector_unit)

    assert summary["loaded_customers_count"] == 0
    assert summary["neo4j_errors"] == 1
    assert "Neo4j error merging ECCustomer 1" in caplog.text


# --- Integration Tests ---
# Requires a running Neo4j instance. Run with: pytest -m integration

@pytest.fixture(scope="module")
def neo4j_customer_module_connector():
    """Provides a Neo4jConnector instance for the customer test module, with module-level cleanup."""
    connector = None
    test_customer_ids = [] # Keep track of IDs created in this module for cleanup

    # Store original function to patch it back if necessary, though pytest handles fixtures well
    original_process_customers_csv_func = process_customers_csv

    try:
        connector = Neo4jConnector()
        connector.execute_query("RETURN 1", tx_type='read') # Verify connection
        logging.info("Neo4jConnector initialized for customer integration test module.")

        # Example: A helper function to be used by tests to register IDs for cleanup
        def add_test_customer_id(cid):
            if cid not in test_customer_ids:
                test_customer_ids.append(cid)

        # Make it available to tests if they need to register IDs (e.g. if not using tmp_path)
        # For this setup, we'll get IDs from the CSV data used in tests directly.

        yield connector # Provide connector to tests

    except ServiceUnavailable:
        logging.warning("Neo4j instance not available. Skipping customer integration tests.")
        pytest.skip("Neo4j instance not available for customer integration tests.")
    except Exception as e:
        logging.error(f"Failed to initialize Neo4jConnector for customer integration tests: {e}")
        pytest.fail(f"Failed to initialize Neo4jConnector for customer integration tests: {e}")
    finally:
        if connector:
            try:
                logging.info(f"Cleaning up Neo4j data for customers (IDs: {test_customer_ids})...")
                # More robust: query for specific test labels or properties if possible
                # For now, using IDs based on test data (hardcoded or dynamically collected)
                # This example assumes test IDs are in a known range or specifically tracked.
                # For this test file, we'll use a known range.
                # If test_customer_ids is populated by tests, use that. Otherwise, use fixed range.
                # This cleanup strategy needs to be robust.
                # A common strategy is to use unique prefixes/suffixes for test data.

                # For this example, let's assume test CustomerIDs are >= 9000
                cleanup_query = "MATCH (c:ECCustomer) WHERE c.customerID >= 9000 DETACH DELETE c"
                connector.execute_query(cleanup_query, tx_type='write')
                logging.info("Customer integration test cleanup successful.")
            except Exception as e:
                logging.error(f"Error during customer integration test Neo4j cleanup: {e}")
            finally:
                connector.close()


@pytest.mark.integration
def test_ingest_customers_full_pipeline(neo4j_customer_module_connector, tmp_path, caplog):
    """Integration test for customer ingestion: CSV -> Pydantic -> Neo4j."""
    caplog.set_level(logging.INFO)
    connector = neo4j_customer_module_connector

    test_customer_ids_for_this_test = [9001, 9002] # For verification later
    csv_rows = [
        {"CustomerID":"9001","FirstName":"IntTest","LastName":"UserOne","Email":"int.user1@example.com","PhoneNumber":"555-9001","ShippingAddress":"9001 Test Ave","BillingAddress":"9001 Test Ave","RegistrationDate":"2023-06-01 10:00:00","LastLoginDate":"2023-06-10 10:00:00"},
        {"CustomerID":"9002","FirstName":"IntTest","LastName":"UserTwo","Email":"int.user2@example.com","PhoneNumber":"555-9002","ShippingAddress":"9002 Test Rd","BillingAddress":"9002 Test Rd","RegistrationDate":"2023-06-02 11:00:00","LastLoginDate":"2023-06-11 11:00:00"},
    ]
    temp_csv_file = tmp_path / "integration_sample_customers.csv"
    with open(temp_csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CUSTOMER_CSV_HEADERS)
        writer.writeheader()
        for row in csv_rows:
            writer.writerow(row)

    summary = process_customers_csv(str(temp_csv_file), connector)

    assert summary["status"] == "Completed"
    assert summary["processed_rows"] == 2
    assert summary["validated_customers_count"] == 2
    assert summary["loaded_customers_count"] == 2
    assert summary["neo4j_errors"] == 0

    # Verify data in Neo4j
    for cid_str, original_row in zip([r["CustomerID"] for r in csv_rows], csv_rows):
        cid = int(cid_str)
        res = connector.execute_query(f"MATCH (c:ECCustomer {{customerID: {cid}}}) RETURN c.firstName as firstName, c.email as email", tx_type='read')
        assert len(res) == 1
        assert res[0]["firstName"] == original_row["FirstName"]
        assert res[0]["email"] == original_row["Email"]

    # Test Idempotency
    logging.info("Running customer ingestion again for idempotency check...")
    summary_idem = process_customers_csv(str(temp_csv_file), connector)
    assert summary_idem["loaded_customers_count"] == 2 # Should still "load" (MERGE)

    count_res = connector.execute_query(f"MATCH (c:ECCustomer) WHERE c.customerID IN {[int(r['CustomerID']) for r in csv_rows]} RETURN count(c) as total", tx_type='read')
    assert count_res[0]["total"] == 2 # No duplicates

@pytest.mark.integration
def test_ingest_customers_mixed_valid_invalid(neo4j_customer_module_connector, tmp_path, caplog):
    """Test ingestion of mixed valid/invalid customer rows."""
    caplog.set_level(logging.INFO) # Include INFO for successful loads
    connector = neo4j_customer_module_connector

    test_customer_ids_for_this_test = [9003] # Only one valid
    csv_rows = [
        {"CustomerID":"9003","FirstName":"Valid","LastName":"User","Email":"valid.user@example.com","PhoneNumber":"555-9003","ShippingAddress":"9003 Valid St","BillingAddress":"9003 Valid St","RegistrationDate":"2023-06-03 10:00:00","LastLoginDate":"2023-06-12 10:00:00"},
        {"CustomerID":"-9004","FirstName":"Invalid","LastName":"IDUser","Email":"invalid.id@example.com","PhoneNumber":"555-9004","ShippingAddress":"9004 Invalid Rd","BillingAddress":"9004 Invalid Rd","RegistrationDate":"2023-06-04 11:00:00","LastLoginDate":"2023-06-13 11:00:00"}, # Invalid ID
    ]
    temp_csv_file = tmp_path / "integration_mixed_customers.csv"
    with open(temp_csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CUSTOMER_CSV_HEADERS)
        writer.writeheader()
        for row in csv_rows:
            writer.writerow(row)

    summary = process_customers_csv(str(temp_csv_file), connector)

    assert summary["status"] == "Completed"
    assert summary["processed_rows"] == 2
    assert summary["validated_customers_count"] == 1 # Only one valid
    assert summary["loaded_customers_count"] == 1
    assert summary["validation_errors"] == 1
    assert summary["neo4j_errors"] == 0

    # Verify valid one is in Neo4j
    res_valid = connector.execute_query("MATCH (c:ECCustomer {customerID: 9003}) RETURN c.email as email", tx_type='read')
    assert len(res_valid) == 1
    assert res_valid[0]["email"] == "valid.user@example.com"

    # Verify invalid one is NOT in Neo4j (assuming CustomerID -9004 would be the pydantic-parsed value if it somehow passed)
    # The Pydantic model will reject CustomerID = -9004.
    res_invalid = connector.execute_query("MATCH (c:ECCustomer {customerID: -9004}) RETURN c.email as email", tx_type='read')
    assert len(res_invalid) == 0

    # Check logs for error on the invalid one
    assert "Validation error" in caplog.text
    assert "CustomerID: -9004" in caplog.text # Check that the log contains info about the failing row.
                                            # This depends on how Pydantic formats its error messages for nested models.
                                            # More precise: check for "value is not a positive integer" related to CustomerID.
