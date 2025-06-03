import pytest
import csv
import io
import logging
from unittest.mock import MagicMock, call # Import call for checking multiple calls
from datetime import datetime

from pydantic import ValidationError as PydanticValidationError

# Assuming ec_models.Order is the one to use.
# The script also uses an internal CSVOrderItemData model.
from src.data_models.ec_models import Order
from src.ingestion.ingest_orders import process_orders_csv, CSVOrderItemData
from src.neo4j_utils.connector import Neo4jConnector
from neo4j.exceptions import Neo4jError, ServiceUnavailable


# --- Unit Tests ---

@pytest.fixture
def mock_neo4j_connector(mocker): # Renamed to avoid conflict if run with other test files' fixtures
    """Fixture to mock Neo4jConnector for order ingestion unit tests."""
    mock_conn = MagicMock(spec=Neo4jConnector)
    # Default behavior: successful query execution returning a mock ID or relevant data
    mock_conn.execute_query.return_value = [{"id": "mock_neo4j_id"}]
    return mock_conn

def create_orders_csv_mock_content(headers, rows_as_dicts):
    """Helper to create in-memory CSV content for orders."""
    si = io.StringIO()
    writer = csv.DictWriter(si, fieldnames=headers)
    writer.writeheader()
    for row in rows_as_dicts:
        writer.writerow(row)
    si.seek(0)
    return si

ORDERS_CSV_HEADERS = [
    "OrderID","CustomerID","OrderDate","OrderStatus","OrderTotalAmount",
    "ShippingAddress","BillingAddress",
    "OrderItemID","ProductID","Quantity","UnitPrice"
]

# Common valid row parts
ORDER_1_PART = {"OrderID":"1001","CustomerID":"1","OrderDate":"2023-01-01 10:00:00","OrderStatus":"Delivered","OrderTotalAmount":"150.00","ShippingAddress":"1 Main St","BillingAddress":"1 Main St"}
ITEM_1A = {"OrderItemID":"2001","ProductID":"101","Quantity":"1","UnitPrice":"100.00"}
ITEM_1B = {"OrderItemID":"2002","ProductID":"102","Quantity":"2","UnitPrice":"25.00"}

ORDER_2_PART = {"OrderID":"1002","CustomerID":"2","OrderDate":"2023-01-02 11:00:00","OrderStatus":"Shipped","OrderTotalAmount":"50.00","ShippingAddress":"2 Oak St","BillingAddress":"2 Oak St"}
ITEM_2A = {"OrderItemID":"2003","ProductID":"103","Quantity":"1","UnitPrice":"50.00"}


def test_process_valid_orders_no_neo4j(mocker, caplog):
    """Test valid CSV processing (single & multi-item orders) without Neo4j."""
    caplog.set_level(logging.INFO)
    csv_rows = [
        {**ORDER_1_PART, **ITEM_1A}, # Order 1001, Item 2001
        {**ORDER_1_PART, **ITEM_1B}, # Order 1001, Item 2002
        {**ORDER_2_PART, **ITEM_2A}, # Order 1002, Item 2003
    ]
    mock_csv_file = create_orders_csv_mock_content(ORDERS_CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)

    summary = process_orders_csv("dummy_orders.csv", connector=None)

    assert summary["processed_rows"] == 3
    assert summary["validated_orders_count"] == 3 # Script validates order part of each row
    assert summary["validated_items_count"] == 3
    assert summary["loaded_orders_count"] == 0
    assert summary["loaded_items_relationships_count"] == 0
    assert summary["placed_relationships_count"] == 0
    assert summary["validation_errors"] == 0
    assert "Order Pydantic-validated: 1001" in caplog.text
    assert "Order Pydantic-validated: 1002" in caplog.text
    assert "OrderItem Pydantic-validated: 2001" in caplog.text
    assert "OrderItem Pydantic-validated: 2002" in caplog.text
    assert "OrderItem Pydantic-validated: 2003" in caplog.text
    # Check that order 1001 was validated for each of its item rows
    assert caplog.text.count("Order Pydantic-validated: 1001") == 2


