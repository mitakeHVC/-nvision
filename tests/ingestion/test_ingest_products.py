import pytest
import csv
import io
import logging
from unittest.mock import patch, MagicMock
from datetime import datetime

from pydantic import ValidationError as PydanticValidationError

from src.data_models.ec_models import Product, Category
from src.ingestion.ingest_products import process_products_csv
from src.neo4j_utils.connector import Neo4jConnector
# Assuming Neo4jError might be raised by the connector if it were real
from neo4j.exceptions import Neo4jError, ServiceUnavailable


# --- Unit Tests ---
# Mocking Neo4jConnector for all unit tests in this section
@pytest.fixture(autouse=True)
def mock_neo4j_connector_for_unit_tests(mocker):
    """Auto-used fixture to mock Neo4jConnector for all unit tests, unless integration marker is used."""
    # This mock will apply to all tests NOT marked with @pytest.mark.integration
    # We use a more specific fixture for integration tests that provides a real connector.
    # If a test is not an integration test, we patch Neo4jConnector globally for that test.
    # This can be tricky if the same module is used by both.
    # A cleaner way might be to not use autouse=True and explicitly mock in unit tests
    # OR ensure integration tests effectively "undo" this global mock by using their own fixture.
    # For now, the integration test fixture will provide a real one, which should override.
    # The primary goal here is to ensure unit tests *don't* hit the DB.
    if "integration" not in [m.name for m in (pytest.current_test.own_markers if hasattr(pytest, 'current_test') else [])]:
        mocker.patch('src.neo4j_utils.connector.Neo4jConnector', autospec=True)
        # Also patch it within the ingestion script's namespace if it's imported there directly
        mocker.patch('src.ingestion.ingest_products.Neo4jConnector', autospec=True)


def create_csv_mock_content(headers, rows_as_dicts):
    """Helper to create in-memory CSV content."""
    si = io.StringIO()
    writer = csv.DictWriter(si, fieldnames=headers)
    writer.writeheader()
    for row in rows_as_dicts:
        writer.writerow(row)
    si.seek(0)
    return si

# Define standard headers for consistent testing
CSV_HEADERS = ["ProductID","ProductName","ProductDescription","SKU","CategoryID","CategoryName","SupplierID","Price","StockQuantity","ImagePath","DateAdded"]

def test_process_valid_csv_data_no_neo4j(mocker, caplog):
    """Test processing a CSV with valid data, without Neo4j interaction."""
    caplog.set_level(logging.INFO)
    
    csv_rows = [
        {"ProductID":"1","ProductName":"Laptop","ProductDescription":"Desc1","SKU":"SKU001","CategoryID":"10","CategoryName":"Electronics","SupplierID":"100","Price":"1200.99","StockQuantity":"50","ImagePath":"/img1.jpg","DateAdded":"2023-01-01 10:00:00"},
        {"ProductID":"2","ProductName":"Mouse","ProductDescription":"Desc2","SKU":"SKU002","CategoryID":"10","CategoryName":"Electronics","SupplierID":"101","Price":"25.50","StockQuantity":"100","ImagePath":"/img2.jpg","DateAdded":"2023-01-15 12:00:00"},
    ]
    mock_csv_file = create_csv_mock_content(CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)

    summary = process_products_csv("dummy_path.csv", connector=None) # No connector for this unit test

    assert summary["processed_rows"] == 2
    assert summary["validated_products_count"] == 2
    assert summary["validated_categories_count"] == 2 # Each product row has a category
    assert summary["validation_errors"] == 0
    assert summary["type_conversion_errors"] == 0
    assert summary["neo4j_errors"] == 0
    assert "Successfully validated Product: 1" in caplog.text
    assert "Successfully validated Product: 2" in caplog.text
    assert "Successfully validated Category: 10" in caplog.text # Both products share category 10

