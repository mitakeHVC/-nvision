import pytest
import csv
import io
import logging
from unittest.mock import MagicMock, call
from datetime import datetime

from pydantic import ValidationError as PydanticValidationError

from src.data_models.ec_models import CustomerReview
from src.ingestion.ingest_reviews import process_reviews_csv
from src.neo4j_utils.connector import Neo4jConnector
from neo4j.exceptions import Neo4jError, ServiceUnavailable


# --- Unit Tests ---

@pytest.fixture
def mock_neo4j_connector(mocker):
    """Fixture to mock Neo4jConnector for review ingestion unit tests."""
    mock_conn = MagicMock(spec=Neo4jConnector)
    # Default behavior: successful query execution returning a mock ID or relevant data
    # Simulate list of dicts as records for general case
    mock_conn.execute_query.return_value = [{"id_or_type": "mock_result"}]
    return mock_conn

def create_reviews_csv_mock_content(headers, rows_as_dicts):
    """Helper to create in-memory CSV content for reviews."""
    si = io.StringIO()
    writer = csv.DictWriter(si, fieldnames=headers)
    writer.writeheader()
    for row in rows_as_dicts:
        writer.writerow(row)
    si.seek(0)
    return si

REVIEWS_CSV_HEADERS = [
    "ReviewID","CustomerID","ProductID","Rating","ReviewText",
    "ReviewDate","SentimentScore","SentimentLabel"
]

VALID_REVIEW_ROW_1 = {
    "ReviewID":"701","CustomerID":"1","ProductID":"101","Rating":"5",
    "ReviewText":"Great product!","ReviewDate":"2023-01-20 15:00:00",
    "SentimentScore":"0.92","SentimentLabel":"Positive"
}
VALID_REVIEW_ROW_2 = {
    "ReviewID":"702","CustomerID":"2","ProductID":"102","Rating":"4",
    "ReviewText":"Good, but could be better.","ReviewDate":"2023-02-18 10:30:00",
    "SentimentScore":"0.45","SentimentLabel":"Positive" # Changed Neutral to Positive for variety
}

def test_process_valid_reviews_no_neo4j(mocker, caplog):
    """Test valid CSV processing without Neo4j interaction."""
    caplog.set_level(logging.INFO)
    csv_rows = [VALID_REVIEW_ROW_1, VALID_REVIEW_ROW_2]
    mock_csv_file = create_reviews_csv_mock_content(REVIEWS_CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)

    summary = process_reviews_csv("dummy_reviews.csv", connector=None)

    assert summary["processed_rows"] == 2
    assert summary["validated_reviews_count"] == 2
    assert summary["loaded_review_nodes_count"] == 0 # No connector
    assert summary["loaded_wrote_review_rels_count"] == 0
    assert summary["loaded_has_review_rels_count"] == 0
    assert summary["validation_errors"] == 0
    assert "Review validated: 701" in caplog.text
    assert "Review validated: 702" in caplog.text

def test_process_reviews_pydantic_validation_errors(mocker, caplog):
    """Test CSV with data causing Pydantic validation errors (e.g., bad Rating)."""
    caplog.set_level(logging.ERROR)
    csv_rows = [
        VALID_REVIEW_ROW_1, # Valid
        {"ReviewID":"703","CustomerID":"1","ProductID":"103","Rating":"6", # Invalid Rating
         "ReviewText":"Rating too high!","ReviewDate":"2023-03-05 12:00:00",
         "SentimentScore":"0.0","SentimentLabel":"Neutral"},
        {"ReviewID":"-704","CustomerID":"2","ProductID":"101","Rating":"3", # Invalid ReviewID
         "ReviewText":"Bad ID.","ReviewDate":"2023-03-06 12:00:00",
         "SentimentScore":"0.0","SentimentLabel":"Neutral"},
    ]
    mock_csv_file = create_reviews_csv_mock_content(REVIEWS_CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)

    summary = process_reviews_csv("dummy_reviews.csv", connector=None)

    assert summary["processed_rows"] == 3
    assert summary["validated_reviews_count"] == 1 # Only the first one
    assert summary["validation_errors"] == 2
    assert "Validation error" in caplog.text