def test_process_orders_invalid_order_data(mocker, caplog):
    """Test CSV with rows causing Order Pydantic validation errors."""
    caplog.set_level(logging.ERROR)
    csv_rows = [
        {**ORDER_1_PART, **ITEM_1A}, # Valid
        {"OrderID":"bad_id","CustomerID":"1"}, # Invalid OrderID (mocking rest of fields for brevity)
        {"OrderID":"1003","CustomerID":"-3"}, # Invalid CustomerID
    ]
    # Fill in missing fields for robust test
    csv_rows[1].update({"OrderDate":"2023-01-03 10:00:00","OrderStatus":"Pending","OrderTotalAmount":"10.0","ShippingAddress":"N/A","BillingAddress":"N/A","OrderItemID":"2004","ProductID":"104","Quantity":"1","UnitPrice":"10.0"})
    csv_rows[2].update({"OrderDate":"2023-01-04 10:00:00","OrderStatus":"Pending","OrderTotalAmount":"20.0","ShippingAddress":"N/A","BillingAddress":"N/A","OrderItemID":"2005","ProductID":"105","Quantity":"1","UnitPrice":"20.0"})

    mock_csv_file = create_orders_csv_mock_content(ORDERS_CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)

    summary = process_orders_csv("dummy_orders.csv", connector=None)

    assert summary["processed_rows"] == 3
    assert summary["validated_orders_count"] == 1 # Only first order
    assert summary["validated_items_count"] == 1 # Only first item
    assert summary["validation_errors"] >= 2 # At least 2 rows have validation errors
    assert "Validation error" in caplog.text

def test_process_orders_invalid_item_data(mocker, caplog):
    """Test CSV with valid Order data but invalid OrderItem data."""
    caplog.set_level(logging.ERROR)
    csv_rows = [
        {**ORDER_1_PART, **ITEM_1A}, # Valid
        {**ORDER_1_PART, "OrderItemID":"bad_item_id", "ProductID":"102", "Quantity":"1", "UnitPrice":"20.0"}, # Invalid OrderItemID
        {**ORDER_2_PART, "OrderItemID":"2004", "ProductID":"103", "Quantity":"-1", "UnitPrice":"30.0"}, # Invalid Quantity
    ]
    mock_csv_file = create_orders_csv_mock_content(ORDERS_CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)

    summary = process_orders_csv("dummy_orders.csv", connector=None)

    assert summary["processed_rows"] == 3
    # Order 1001 (from ITEM_1A) is valid. Order parts of row 2 and 3 are Pydantic-valid if types are okay.
    # The items for row 2 and 3 fail, but their Order parts might pass initial Pydantic validation.
    # The script validates Order and OrderItem separately.
    # Order 1 (from ITEM_1A) is valid.
    # Order 1 (from bad_item_id row) is valid.
    # Order 2 (from invalid quantity row) is valid.
    assert summary["validated_orders_count"] == 3 # Script validates order part of each row
    assert summary["validated_items_count"] == 1 # Only ITEM_1A
    assert summary["validation_errors"] >= 2 # 2 items have validation errors
    assert "Validation error" in caplog.text # For Pydantic CSVOrderItemData model