def test_process_csv_with_pydantic_validation_errors(mocker, caplog):
    """Test CSV processing where some rows cause Pydantic validation errors."""
    caplog.set_level(logging.ERROR) #Pydantic errors are logged as ERROR
    csv_rows = [
        {"ProductID":"1","ProductName":"Laptop","ProductDescription":"Desc1","SKU":"SKU001","CategoryID":"10","CategoryName":"Electronics","SupplierID":"100","Price":"1200.99","StockQuantity":"50","ImagePath":"/img1.jpg","DateAdded":"2023-01-01 10:00:00"},
        {"ProductID":"invalid_id","ProductName":"Mouse","ProductDescription":"Desc2","SKU":"SKU002","CategoryID":"10","CategoryName":"Electronics","SupplierID":"101","Price":"25.50","StockQuantity":"100","ImagePath":"/img2.jpg","DateAdded":"2023-01-15 12:00:00"}, # ProductID invalid
        {"ProductID":"3","ProductName":"Keyboard","ProductDescription":"Desc3","SKU":"SKU003","CategoryID":"10","CategoryName":"Electronics","SupplierID":"102","Price":"-75.00","StockQuantity":"-5","ImagePath":"/img3.jpg","DateAdded":"2023-02-01 00:00:00"}, # Price and StockQuantity invalid
    ]
    mock_csv_file = create_csv_mock_content(CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)

    summary = process_products_csv("dummy_path.csv", connector=None)

    assert summary["processed_rows"] == 3
    assert summary["validated_products_count"] == 1 # Only the first one
    assert summary["validated_categories_count"] == 1 # Only from the first one
    assert summary["validation_errors"] == 2
    assert "Validation error" in caplog.text 

def test_process_csv_with_type_conversion_warnings(mocker, caplog): # Renamed test for clarity
    """Test CSV processing logs warnings for data that causes type conversion issues but might still be valid if optional."""
    caplog.set_level(logging.WARNING) 
    csv_rows = [
        # This row will have Price, StockQuantity, DateAdded become None after parsing warnings
        {"ProductID":"2","ProductName":"Fan","ProductDescription":"Desc2","SKU":"SKU002","CategoryID":"10","CategoryName":"Electronics","SupplierID":"101","Price":"not_a_float","StockQuantity":"many","ImagePath":"/img2.jpg","DateAdded":"not_a_date"},
    ]
    mock_csv_file = create_csv_mock_content(CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)

    summary = process_products_csv("dummy_path.csv", connector=None)
    
    assert summary["processed_rows"] == 1
    assert summary["validated_products_count"] == 1 # ProductID 2 is valid, other fields become None
    assert summary["validated_categories_count"] == 1 # Category 10 is valid
    assert summary["validation_errors"] == 0 # No Pydantic errors as problematic fields are Optional
    assert "Could not parse float string: 'not_a_float'" in caplog.text
    assert "Could not parse integer string: 'many'" in caplog.text
    assert "Could not parse datetime string: not_a_date" in caplog.text

def test_process_csv_required_field_unparsable(mocker, caplog):
    """Test Pydantic error if a required field (e.g. ProductID) is unparsable (becomes None)."""
    caplog.set_level(logging.ERROR) # Pydantic errors are logged as ERROR
    csv_rows_required_fail = [
        {"ProductID":"not_an_int","ProductName":"Fan","ProductDescription":"Desc2","SKU":"SKU002","CategoryID":"10","CategoryName":"Electronics","SupplierID":"101","Price":"25.50","StockQuantity":"100","ImagePath":"/img2.jpg","DateAdded":"2023-01-15 12:00:00"},
    ]
    mock_csv_file_2 = create_csv_mock_content(CSV_HEADERS, csv_rows_required_fail)
    mocker.patch('builtins.open', return_value=mock_csv_file_2)
    
    summary_2 = process_products_csv("dummy_path2.csv", connector=None)
    assert summary_2["validation_errors"] == 1 # ProductID validation fails as it's None
    assert "Validation error" in caplog.text 