def test_process_reviews_type_conversion_error(mocker, caplog):
    """Test CSV with type conversion errors (e.g., bad date, non-numeric score)."""
    # Errors from _parse_xxx are warnings. Pydantic error if required field becomes None.
    caplog.set_level(logging.WARNING) # To catch parsing warnings
    csv_rows = [
        {"ReviewID":"705","CustomerID":"3","ProductID":"104","Rating":"4",
         "ReviewText":"Bad date here.","ReviewDate":"not-a-date-at-all", # Invalid date
         "SentimentScore":"not-a-float","SentimentLabel":"Neutral"}, # Invalid float
    ]
    mock_csv_file = create_reviews_csv_mock_content(REVIEWS_CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)

    # Run with error level to catch Pydantic errors if required fields become None
    with caplog.at_level(logging.ERROR):
        summary = process_reviews_csv("dummy_reviews.csv", connector=None)

    assert summary["processed_rows"] == 1
    # ReviewDate and SentimentScore are Optional in Pydantic model, so None is fine
    assert summary["validated_reviews_count"] == 1
    assert summary["validation_errors"] == 0 # No Pydantic validation errors for this specific case
    assert "Could not parse datetime string: not-a-date-at-all" in caplog.text
    assert "Could not parse float string: 'not-a-float'" in caplog.text

def test_process_reviews_mocked_neo4j_calls_full_success(mocker, mock_neo4j_connector, caplog):
    """Test correct Neo4j calls for a valid review with Customer and Product."""
    caplog.set_level(logging.INFO)
    csv_rows = [VALID_REVIEW_ROW_1]
    mock_csv_file = create_reviews_csv_mock_content(REVIEWS_CSV_HEADERS, csv_rows)
    mocker.patch('builtins.open', return_value=mock_csv_file)

    # Configure specific return values for each call if needed for more complex tests
    # For this test, the default mock_id return is fine for successful MERGE.
    mock_neo4j_connector.execute_query.return_value = [{"id_or_type": "mock_result"}]


    summary = process_reviews_csv("dummy_reviews.csv", connector=mock_neo4j_connector)

    assert summary["loaded_review_nodes_count"] == 1
    assert summary["loaded_wrote_review_rels_count"] == 1
    assert summary["loaded_has_review_rels_count"] == 1
    assert summary["neo4j_errors"] == 0

    assert mock_neo4j_connector.execute_query.call_count == 3

    # Call 1: Merge Review Node
    call_review_node = mock_neo4j_connector.execute_query.call_args_list[0]
    assert "MERGE (rev:Review {reviewID: $reviewID_param})" in call_review_node.args[0]
    assert call_review_node.kwargs['params']['reviewID_param'] == 701
    assert call_review_node.kwargs['params']['props']['ReviewText'] == "Great product!"

    # Call 2: Merge WROTE_REVIEW Relationship
    call_wrote_rel = mock_neo4j_connector.execute_query.call_args_list[1]
    assert "MATCH (c:ECCustomer {customerID: $customerID})" in call_wrote_rel.args[0]
    assert "MATCH (rev:Review {reviewID: $reviewID})" in call_wrote_rel.args[0]
    assert "MERGE (c)-[r:WROTE_REVIEW]->(rev)" in call_wrote_rel.args[0]
    assert call_wrote_rel.kwargs['params']['customerID'] == 1
    assert call_wrote_rel.kwargs['params']['reviewID'] == 701

    # Call 3: Merge HAS_REVIEW Relationship
    call_has_rel = mock_neo4j_connector.execute_query.call_args_list[2]
    assert "MATCH (p:Product {productID: $productID})" in call_has_rel.args[0]
    assert "MATCH (rev:Review {reviewID: $reviewID})" in call_has_rel.args[0]
    assert "MERGE (p)-[r:HAS_REVIEW]->(rev)" in call_has_rel.args[0]
    assert call_has_rel.kwargs['params']['productID'] == 101
    assert call_has_rel.kwargs['params']['reviewID'] == 701