def test_process_orders_mocked_neo4j_calls_multi_item_order(mocker, mock_neo4j_connector, caplog):
    """Test correct Neo4j calls for a single order with multiple items."""
    caplog.set_level(logging.INFO)
    csv_rows = [
        {**ORDER_1_PART, **ITEM_1A},
        {**ORDER_1_PART, **ITEM_1B},
    ]
    mock_csv_file = create_orders_csv_mock_content(ORDERS_CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)

    # Define side effects for the mock connector to simulate Neo4j responses
    mock_neo4j_connector.execute_query.side_effect = [
        [{"o.orderID": 1001}],  # Mock response for merging Order 1001
        [{"rel_type": "PLACED"}],  # Mock response for PLACED relationship
        [{"rel_type": "CONTAINS"}],# Mock response for CONTAINS for ITEM_1A
        [{"rel_type": "CONTAINS"}] # Mock response for CONTAINS for ITEM_1B
    ]
    summary = process_orders_csv("dummy_orders.csv", connector=mock_neo4j_connector)

    assert summary["loaded_orders_count"] == 1
    assert summary["placed_relationships_count"] == 1
    assert summary["loaded_items_relationships_count"] == 2
    assert summary["neo4j_errors"] == 0

    # Expected calls: 1 for Order node, 1 for PLACED rel, 2 for CONTAINS rels
    assert mock_neo4j_connector.execute_query.call_count == 1 + 1 + 2

    # Call 1: Merge Order Node
    call_order_node = mock_neo4j_connector.execute_query.call_args_list[0]
    assert "MERGE (o:Order {orderID: $orderID})" in call_order_node.args[0]
    assert call_order_node.args[1]['orderID'] == 1001
    assert call_order_node.args[1]['props']['TotalAmount'] == 150.00 # Key in Pydantic model is TotalAmount

    # Call 2: Merge PLACED Relationship
    call_placed_rel = mock_neo4j_connector.execute_query.call_args_list[1]
    assert "MATCH (c:ECCustomer {customerID: $customerID})" in call_placed_rel.args[0]
    assert "MERGE (c)-[r:PLACED]->(o)" in call_placed_rel.args[0]
    assert call_placed_rel.args[1]['orderID'] == 1001
    assert call_placed_rel.args[1]['customerID'] == 1

    # Call 3: Merge CONTAINS for ITEM_1A
    call_contains_1a = mock_neo4j_connector.execute_query.call_args_list[2]
    assert "MERGE (o)-[r:CONTAINS {orderItemID: $orderItemID}]->(p)" in call_contains_1a.args[0]
    assert call_contains_1a.args[1]['orderItemID'] == 2001
    assert call_contains_1a.args[1]['quantity'] == 1
    assert call_contains_1a.args[1]['unitPrice'] == 100.00
    assert call_contains_1a.args[1]['totalItemPrice'] == 1 * 100.00

    # Call 4: Merge CONTAINS for ITEM_1B
    call_contains_1b = mock_neo4j_connector.execute_query.call_args_list[3]
    assert "MERGE (o)-[r:CONTAINS {orderItemID: $orderItemID}]->(p)" in call_contains_1b.args[0]
    assert call_contains_1b.args[1]['orderItemID'] == 2002
    assert call_contains_1b.args[1]['quantity'] == 2
    assert call_contains_1b.args[1]['unitPrice'] == 25.00
    assert call_contains_1b.args[1]['totalItemPrice'] == 2 * 25.00


def test_process_orders_neo4j_error_on_order_merge(mocker, mock_neo4j_connector, caplog):
    """Test Neo4j error during Order node MERGE."""
    caplog.set_level(logging.ERROR)
    csv_rows = [{**ORDER_1_PART, **ITEM_1A}]
    mock_csv_file = create_orders_csv_mock_content(ORDERS_CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)

    # Simulate Neo4j error only for the first call (Order MERGE)
    mock_neo4j_connector.execute_query.side_effect = [Neo4jError("Simulated DB error on Order"), MagicMock()]

    summary = process_orders_csv("dummy_orders.csv", connector=mock_neo4j_connector)

    assert summary["loaded_orders_count"] == 0
    assert summary["placed_relationships_count"] == 0
    assert summary["loaded_items_relationships_count"] == 0 # Item processing should be skipped
    assert summary["neo4j_errors"] == 1
    assert "Neo4j error processing Order 1001" in caplog.text
    # Should only be one call to execute_query (the one that failed)
    assert mock_neo4j_connector.execute_query.call_count == 1


def test_process_orders_neo4j_error_on_contains_merge(mocker, mock_neo4j_connector, caplog):
    """Test Neo4j error during CONTAINS relationship MERGE."""
    caplog.set_level(logging.ERROR)
    csv_rows = [{**ORDER_1_PART, **ITEM_1A}]
    mock_csv_file = create_orders_csv_mock_content(ORDERS_CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)

    # Order MERGE and PLACED MERGE succeed, CONTAINS MERGE fails
    mock_neo4j_connector.execute_query.side_effect = [
        [{"o.orderID": 1001}], # Success for Order Merge
        [{"rel_type": "PLACED"}], # Success for Placed Rel Merge
        Neo4jError("Simulated DB error on CONTAINS") # Failure for Contains Rel Merge
    ]

    summary = process_orders_csv("dummy_orders.csv", connector=mock_neo4j_connector)

    assert summary["loaded_orders_count"] == 1
    assert summary["placed_relationships_count"] == 1
    assert summary["loaded_items_relationships_count"] == 0
    assert summary["neo4j_errors"] == 1
    assert "Neo4j error processing CONTAINS rel for OrderItem 2001" in caplog.text
    assert mock_neo4j_connector.execute_query.call_count == 3