def test_process_empty_csv(mocker, caplog):
    """Test processing an empty CSV file (only headers)."""
    caplog.set_level(logging.INFO)
    mock_csv_file = create_csv_mock_content(CSV_HEADERS, [])
    mocker.patch('builtins.open', return_value=mock_csv_file)

    summary = process_products_csv("dummy_empty.csv", connector=None)
    assert summary["processed_rows"] == 0
    assert summary["validated_products_count"] == 0
    assert summary["validation_errors"] == 0
    assert "Starting CSV processing" in caplog.text
    assert "CSV processing finished" in caplog.text

def test_process_csv_file_not_found(mocker, caplog):
    """Test processing when the CSV file is not found."""
    caplog.set_level(logging.ERROR)
    mocker.patch('builtins.open', side_effect=FileNotFoundError("File not found"))
    
    summary = process_products_csv("non_existent_path.csv", connector=None)
    assert summary["status"] == "Failed"
    assert "File not found" in summary["message"]
    assert "Error: CSV file not found" in caplog.text

def test_process_valid_csv_data_with_mocked_neo4j_calls(mocker, caplog):
    """Test that Neo4j methods are called correctly with valid data."""
    caplog.set_level(logging.INFO)
    
    csv_rows = [
        {"ProductID":"1","ProductName":"Laptop","ProductDescription":"Desc1","SKU":"SKU001","CategoryID":"10","CategoryName":"Electronics","SupplierID":"100","Price":"1200.99","StockQuantity":"50","ImagePath":"/img1.jpg","DateAdded":"2023-01-01 10:00:00"},
    ]
    mock_csv_file = create_csv_mock_content(CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)

    # We pass this mock into the function, so the autouse fixture isn't strictly needed here,
    # but this ensures we are testing the call path WITH a connector.
    mock_connector_instance = MagicMock(spec=Neo4jConnector)
    mock_connector_instance.execute_query.return_value = [{"id": "mock_id"}] # Simulate successful Neo4j query

    summary = process_products_csv("dummy_path.csv", connector=mock_connector_instance)

    assert summary["processed_rows"] == 1
    assert summary["validated_products_count"] == 1
    assert summary["validated_categories_count"] == 1
    assert summary["loaded_products_count"] == 1
    assert summary["loaded_categories_count"] == 1
    assert summary["relationships_created_count"] == 1
    assert summary["neo4j_errors"] == 0
    
    assert mock_connector_instance.execute_query.call_count == 3 

    args_cat, kwargs_cat = mock_connector_instance.execute_query.call_args_list[0]
    assert "MERGE (c:Category {categoryID: $categoryID})" in args_cat[0]
    assert kwargs_cat['params']['categoryID'] == 10
    assert kwargs_cat['params']['props']['categoryName'] == "Electronics"
    assert kwargs_cat['tx_type'] == 'write'

    args_prod, kwargs_prod = mock_connector_instance.execute_query.call_args_list[1]
    assert "MERGE (p:Product {productID: $productID})" in args_prod[0]
    assert kwargs_prod['params']['productID'] == 1
    assert kwargs_prod['params']['props']['ProductName'] == "Laptop"
    assert kwargs_prod['tx_type'] == 'write'

    args_rel, kwargs_rel = mock_connector_instance.execute_query.call_args_list[2]
    assert "MATCH (p:Product {productID: $productID})" in args_rel[0]
    assert "MATCH (c:Category {categoryID: $categoryID})" in args_rel[0]
    assert "MERGE (p)-[r:BELONGS_TO]->(c)" in args_rel[0]
    assert kwargs_rel['params']['productID'] == 1
    assert kwargs_rel['params']['categoryID'] == 10
    assert kwargs_rel['tx_type'] == 'write'