def test_process_reviews_skip_rels_if_ids_missing(mocker, mock_neo4j_connector, caplog):
    """Test that relationships are skipped if CustomerID or ProductID is missing."""
    caplog.set_level(logging.INFO)
    csv_row_no_cid = {"ReviewID":"707","CustomerID":"","ProductID":"103","Rating":"4","ReviewText":"No customer ID here","ReviewDate":"2023-01-01 00:00:00","SentimentScore":"0.5","SentimentLabel":"Positive"}
    csv_row_no_pid = {"ReviewID":"708","CustomerID":"3","ProductID":"","Rating":"3","ReviewText":"No product ID here","ReviewDate":"2023-01-02 00:00:00","SentimentScore":"0.0","SentimentLabel":"Neutral"}

    mock_csv_file = create_reviews_csv_mock_content(REVIEWS_CSV_HEADERS, [csv_row_no_cid, csv_row_no_pid])
    mocker.patch('builtins.open', return_value=mock_csv_file)

    process_reviews_csv("dummy_reviews.csv", connector=mock_neo4j_connector)

    # For row_no_cid (Review 707): 1 call for Review node, 0 for WROTE_REVIEW, 1 for HAS_REVIEW
    # For row_no_pid (Review 708): 1 call for Review node, 1 for WROTE_REVIEW, 0 for HAS_REVIEW
    # Total calls = (1+0+1) + (1+1+0) = 4
    assert mock_neo4j_connector.execute_query.call_count == 4
    assert "No CustomerID for Review 707, skipping WROTE_REVIEW" in caplog.text
    assert "No ProductID for Review 708, skipping HAS_REVIEW" in caplog.text


def test_process_reviews_neo4j_error_on_review_node(mocker, mock_neo4j_connector, caplog):
    """Test Neo4j error during Review node MERGE."""
    caplog.set_level(logging.ERROR)
    mock_csv_file = create_reviews_csv_mock_content(REVIEWS_CSV_HEADERS, [VALID_REVIEW_ROW_1])
    mocker.patch('builtins.open', return_value=mock_csv_file)
    mock_neo4j_connector.execute_query.side_effect = Neo4jError("Simulated DB error on Review node")

    summary = process_reviews_csv("dummy_reviews.csv", connector=mock_neo4j_connector)

    assert summary["loaded_review_nodes_count"] == 0
    assert summary["loaded_wrote_review_rels_count"] == 0
    assert summary["loaded_has_review_rels_count"] == 0
    assert summary["neo4j_errors"] == 1
    assert "Neo4j error merging Review node 701" in caplog.text
    assert mock_neo4j_connector.execute_query.call_count == 1 # Only first call attempted


# --- Integration Tests ---
# Require a running Neo4j instance. Run with: pytest -m integration

@pytest.fixture(scope="module")
def neo4j_review_module_connector_and_setup(caplog):
    """
    Pytest fixture for review ingestion integration tests.
    Provides a Neo4jConnector, sets up prerequisite Customer & Product nodes, and cleans up.
    """
    caplog.set_level(logging.INFO)
    connector = None
    # Define IDs for prerequisite and test-created data
    test_customer_ids = [9050, 9060]
    test_product_ids = [8050, 8060]
    # ReviewIDs will be generated by tests, cleanup will target Review label or specific IDs if tracked

    try:
        connector = Neo4jConnector()
        connector.execute_query("RETURN 1", tx_type='read') # Verify connection
        logging.info("Neo4jConnector initialized for review integration test module.")

        # Setup: Create prerequisite ECCustomer and Product nodes
        logging.info("Setting up prerequisite Customer and Product nodes for review tests...")
        for cid in test_customer_ids:
            connector.execute_query(
                "MERGE (c:ECCustomer {customerID: $cid}) SET c.name = 'Review Test Customer ' + $cid",
                {"cid": cid}, tx_type='write'
            )
        for pid in test_product_ids:
            connector.execute_query(
                "MERGE (p:Product {productID: $pid}) SET p.name = 'Review Test Product ' + $pid, p.Price = 20.0",
                {"pid": pid}, tx_type='write'
            )
        logging.info("Prerequisite Customer/Product nodes for reviews created.")

        yield connector # Provide connector to tests

    except ServiceUnavailable:
        logging.warning("Neo4j instance not available. Skipping review integration tests.")
        pytest.skip("Neo4j instance not available for review integration tests.")
    except Exception as e:
        logging.error(f"Failed to initialize Neo4jConnector or setup data for review integration tests: {e}", exc_info=True)
        pytest.fail(f"Failed to initialize Neo4jConnector or setup data for reviews: {e}")
    finally:
        if connector:
            try:
                logging.info("Cleaning up Neo4j data after review integration test module...")
                # Cleanup Review nodes (safer: use specific IDs if tests generate them predictably)
                # For this example, assuming test ReviewIDs might be in a certain range or just delete all.
                # To be very safe, one might add a temporary label to test reviews.
                connector.execute_query("MATCH (rev:Review) WHERE rev.reviewID >= 900 DETACH DELETE rev", tx_type='write') # Assuming test ReviewIDs are >= 900

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
                logging.info("Review integration test cleanup successful.")
            except Exception as e:
                logging.error(f"Error during review integration test Neo4j cleanup: {e}", exc_info=True)
            finally:
                connector.close()