# --- Integration Tests (Placeholder - to be filled in next step) ---

@pytest.mark.integration
def test_ingest_orders_full_pipeline_basic(tmp_path, caplog): # Add fixture later
    logging.info("Placeholder for order ingestion integration test. Requires Neo4j instance and pre-existing Customer/Product nodes.")
    pass

# More unit tests could cover:
# - CSV with missing optional fields (e.g. no OrderStatus).
# - FileNotFoundError for CSV.
# - More varied type conversion failures.
# - Scenarios where CustomerID or ProductID in an item row is missing/invalid, preventing relationship creation.
# - What happens if OrderTotalAmount in CSV does not match sum of item totals (currently not cross-validated by script).
# - What happens if OrderDate for the same OrderID differs across rows (current logic takes the first one).
# - Behavior if `connector.execute_query` returns None or unexpected results.
# - Test the `CSVOrderItemData` model directly for its validation rules.

def test_csvorderitemdata_validation():
    valid_data = {"OrderItemID":1, "ProductID":1, "Quantity":1, "UnitPrice":10.0}
    item = CSVOrderItemData(**valid_data)
    assert item.Quantity == 1

    with pytest.raises(PydanticValidationError): # Quantity must be positive
        CSVOrderItemData(OrderItemID=1, ProductID=1, Quantity=0, UnitPrice=10.0)
    with pytest.raises(PydanticValidationError): # UnitPrice must be positive
        CSVOrderItemData(OrderItemID=1, ProductID=1, Quantity=1, UnitPrice=0.0)
    with pytest.raises(PydanticValidationError): # UnitPrice must be positive
        CSVOrderItemData(OrderItemID=1, ProductID=1, Quantity=1, UnitPrice=-1.0)


# --- Integration Tests ---
# Require a running Neo4j instance. Run with: pytest -m integration

@pytest.fixture(scope="module")
def neo4j_order_module_connector_and_setup():
    """
    Pytest fixture for order ingestion integration tests.
    Provides a Neo4jConnector instance and sets up prerequisite Customer and Product nodes.
    Cleans up all created data (Orders, specific Customers, specific Products) afterwards.
    """
    # caplog.set_level(logging.INFO) # Removed: caplog is function-scoped
    connector = None
    # Define IDs for prerequisite and test-created data to manage cleanup
    # These IDs should be distinct from any other tests or sample data loaders
    # to prevent interference.
    test_customer_ids = [9010, 9020]
    test_product_ids = [8010, 8020, 8030]
    test_order_ids_to_cleanup = [] # Will be populated by tests if needed, or use a range

    try:
        connector = Neo4jConnector()
        connector.execute_query("RETURN 1", tx_type='read') # Verify connection
        logging.info("Neo4jConnector initialized for order integration test module.")

        # Setup: Create prerequisite ECCustomer and Product nodes
        logging.info("Setting up prerequisite Customer and Product nodes for order tests...")
        for cid in test_customer_ids:
            connector.execute_query(
                "MERGE (c:ECCustomer {customerID: $cid}) SET c.name = 'Test Customer ' + $cid",
                {"cid": cid}, tx_type='write'
            )
        for pid in test_product_ids:
            connector.execute_query(
                "MERGE (p:Product {productID: $pid}) SET p.name = 'Test Product ' + $pid, p.Price = 10.0", # Add Price for completeness
                {"pid": pid}, tx_type='write'
            )
        logging.info("Prerequisite nodes created.")

        yield connector # Provide connector to tests

    except ServiceUnavailable:
        logging.warning("Neo4j instance not available. Skipping order integration tests.")
        pytest.skip("Neo4j instance not available for order integration tests.")
    except Exception as e:
        logging.error(f"Failed to initialize Neo4jConnector or setup data for order integration tests: {e}", exc_info=True)
        pytest.fail(f"Failed to initialize Neo4jConnector or setup data: {e}")
    finally:
        if connector:
            try:
                logging.info("Cleaning up Neo4j data after order integration test module...")
                # Cleanup Orders created by tests (assuming they might use various OrderIDs)
                # A more robust way would be to collect all OrderIDs created by tests if they are dynamic.
                # For now, using a broader match or specific IDs if known.
                # This example cleans ALL Order nodes - be careful on shared DBs.
                # A safer approach: MATCH (o:Order) WHERE o.orderID >= some_test_min_id DETACH DELETE o
                connector.execute_query("MATCH (o:Order) DETACH DELETE o", tx_type='write')

                # Cleanup prerequisite Customer and Product nodes
                if test_customer_ids:
                    connector.execute_query(
                        f"MATCH (c:ECCustomer) WHERE c.customerID IN {test_customer_ids} DETACH DELETE c",
                        tx_type='write'
                    )
                if test_product_ids:
                    connector.execute_query(
                        f"MATCH (p:Product) WHERE p.productID IN {test_product_ids} DETACH DELETE p",
                        tx_type='write'
                    )
                logging.info("Order integration test cleanup successful.")
            except Exception as e:
                logging.error(f"Error during order integration test Neo4j cleanup: {e}", exc_info=True)
            finally:
                connector.close()