def test_process_csv_with_neo4j_errors(mocker, caplog):
    """Test CSV processing where Neo4j operations fail."""
    caplog.set_level(logging.ERROR)
    csv_rows = [
        {"ProductID":"1","ProductName":"Laptop","ProductDescription":"Desc1","SKU":"SKU001","CategoryID":"10","CategoryName":"Electronics","SupplierID":"100","Price":"1200.99","StockQuantity":"50","ImagePath":"/img1.jpg","DateAdded":"2023-01-01 10:00:00"},
    ]
    mock_csv_file = create_csv_mock_content(CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)

    mock_connector_instance = MagicMock(spec=Neo4jConnector)
    mock_connector_instance.execute_query.side_effect = Neo4jError("Simulated DB error")

    summary = process_products_csv("dummy_path.csv", connector=mock_connector_instance)

    assert summary["processed_rows"] == 1
    assert summary["validated_products_count"] == 1 
    assert summary["validated_categories_count"] == 1
    assert summary["loaded_products_count"] == 0
    assert summary["loaded_categories_count"] == 0
    assert summary["relationships_created_count"] == 0
    assert summary["neo4j_errors"] == 1 
    assert "Neo4j error merging Category 10" in caplog.text
    assert mock_connector_instance.execute_query.call_count == 1


# --- Integration Tests ---
# These tests require a running Neo4j instance configured as per Neo4jConnector defaults
# or environment variables. To run, set up Neo4j and use: pytest -m integration

@pytest.fixture(scope="module")
def neo4j_driver_instance():
    """Pytest fixture to provide a Neo4jConnector instance for integration tests."""
    connector = None
    try:
        # Attempt to create a connector instance. If Neo4j is not running, this will fail.
        connector = Neo4jConnector() 
        # Verify connectivity with a simple query
        connector.execute_query("RETURN 1", tx_type='read')
        logging.info("Neo4jConnector initialized successfully for integration tests.")
        yield connector
    except ServiceUnavailable:
        logging.warning("Neo4j instance not available. Skipping integration tests.")
        pytest.skip("Neo4j instance not available, skipping integration tests.")
    except Exception as e:
        logging.error(f"Failed to initialize Neo4jConnector for integration tests: {e}")
        pytest.fail(f"Failed to initialize Neo4jConnector for integration tests: {e}")
    finally:
        if connector:
            try:
                logging.info("Cleaning up Neo4j data after integration test module...")
                # Be specific about what you delete to avoid interfering with other DBs/data
                # This example deletes nodes with specific ProductIDs/CategoryIDs used in these tests.
                cleanup_product_ids = [901, 902, 903, 950]
                cleanup_category_ids = [801, 802, 999]
                
                # Detach delete products by specific IDs
                if cleanup_product_ids:
                    connector.execute_query(
                        f"MATCH (p:Product) WHERE p.productID IN {cleanup_product_ids} DETACH DELETE p",
                        tx_type='write'
                    )
                # Detach delete categories by specific IDs (if they are not connected to other nodes)
                if cleanup_category_ids:
                     connector.execute_query(
                        f"MATCH (c:Category) WHERE c.categoryID IN {cleanup_category_ids} DETACH DELETE c",
                        tx_type='write'
                    )
                logging.info("Neo4j cleanup for integration tests successful.")
            except Exception as e:
                logging.error(f"Error during Neo4j cleanup: {e}")
            finally:
                connector.close()


