import csv
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import ValidationError as PydanticValidationError

from src.data_models.ec_models import CustomerReview
from src.neo4j_utils.connector import Neo4jConnector
from neo4j.exceptions import Neo4jError, ServiceUnavailable

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Helper functions
def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value: return None
    formats_to_try = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d']
    for fmt in formats_to_try:
        try: return datetime.strptime(value, fmt)
        except ValueError: continue
    logging.warning(f"Could not parse datetime string: {value} with tried formats.")
    return None

def _parse_int(value: Optional[str]) -> Optional[int]:
    if value is None or value.strip() == "": return None
    try: return int(value)
    except ValueError: logging.warning(f"Could not parse integer string: '{value}'"); return None

def _parse_float(value: Optional[str]) -> Optional[float]:
    if value is None or value.strip() == "": return None
    try: return float(value)
    except ValueError: logging.warning(f"Could not parse float string: '{value}'"); return None

def process_reviews_csv(csv_file_path: str, connector: Optional[Neo4jConnector] = None) -> Dict[str, Any]:
    """
    Reads customer review data from a CSV, validates it, and loads into Neo4j,
    including relationships to customers and products.
    """
    processed_rows = 0
    validated_reviews_count = 0
    loaded_review_nodes_count = 0
    loaded_wrote_review_rels_count = 0
    loaded_has_review_rels_count = 0
    validation_errors = 0
    type_conversion_errors = 0
    neo4j_errors = 0

    logging.info(f"Starting CSV processing for review data: {csv_file_path}. Neo4j loading: {'Enabled' if connector else 'Disabled'}")

    try:
        with open(csv_file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row_num, row in enumerate(reader, 1):
                processed_rows += 1
                review_id_str = row.get('ReviewID', f'ROW_{row_num}')
                log_prefix = f"Row {row_num} (ReviewID: {review_id_str}):"
                review_instance = None # To hold the validated Pydantic model

                try:
                    review_data_typed = {
                        'ReviewID': _parse_int(row.get('ReviewID')),
                        'CustomerID': _parse_int(row.get('CustomerID')),
                        'ProductID': _parse_int(row.get('ProductID')),
                        'Rating': _parse_int(row.get('Rating')),
                        'ReviewText': row.get('ReviewText'),
                        'ReviewDate': _parse_datetime(row.get('ReviewDate')),
                        'SentimentScore': _parse_float(row.get('SentimentScore')),
                        'SentimentLabel': row.get('SentimentLabel')
                    }

                    review_instance = CustomerReview(**review_data_typed)
                    validated_reviews_count += 1
                    logging.info(f"{log_prefix} Review validated: {review_instance.ReviewID}")

                    if connector:
                        # 1. Merge Review Node
                        review_props = review_instance.model_dump(exclude_none=True)
                        review_props['reviewID'] = review_instance.ReviewID # Ensure merge key in props for SET

                        query_review_node = "MERGE (rev:Review {reviewID: $reviewID_param}) SET rev = $props RETURN rev.reviewID AS id"
                        params_review_node = {"reviewID_param": review_instance.ReviewID, "props": review_props}

                        review_node_created_or_merged = False
                        try:
                            result_node = connector.execute_query(query_review_node, params_review_node, tx_type='write')
                            if result_node and result_node[0]['id'] == review_instance.ReviewID:
                                logging.info(f"{log_prefix} Review node MERGED: {review_instance.ReviewID}")
                                loaded_review_nodes_count +=1 # Count successful MERGE of node
                                review_node_created_or_merged = True
                            else:
                                logging.error(f"{log_prefix} Review node MERGE failed or no return for {review_instance.ReviewID}")
                                neo4j_errors +=1
                        except Neo4jError as e:
                            logging.error(f"{log_prefix} Neo4j error merging Review node {review_instance.ReviewID}: {e}")
                            neo4j_errors += 1
                            continue # Skip relationships if node failed

                        if not review_node_created_or_merged:
                            continue

                        # 2. Merge WROTE_REVIEW Relationship (if CustomerID exists)
                        if review_instance.CustomerID:
                            query_wrote_rel = (
                                "MATCH (c:ECCustomer {customerID: $customerID}) "
                                "MATCH (rev:Review {reviewID: $reviewID}) "
                                "MERGE (c)-[r:WROTE_REVIEW]->(rev) RETURN type(r) as rel_type"
                            )
                            params_wrote_rel = {"customerID": review_instance.CustomerID, "reviewID": review_instance.ReviewID}
                            try:
                                result_wrote = connector.execute_query(query_wrote_rel, params_wrote_rel, tx_type='write')
                                if result_wrote:
                                    logging.info(f"{log_prefix} WROTE_REVIEW relationship MERGED for Review {review_instance.ReviewID} to Customer {review_instance.CustomerID}")
                                    loaded_wrote_review_rels_count +=1
                                else: # Should not happen if MATCHes succeed and MERGE is valid
                                     logging.warning(f"{log_prefix} WROTE_REVIEW MERGE did not return for R:{review_instance.ReviewID} C:{review_instance.CustomerID}")
                                     # Not necessarily a neo4j_error if query ran but didn't create/match due to data issues
                            except Neo4jError as e: # Catches if Customer doesn't exist or other DB issues
                                logging.error(f"{log_prefix} Neo4j error merging WROTE_REVIEW for Review {review_instance.ReviewID}: {e}")
                                neo4j_errors += 1
                        else:
                            logging.warning(f"{log_prefix} No CustomerID for Review {review_instance.ReviewID}, skipping WROTE_REVIEW.")

                        # 3. Merge HAS_REVIEW Relationship (if ProductID exists)
                        if review_instance.ProductID:
                            query_has_rel = (
                                "MATCH (p:Product {productID: $productID}) "
                                "MATCH (rev:Review {reviewID: $reviewID}) "
                                "MERGE (p)-[r:HAS_REVIEW]->(rev) RETURN type(r) as rel_type"
                            )
                            params_has_rel = {"productID": review_instance.ProductID, "reviewID": review_instance.ReviewID}
                            try:
                                result_has = connector.execute_query(query_has_rel, params_has_rel, tx_type='write')
                                if result_has:
                                    logging.info(f"{log_prefix} HAS_REVIEW relationship MERGED for Review {review_instance.ReviewID} to Product {review_instance.ProductID}")
                                    loaded_has_review_rels_count +=1
                                else:
                                    logging.warning(f"{log_prefix} HAS_REVIEW MERGE did not return for R:{review_instance.ReviewID} P:{review_instance.ProductID}")
                            except Neo4jError as e: # Catches if Product doesn't exist or other DB issues
                                logging.error(f"{log_prefix} Neo4j error merging HAS_REVIEW for Review {review_instance.ReviewID}: {e}")
                                neo4j_errors += 1
                        else:
                            logging.warning(f"{log_prefix} No ProductID for Review {review_instance.ReviewID}, skipping HAS_REVIEW.")

                except PydanticValidationError as e:
                    logging.error(f"{log_prefix} Validation error: {e.errors()} for data {dict(row)}")
                    validation_errors += 1
                except Exception as e:
                    logging.error(f"{log_prefix} Unexpected error processing row: {e} for data {dict(row)}", exc_info=True)
                    type_conversion_errors +=1

    except FileNotFoundError:
        logging.error(f"Error: CSV file not found at {csv_file_path}")
        # Ensure all count keys are present in the returned dict
        return {"status": "Failed", "message": f"File not found: {csv_file_path}", "processed_rows": 0, "validated_reviews_count": 0, "loaded_review_nodes_count": 0, "loaded_wrote_review_rels_count":0, "loaded_has_review_rels_count":0, "validation_errors": 0, "type_conversion_errors": 0, "neo4j_errors": 0}
    except Exception as e:
        logging.error(f"An unexpected error occurred during CSV file processing: {e}", exc_info=True)
        return {"status": "Failed", "message": f"Unexpected error: {e}", "processed_rows": processed_rows, "validated_reviews_count": validated_reviews_count, "loaded_review_nodes_count": loaded_review_nodes_count, "loaded_wrote_review_rels_count":loaded_wrote_review_rels_count, "loaded_has_review_rels_count":loaded_has_review_rels_count, "validation_errors": validation_errors, "type_conversion_errors": type_conversion_errors, "neo4j_errors": neo4j_errors}

    summary = {
        "status": "Completed",
        "csv_file_path": csv_file_path,
        "processed_rows": processed_rows,
        "validated_reviews_count": validated_reviews_count,
        "loaded_review_nodes_count": loaded_review_nodes_count,
        "loaded_wrote_review_rels_count": loaded_wrote_review_rels_count,
        "loaded_has_review_rels_count": loaded_has_review_rels_count,
        "validation_errors": validation_errors,
        "type_conversion_errors": type_conversion_errors,
        "neo4j_errors": neo4j_errors
    }
    logging.info(f"CSV review processing finished. Summary: {summary}")
    return summary

if __name__ == "__main__":
    csv_path = "data/sample_reviews.csv"

    import os
    if not os.path.exists(csv_path):
        logging.error(f"Sample CSV file '{csv_path}' not found. Ensure you are in the project root directory or the path is correct.")
    else:
        processing_summary = None
        try:
            with Neo4jConnector() as connector_instance:
                processing_summary = process_reviews_csv(csv_path, connector_instance)
        except ServiceUnavailable:
            logging.error("Neo4j service is unavailable. Running CSV validation for reviews without Neo4j loading.")
            processing_summary = process_reviews_csv(csv_path, None)
        except Exception as e:
            logging.error(f"Failed to initialize Neo4jConnector or other critical error: {e}. Running CSV validation for reviews without Neo4j loading.")
            processing_summary = process_reviews_csv(csv_path, None)

        if processing_summary:
            print("\n--- Review Processing Summary ---")
            for key, value in processing_summary.items():
                print(f"{key.replace('_', ' ').title()}: {value}")
        else:
            print("Review processing could not be completed due to an early critical error.")