@pytest.mark.integration
def test_ingest_reviews_full_pipeline(neo4j_review_module_connector_and_setup, tmp_path, caplog):
    """Integration test for review ingestion: CSV -> Pydantic -> Neo4j relationships."""
    caplog.set_level(logging.INFO)
    connector = neo4j_review_module_connector_and_setup

    # CustomerIDs: 9050, 9060 | ProductIDs: 8050, 8060
    review_id_1 = 901
    review_id_2 = 902
    csv_rows = [
        {"ReviewID":str(review_id_1),"CustomerID":"9050","ProductID":"8050","Rating":"5","ReviewText":"Fantastic!","ReviewDate":"2023-08-01 10:00:00","SentimentScore":"0.95","SentimentLabel":"Positive"},
        {"ReviewID":str(review_id_2),"CustomerID":"9060","ProductID":"8060","Rating":"2","ReviewText":"Not good.","ReviewDate":"2023-08-02 11:00:00","SentimentScore":"-0.7","SentimentLabel":"Negative"},
    ]
    temp_csv_file = tmp_path / "integration_sample_reviews.csv"
    with open(temp_csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=REVIEWS_CSV_HEADERS)
        writer.writeheader()
        for row in csv_rows:
            writer.writerow(row)

    summary = process_reviews_csv(str(temp_csv_file), connector)

    assert summary["status"] == "Completed"
    assert summary["processed_rows"] == 2
    assert summary["validated_reviews_count"] == 2
    assert summary["loaded_review_nodes_count"] == 2
    assert summary["loaded_wrote_review_rels_count"] == 2
    assert summary["loaded_has_review_rels_count"] == 2
    assert summary["neo4j_errors"] == 0

    # Verify Review 901 and its relationships
    rev901 = connector.execute_query(f"MATCH (rev:Review {{reviewID: {review_id_1}}}) RETURN rev.reviewText as text, rev.rating as rating", tx_type='read')
    assert len(rev901) == 1 and rev901[0]["text"] == "Fantastic!" and rev901[0]["rating"] == 5

    wrote901 = connector.execute_query(f"MATCH (:ECCustomer {{customerID: 9050}})-[r:WROTE_REVIEW]->(:Review {{reviewID: {review_id_1}}}) RETURN type(r) as rel_type", tx_type='read')
    assert len(wrote901) == 1 and wrote901[0]["rel_type"] == "WROTE_REVIEW"

    has901 = connector.execute_query(f"MATCH (:Product {{productID: 8050}})-[r:HAS_REVIEW]->(:Review {{reviewID: {review_id_1}}}) RETURN type(r) as rel_type", tx_type='read')
    assert len(has901) == 1 and has901[0]["rel_type"] == "HAS_REVIEW"

    # Idempotency Check
    logging.info("Running review ingestion again for idempotency check...")
    summary_idem = process_reviews_csv(str(temp_csv_file), connector)
    assert summary_idem["loaded_review_nodes_count"] == 2 # Nodes are MERGED
    assert summary_idem["loaded_wrote_review_rels_count"] == 2 # Rels are MERGED
    assert summary_idem["loaded_has_review_rels_count"] == 2 # Rels are MERGED

    review_count = connector.execute_query(f"MATCH (rev:Review) WHERE rev.reviewID IN [{review_id_1}, {review_id_2}] RETURN count(rev) as total", tx_type='read')
    assert review_count[0]["total"] == 2