@pytest.mark.integration
def test_ingest_orders_full_pipeline(neo4j_order_module_connector_and_setup, tmp_path, caplog):
    """Integration test for order ingestion: CSV -> Pydantic -> Neo4j."""
    caplog.set_level(logging.INFO)
    connector = neo4j_order_module_connector_and_setup

    # Use CustomerIDs and ProductIDs that were set up by the fixture
    # CustomerIDs: 9010, 9020
    # ProductIDs: 8010, 8020, 8030
    csv_rows = [
        # Order 5001 for Customer 9010, 2 items
        {"OrderID":"5001","CustomerID":"9010","OrderDate":"2023-07-01 10:00:00","OrderStatus":"Delivered","OrderTotalAmount":"120.00","ShippingAddress":"Addr 1","BillingAddress":"Addr 1","OrderItemID":"6001","ProductID":"8010","Quantity":"2","UnitPrice":"50.00"}, # Total 100
        {"OrderID":"5001","CustomerID":"9010","OrderDate":"2023-07-01 10:00:00","OrderStatus":"Delivered","OrderTotalAmount":"120.00","ShippingAddress":"Addr 1","BillingAddress":"Addr 1","OrderItemID":"6002","ProductID":"8020","Quantity":"1","UnitPrice":"20.00"}, # Total 20
        # Order 5002 for Customer 9020, 1 item
        {"OrderID":"5002","CustomerID":"9020","OrderDate":"2023-07-02 11:00:00","OrderStatus":"Shipped","OrderTotalAmount":"30.00","ShippingAddress":"Addr 2","BillingAddress":"Addr 2","OrderItemID":"6003","ProductID":"8030","Quantity":"3","UnitPrice":"10.00"}  # Total 30
    ]
    temp_csv_file = tmp_path / "integration_sample_orders.csv"
    with open(temp_csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=ORDERS_CSV_HEADERS)
        writer.writeheader()
        for row in csv_rows:
            writer.writerow(row)

    summary = process_orders_csv(str(temp_csv_file), connector)

    assert summary["status"] == "Completed"
    assert summary["processed_rows"] == 3
    assert summary["validated_orders_count"] == 2 # Orders 5001, 5002
    assert summary["validated_items_count"] == 3
    assert summary["loaded_orders_count"] == 2
    assert summary["placed_relationships_count"] == 2
    assert summary["loaded_items_relationships_count"] == 3
    assert summary["neo4j_errors"] == 0

    # Verify Order 5001
    order5001 = connector.execute_query("MATCH (o:Order {orderID: 5001}) RETURN o.orderStatus as status, o.totalAmount as total", tx_type='read')
    assert len(order5001) == 1
    assert order5001[0]["status"] == "Delivered"
    assert order5001[0]["total"] == 120.00

    # Verify PLACED relationship for Order 5001
    placed5001 = connector.execute_query("MATCH (c:ECCustomer {customerID: 9010})-[r:PLACED]->(o:Order {orderID: 5001}) RETURN r.date as order_date", tx_type='read')
    assert len(placed5001) == 1
    assert isinstance(placed5001[0]["order_date"], datetime) # Check if date is set

    # Verify CONTAINS relationships for Order 5001
    contains5001 = connector.execute_query(
        "MATCH (o:Order {orderID: 5001})-[r:CONTAINS]->(p:Product) "
        "RETURN r.orderItemID as itemID, r.quantity as qty, r.unitPrice as price, r.totalItemPrice as item_total, p.productID as productID "
        "ORDER BY r.orderItemID", tx_type='read'
    )
    assert len(contains5001) == 2
    assert contains5001[0]["itemID"] == 6001 and contains5001[0]["productID"] == 8010 and contains5001[0]["qty"] == 2 and contains5001[0]["price"] == 50.00 and contains5001[0]["item_total"] == 100.00
    assert contains5001[1]["itemID"] == 6002 and contains5001[1]["productID"] == 8020 and contains5001[1]["qty"] == 1 and contains5001[1]["price"] == 20.00 and contains5001[1]["item_total"] == 20.00

    # Idempotency Check
    logging.info("Running order ingestion again for idempotency check...")
    summary_idem = process_orders_csv(str(temp_csv_file), connector)
    assert summary_idem["loaded_orders_count"] == 2
    assert summary_idem["placed_relationships_count"] == 2
    assert summary_idem["loaded_items_relationships_count"] == 3

    # Check total counts in DB to ensure no duplicates
    order_count = connector.execute_query("MATCH (o:Order) WHERE o.orderID IN [5001, 5002] RETURN count(o) as total", tx_type='read')
    assert order_count[0]["total"] == 2

    placed_rel_count = connector.execute_query("MATCH (:ECCustomer)-[r:PLACED]->(:Order) WHERE r.date IS NOT NULL AND r.date >= datetime('2023-07-01') RETURN count(r) as total", tx_type='read')
    assert placed_rel_count[0]["total"] == 2 # Assuming test dates are unique enough

    contains_rel_count = connector.execute_query("MATCH (:Order)-[r:CONTAINS]->(:Product) WHERE r.orderItemID IN [6001, 6002, 6003] RETURN count(r) as total", tx_type='read')
    assert contains_rel_count[0]["total"] == 3