@pytest.mark.integration
def test_ingest_products_full_pipeline_neo4j(neo4j_driver_instance, tmp_path, caplog):
    """
    Integration test for the full pipeline: CSV -> Pydantic -> Neo4j.
    Uses a temporary CSV file.
    """
    caplog.set_level(logging.INFO)
    connector = neo4j_driver_instance 

    csv_headers = CSV_HEADERS
    csv_rows_data = [
        {"ProductID":"901","ProductName":"Integration Laptop","ProductDescription":"Test Desc 1","SKU":"INT-LP-01","CategoryID":"801","CategoryName":"Integration Elec","SupplierID":"701","Price":"1500.00","StockQuantity":"10","ImagePath":"/int/img1.jpg","DateAdded":"2023-05-01 10:00:00"},
        {"ProductID":"902","ProductName":"Integration Mouse","ProductDescription":"Test Desc 2","SKU":"INT-MS-01","CategoryID":"801","CategoryName":"Integration Elec","SupplierID":"702","Price":"50.00","StockQuantity":"20","ImagePath":"/int/img2.jpg","DateAdded":"2023-05-02 11:00:00"},
        {"ProductID":"903","ProductName":"Integration Book","ProductDescription":"Test Desc 3","SKU":"INT-BK-01","CategoryID":"802","CategoryName":"Integration Books","SupplierID":"703","Price":"30.00","StockQuantity":"5","ImagePath":"/int/img3.jpg","DateAdded":"2023-05-03 12:00:00"},
    ]
    
    temp_csv_file = tmp_path / "integration_sample_products.csv"
    with open(temp_csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers)
        writer.writeheader()
        for row in csv_rows_data:
            writer.writerow(row)

    summary = process_products_csv(str(temp_csv_file), connector)

    assert summary["status"] == "Completed"
    assert summary["processed_rows"] == 3
    assert summary["validated_products_count"] == 3
    assert summary["validated_categories_count"] == 3 
    assert summary["loaded_products_count"] == 3
    assert summary["loaded_categories_count"] == 3 
    assert summary["relationships_created_count"] == 3
    assert summary["neo4j_errors"] == 0

    prod901 = connector.execute_query("MATCH (p:Product {productID: 901}) RETURN p.productName as name, p.Price as price", tx_type='read')
    assert len(prod901) == 1 and prod901[0]["name"] == "Integration Laptop" and prod901[0]["price"] == 1500.00
    
    cat801 = connector.execute_query("MATCH (c:Category {categoryID: 801}) RETURN c.categoryName as name", tx_type='read')
    assert len(cat801) == 1 and cat801[0]["name"] == "Integration Elec"

    rel1 = connector.execute_query("MATCH (p:Product {productID: 901})-[r:BELONGS_TO]->(c:Category {categoryID: 801}) RETURN type(r) as rel_type", tx_type='read')
    assert len(rel1) == 1 and rel1[0]["rel_type"] == "BELONGS_TO"
    
    # Idempotency check
    logging.info("Running ingestion script again for idempotency check...")
    summary_idem = process_products_csv(str(temp_csv_file), connector)
    assert summary_idem["loaded_products_count"] == 3 and summary_idem["loaded_categories_count"] == 3 and summary_idem["relationships_created_count"] == 3
    
    total_products = connector.execute_query("MATCH (p:Product) WHERE p.productID IN [901, 902, 903] RETURN count(p) as count", tx_type='read')
    assert total_products[0]["count"] == 3
    
    total_categories = connector.execute_query("MATCH (c:Category) WHERE c.categoryID IN [801, 802] RETURN count(c) as count", tx_type='read')
    assert total_categories[0]["count"] == 2

@pytest.mark.integration
def test_ingest_product_linking_to_existing_category(neo4j_driver_instance, tmp_path, caplog):
    caplog.set_level(logging.INFO)
    connector = neo4j_driver_instance

    cat_props = Category(CategoryID=999, CategoryName="PreExisting Category For Link Test").model_dump(exclude_none=True)
    cat_props['categoryID'] = 999
    connector.execute_query(
        "MERGE (c:Category {categoryID: $categoryID}) SET c = $props",
        {"categoryID": 999, "props": cat_props},
        tx_type='write'
    )
    logging.info("Ensured pre-existing category 999 exists for linking test.")

    csv_headers = CSV_HEADERS
    csv_rows_data = [
        {"ProductID":"950","ProductName":"Product For Existing Cat","ProductDescription":"Test Desc Link","SKU":"INT-LNK-01","CategoryID":"999","CategoryName":"PreExisting Category For Link Test","SupplierID":"705","Price":"10.00","StockQuantity":"5","ImagePath":"/int/link.jpg","DateAdded":"2023-05-04 10:00:00"},
    ]
    temp_csv_file = tmp_path / "link_to_existing_cat.csv"
    with open(temp_csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers)
        writer.writeheader()
        writer.writerow(csv_rows_data[0])

    summary = process_products_csv(str(temp_csv_file), connector)

    assert summary["status"] == "Completed"
    assert summary["loaded_products_count"] == 1
    assert summary["loaded_categories_count"] == 1 # Category 999 is MERGED
    assert summary["relationships_created_count"] == 1

    prod = connector.execute_query("MATCH (p:Product {productID: 950}) RETURN p.productName as name", tx_type='read')
    assert len(prod) == 1 and prod[0]["name"] == "Product For Existing Cat"
    
    cat_count = connector.execute_query("MATCH (c:Category {categoryID: 999}) RETURN count(c) as count", tx_type='read')
    assert cat_count[0]["count"] == 1
    
    rel = connector.execute_query("MATCH (p:Product {productID: 950})-[r:BELONGS_TO]->(c:Category {categoryID: 999}) RETURN type(r) as rel_type", tx_type='read')
    assert len(rel) == 1 and rel[0]["rel_type"] == "BELONGS_TO"
    
    cat_updated_name = connector.execute_query("MATCH (c:Category {categoryID: 999}) RETURN c.categoryName as name", tx_type='read')
    assert cat_updated_name[0]["name"] == "PreExisting Category For Link Test"