@pytest.mark.integration
def test_ingest_review_for_nonexistent_customer_or_product(neo4j_review_module_connector_and_setup, tmp_path, caplog):
    """Test review ingestion where Customer or Product for relationship doesn't exist."""
    caplog.set_level(logging.WARNING) # Expect warnings for failed relationship merges
    connector = neo4j_review_module_connector_and_setup

    review_id_no_cust = 903
    review_id_no_prod = 904
    non_existent_cust_id = 99999
    non_existent_prod_id = 88888

    csv_rows = [
        # Review node should be created, WROTE_REVIEW should fail, HAS_REVIEW should succeed
        {"ReviewID":str(review_id_no_cust),"CustomerID":str(non_existent_cust_id),"ProductID":"8050","Rating":"3","ReviewText":"Cust DNE","ReviewDate":"2023-08-03 10:00:00","SentimentScore":"0.0","SentimentLabel":"Neutral"},
        # Review node should be created, WROTE_REVIEW should succeed, HAS_REVIEW should fail
        {"ReviewID":str(review_id_no_prod),"CustomerID":"9050","ProductID":str(non_existent_prod_id),"Rating":"3","ReviewText":"Prod DNE","ReviewDate":"2023-08-04 10:00:00","SentimentScore":"0.0","SentimentLabel":"Neutral"},
    ]
    temp_csv_file = tmp_path / "integration_sample_reviews_bad_refs.csv"
    with open(temp_csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=REVIEWS_CSV_HEADERS)
        writer.writeheader()
        for row in csv_rows:
            writer.writerow(row)

    summary = process_reviews_csv(str(temp_csv_file), connector)

    assert summary["status"] == "Completed"
    assert summary["processed_rows"] == 2
    assert summary["validated_reviews_count"] == 2
    assert summary["loaded_review_nodes_count"] == 2 # Both review nodes should be created
    assert summary["loaded_wrote_review_rels_count"] == 1 # Only for review_id_no_prod
    assert summary["loaded_has_review_rels_count"] == 1   # Only for review_id_no_cust
    # Each failed relationship MERGE (due to failed MATCH) is logged as a warning by the script,
    # but the query itself doesn't raise Neo4jError if MATCH yields nothing for an OPTIONAL MATCH like pattern.
    # The script logs a warning if the result of execute_query is None/empty.
    # Here, if MATCH fails, MERGE is skipped, execute_query returns empty list.
    # So, this should be counted as a "neo4j_error" by current script logic if result is empty.
    # The script logic was: if result_wrote: log success else log warning, neo4j_errors+=1
    # This logic is slightly flawed, as an empty result from MERGE (if MATCH failed) isn't a Neo4jError.
    # Let's assume the script's current logging/counting for this.
    # If MATCH fails, MERGE on rel is skipped, result is empty. Script logs warning, increments neo4j_errors.
    assert summary["neo4j_errors"] == 2 # One for WROTE_REVIEW, one for HAS_REVIEW

    # Verify Review nodes were created
    rev_no_cust = connector.execute_query(f"MATCH (rev:Review {{reviewID: {review_id_no_cust}}}) RETURN rev.reviewID", tx_type='read')
    assert len(rev_no_cust) == 1
    rev_no_prod = connector.execute_query(f"MATCH (rev:Review {{reviewID: {review_id_no_prod}}}) RETURN rev.reviewID", tx_type='read')
    assert len(rev_no_prod) == 1

    # Verify relationships (or lack thereof)
    wrote_rel_fail = connector.execute_query(f"MATCH (:ECCustomer)-[r:WROTE_REVIEW]->(:Review {{reviewID: {review_id_no_cust}}}) RETURN type(r)", tx_type='read')
    assert len(wrote_rel_fail) == 0 # Should not exist

    has_rel_ok = connector.execute_query(f"MATCH (:Product {{productID: 8050}})-[r:HAS_REVIEW]->(:Review {{reviewID: {review_id_no_cust}}}) RETURN type(r)", tx_type='read')
    assert len(has_rel_ok) == 1 # Should exist

    wrote_rel_ok = connector.execute_query(f"MATCH (:ECCustomer {{customerID: 9050}})-[r:WROTE_REVIEW]->(:Review {{reviewID: {review_id_no_prod}}}) RETURN type(r)", tx_type='read')
    assert len(wrote_rel_ok) == 1 # Should exist

    has_rel_fail = connector.execute_query(f"MATCH (:Product)-[r:HAS_REVIEW]->(:Review {{reviewID: {review_id_no_prod}}}) RETURN type(r)", tx_type='read')
    assert len(has_rel_fail) == 0 # Should not exist

    assert f"WROTE_REVIEW MERGE did not return for R:{review_id_no_cust} C:{non_existent_cust_id}" in caplog.text
    assert f"HAS_REVIEW MERGE did not return for R:{review_id_no_prod} P:{non_existent_prod_id}" in caplog.text