@pytest.mark.integration
def test_ingest_orders_item_references_nonexistent_product(neo4j_order_module_connector_and_setup, tmp_path, caplog):
    """Test order item referencing a product not in DB (should result in Neo4j error for that item)."""
    caplog.set_level(logging.INFO) # Include INFO for success, WARNING/ERROR for issues
    connector = neo4j_order_module_connector_and_setup

    csv_rows = [
        # Valid order, but ProductID 7777 does not exist (fixture created 8010, 8020, 8030)
        {"OrderID":"5003","CustomerID":"9010","OrderDate":"2023-07-03 10:00:00","OrderStatus":"Pending","OrderTotalAmount":"99.99","ShippingAddress":"Addr 3","BillingAddress":"Addr 3","OrderItemID":"6004","ProductID":"7777","Quantity":"1","UnitPrice":"99.99"},
    ]
    temp_csv_file = tmp_path / "integration_bad_item_ref.csv"
    with open(temp_csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=ORDERS_CSV_HEADERS)
        writer.writeheader()
        writer.writerow(csv_rows[0])

    summary = process_orders_csv(str(temp_csv_file), connector)

    assert summary["status"] == "Completed"
    assert summary["processed_rows"] == 1
    assert summary["validated_orders_count"] == 1 # Order itself is valid
    assert summary["validated_items_count"] == 1  # Item data is Pydantic-valid
    assert summary["loaded_orders_count"] == 1 # Order node gets created
    assert summary["placed_relationships_count"] == 1 # PLACED rel gets created
    assert summary["loaded_items_relationships_count"] == 0 # CONTAINS rel fails
    assert summary["neo4j_errors"] == 1 # Error from trying to MATCH non-existent Product 7777

    assert "Neo4j error processing CONTAINS rel for OrderItem 6004" in caplog.text
    # Check that the Order node 5003 was still created
    order5003 = connector.execute_query("MATCH (o:Order {orderID: 5003}) RETURN o.orderID", tx_type='read')
    assert len(order5003) == 1
    # Check no CONTAINS relationship for order 5003
    contains5003 = connector.execute_query("MATCH (o:Order {orderID: 5003})-[r:CONTAINS]->() RETURN count(r) as count", tx_type='read')
    assert contains5003[0]["count"] == 0