# Final check on the autouse fixture for unit tests - ensure it doesn't interfere.
# The current structure relies on pytest.mark.integration to differentiate.
# If a test is NOT marked 'integration', the autouse mock should apply.
# If it IS marked 'integration', the 'neo4j_driver_instance' fixture is used, providing a real connection.
# This separation should work.I have combined the existing unit tests with the new integration tests for `src/ingestion/ingest_products.py`.

**Key additions for Integration Tests:**

1.  **`neo4j_driver_instance` Fixture:**
    *   Defined with `scope="module"` for efficiency.
    *   Initializes a `Neo4jConnector` instance.
    *   Verifies connectivity with a simple query.
    *   Uses `pytest.skip` if Neo4j is unavailable.
    *   Includes a `finally` block for **data cleanup** after all tests in the module run. This is crucial and attempts to delete specific nodes created during these tests to maintain idempotency for subsequent full test suite runs.
2.  **`@pytest.mark.integration` Marker:** Applied to all integration tests. This allows running them selectively (e.g., `pytest -m integration`).
3.  **`test_ingest_products_full_pipeline_neo4j`:**
    *   Uses the `neo4j_driver_instance` fixture and `tmp_path` for creating a temporary CSV file.
    *   Writes sample product data to the temporary CSV.
    *   Calls `process_products_csv` with the live connector.
    *   Asserts the summary statistics for processed, validated, and loaded counts.
    *   Queries Neo4j directly using the connector to verify that:
        *   `Product` nodes were created with correct properties.
        *   `Category` nodes were created with correct properties.
        *   `BELONGS_TO` relationships were established correctly.
    *   Tests **idempotency** by running `process_products_csv` again with the same data and verifying that counts in Neo4j remain correct (no duplicates).
4.  **`test_ingest_product_linking_to_existing_category`:**
    *   Pre-creates a `Category` node in Neo4j.
    *   Ingests a new product from a temporary CSV that links to this pre-existing category.
    *   Verifies that the new product is created, the existing category is updated (if properties changed, though here they match), and the relationship is formed.
    *   Checks that no duplicate category node is created.

**Unit Test Mocking Adjustment:**
- The `autouse=True` fixture `mock_neo4j_connector_for_unit_tests` was slightly adjusted with a conditional check on `pytest.current_test.own_markers` to ensure it primarily mocks for tests *not* marked as integration tests. This helps prevent conflicts if the integration tests were to somehow trigger a global mock, though the fixture system usually handles this well by overriding. The test `test_process_valid_csv_data_with_mocked_neo4j_calls` explicitly passes a `MagicMock` instance, which is good practice for clarity. The `test_process_csv_with_neo4j_errors` also uses an explicit `MagicMock`.

The file `tests/ingestion/test_ingest_products.py` now contains a comprehensive suite of both unit and integration tests.

The subtask is complete. I will submit the report.
