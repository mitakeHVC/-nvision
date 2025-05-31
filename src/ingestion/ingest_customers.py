import csv
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import ValidationError as PydanticValidationError

from src.data_models.ec_models import Customer # EC Customer model
from src.neo4j_utils.connector import Neo4jConnector
from neo4j.exceptions import Neo4jError, ServiceUnavailable

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Helper functions for parsing (can be moved to a shared utility module later)
def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Safely parse a datetime string from common formats, returning None if empty or invalid."""
    if not value:
        return None
    formats_to_try = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d']
    for fmt in formats_to_try:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    logging.warning(f"Could not parse datetime string: {value} with tried formats.")
    return None

def _parse_int(value: Optional[str]) -> Optional[int]:
    """Safely parse an integer string, returning None if empty, invalid, or non-numeric."""
    if value is None or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError:
        logging.warning(f"Could not parse integer string: '{value}'")
        return None

def process_customers_csv(csv_file_path: str, connector: Optional[Neo4jConnector] = None) -> Dict[str, Any]:
    """
    Reads customer data from a CSV file, validates it using the Pydantic Customer model,
    logs successes or errors, and optionally loads data into Neo4j.

    Args:
        csv_file_path (str): The path to the CSV file.
        connector (Neo4jConnector, optional): An instance of Neo4jConnector for DB operations.
                                              If None, Neo4j loading steps are skipped.

    Returns:
        Dict[str, Any]: A summary of the processing.
    """
    processed_rows = 0
    validated_customers_count = 0
    loaded_customers_count = 0
    validation_errors = 0
    type_conversion_errors = 0 # For errors during manual parsing before Pydantic
    neo4j_errors = 0

    logging.info(f"Starting CSV processing for customer data: {csv_file_path}. Neo4j loading: {'Enabled' if connector else 'Disabled'}")

    try:
        with open(csv_file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row_num, row in enumerate(reader, 1):
                processed_rows += 1
                customer_id_str = row.get('CustomerID', f'ROW_{row_num}')
                log_prefix = f"Row {row_num} (CustomerID: {customer_id_str}):"

                try:
                    # Prepare data for Customer model
                    customer_data_typed = {
                        'CustomerID': _parse_int(row.get('CustomerID')),
                        'FirstName': row.get('FirstName'),
                        'LastName': row.get('LastName'),
                        'Email': row.get('Email'),
                        'PhoneNumber': row.get('PhoneNumber'),
                        'ShippingAddress': row.get('ShippingAddress'),
                        'BillingAddress': row.get('BillingAddress'),
                        'RegistrationDate': _parse_datetime(row.get('RegistrationDate')),
                        'LastLoginDate': _parse_datetime(row.get('LastLoginDate'))
                    }

                    customer_instance = Customer(**customer_data_typed)
                    validated_customers_count += 1
                    logging.info(f"{log_prefix} Customer validated: {customer_instance.CustomerID} - {customer_instance.Email}")

                    # Load into Neo4j if connector is provided
                    if connector:
                        # Use model_dump for Pydantic v2, or .dict() for v1
                        props = customer_instance.model_dump(exclude_none=True)
                        # Ensure customerID is in props for the SET clause
                        props['customerID'] = customer_instance.CustomerID

                        query = "MERGE (c:ECCustomer {customerID: $customerID}) SET c = $props RETURN c.customerID AS id"
                        params = {"customerID": customer_instance.CustomerID, "props": props}

                        try:
                            result = connector.execute_query(query, params, tx_type='write')
                            if result and result[0]['id'] == customer_instance.CustomerID:
                                logging.info(f"{log_prefix} ECCustomer node MERGED: {customer_instance.CustomerID}")
                                loaded_customers_count += 1
                            else:
                                logging.warning(f"{log_prefix} ECCustomer MERGE did not return expected ID for {customer_instance.CustomerID}. Result: {result}")
                                neo4j_errors += 1 # Count as error if result is not as expected
                        except Neo4jError as e:
                            logging.error(f"{log_prefix} Neo4j error merging ECCustomer {customer_instance.CustomerID}: {e}")
                            neo4j_errors += 1
                        except Exception as e: # Catch other unexpected errors during Neo4j operation
                            logging.error(f"{log_prefix} Unexpected error during Neo4j operation for ECCustomer {customer_instance.CustomerID}: {e}", exc_info=True)
                            neo4j_errors += 1

                except PydanticValidationError as e:
                    logging.error(f"{log_prefix} Validation error: {e.errors()} for data {dict(row)}")
                    validation_errors += 1
                except Exception as e:
                    logging.error(f"{log_prefix} Unexpected error processing row: {e} for data {dict(row)}", exc_info=True)
                    type_conversion_errors +=1

    except FileNotFoundError:
        logging.error(f"Error: CSV file not found at {csv_file_path}")
        return {
            "status": "Failed", "message": f"File not found: {csv_file_path}",
            "processed_rows": 0, "validated_customers_count": 0, "loaded_customers_count": 0,
            "validation_errors": 0, "type_conversion_errors": 0, "neo4j_errors": 0
        }
    except Exception as e:
        logging.error(f"An unexpected error occurred during CSV file processing: {e}", exc_info=True)
        return {
            "status": "Failed", "message": f"Unexpected error: {e}",
            "processed_rows": processed_rows, "validated_customers_count": validated_customers_count,
            "loaded_customers_count": loaded_customers_count,
            "validation_errors": validation_errors, "type_conversion_errors": type_conversion_errors,
            "neo4j_errors": neo4j_errors
        }

    summary = {
        "status": "Completed",
        "csv_file_path": csv_file_path,
        "processed_rows": processed_rows,
        "validated_customers_count": validated_customers_count,
        "loaded_customers_count": loaded_customers_count,
        "validation_errors": validation_errors,
        "type_conversion_errors": type_conversion_errors,
        "neo4j_errors": neo4j_errors
    }
    logging.info(f"CSV customer processing finished. Summary: {summary}")
    return summary

if __name__ == "__main__":
    csv_path = "data/sample_customers.csv"

    import os
    if not os.path.exists(csv_path):
        logging.error(f"Sample CSV file '{csv_path}' not found. Ensure you are in the project root directory or the path is correct.")
    else:
        processing_summary = None
        try:
            with Neo4jConnector() as connector_instance:
                processing_summary = process_customers_csv(csv_path, connector_instance)
        except ServiceUnavailable:
            logging.error("Neo4j service is unavailable. Running CSV validation for customers without Neo4j loading.")
            processing_summary = process_customers_csv(csv_path, None)
        except Exception as e:
            logging.error(f"Failed to initialize Neo4jConnector or other critical error: {e}. Running CSV validation for customers without Neo4j loading.")
            processing_summary = process_customers_csv(csv_path, None)

        if processing_summary:
            print("\n--- Customer Processing Summary ---")
            for key, value in processing_summary.items():
                print(f"{key.replace('_', ' ').title()}: {value}")
        else:
            print("Customer processing could not be completed due to an early critical error.")
