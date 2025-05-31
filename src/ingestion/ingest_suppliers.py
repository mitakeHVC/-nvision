import csv
import logging
from typing import Optional, Dict, Any, List
from pydantic import ValidationError as PydanticValidationError

from src.data_models.ec_models import Supplier # EC Supplier model
from src.neo4j_utils.connector import Neo4jConnector
from neo4j.exceptions import Neo4jError, ServiceUnavailable

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Helper function for parsing (can be moved to a shared utility module later)
def _parse_int(value: Optional[str]) -> Optional[int]:
    """Safely parse an integer string, returning None if empty, invalid, or non-numeric."""
    if value is None or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError:
        logging.warning(f"Could not parse integer string: '{value}'")
        return None

def process_suppliers_csv(csv_file_path: str, connector: Optional[Neo4jConnector] = None) -> Dict[str, Any]:
    """
    Reads supplier data from a CSV file, validates it using the Pydantic Supplier model,
    logs successes or errors, and optionally loads data into Neo4j.

    Args:
        csv_file_path (str): The path to the CSV file.
        connector (Neo4jConnector, optional): An instance of Neo4jConnector for DB operations.
                                              If None, Neo4j loading steps are skipped.

    Returns:
        Dict[str, Any]: A summary of the processing.
    """
    processed_rows = 0
    validated_suppliers_count = 0
    loaded_suppliers_count = 0
    validation_errors = 0
    type_conversion_errors = 0 # For errors during manual parsing before Pydantic
    neo4j_errors = 0

    logging.info(f"Starting CSV processing for supplier data: {csv_file_path}. Neo4j loading: {'Enabled' if connector else 'Disabled'}")

    try:
        with open(csv_file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row_num, row in enumerate(reader, 1):
                processed_rows += 1
                supplier_id_str = row.get('SupplierID', f'ROW_{row_num}')
                log_prefix = f"Row {row_num} (SupplierID: {supplier_id_str}):"

                try:
                    # Prepare data for Supplier model
                    supplier_data_typed = {
                        'SupplierID': _parse_int(row.get('SupplierID')),
                        'SupplierName': row.get('SupplierName'),
                        'ContactPerson': row.get('ContactPerson'),
                        'Email': row.get('Email'),
                        'PhoneNumber': row.get('PhoneNumber')
                    }

                    supplier_instance = Supplier(**supplier_data_typed)
                    validated_suppliers_count += 1
                    logging.info(f"{log_prefix} Supplier validated: {supplier_instance.SupplierID} - {supplier_instance.SupplierName}")

                    # Load into Neo4j if connector is provided
                    if connector:
                        props = supplier_instance.model_dump(exclude_none=True)
                        # Ensure supplierID is in props for the SET clause, as MERGE key is separate
                        props['supplierID'] = supplier_instance.SupplierID

                        query = "MERGE (s:Supplier {supplierID: $supplierID_param}) SET s = $props RETURN s.supplierID AS id"
                        params = {"supplierID_param": supplier_instance.SupplierID, "props": props}

                        try:
                            result = connector.execute_query(query, params, tx_type='write')
                            if result and result[0]['id'] == supplier_instance.SupplierID:
                                logging.info(f"{log_prefix} Supplier node MERGED: {supplier_instance.SupplierID}")
                                loaded_suppliers_count += 1
                            else:
                                logging.warning(f"{log_prefix} Supplier MERGE did not return expected ID for {supplier_instance.SupplierID}. Result: {result}")
                                neo4j_errors += 1
                        except Neo4jError as e:
                            logging.error(f"{log_prefix} Neo4j error merging Supplier {supplier_instance.SupplierID}: {e}")
                            neo4j_errors += 1
                        except Exception as e:
                            logging.error(f"{log_prefix} Unexpected error during Neo4j operation for Supplier {supplier_instance.SupplierID}: {e}", exc_info=True)
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
            "processed_rows": 0, "validated_suppliers_count": 0, "loaded_suppliers_count": 0,
            "validation_errors": 0, "type_conversion_errors": 0, "neo4j_errors": 0
        }
    except Exception as e:
        logging.error(f"An unexpected error occurred during CSV file processing: {e}", exc_info=True)
        return {
            "status": "Failed", "message": f"Unexpected error: {e}",
            "processed_rows": processed_rows, "validated_suppliers_count": validated_suppliers_count,
            "loaded_suppliers_count": loaded_suppliers_count,
            "validation_errors": validation_errors, "type_conversion_errors": type_conversion_errors,
            "neo4j_errors": neo4j_errors
        }

    summary = {
        "status": "Completed",
        "csv_file_path": csv_file_path,
        "processed_rows": processed_rows,
        "validated_suppliers_count": validated_suppliers_count,
        "loaded_suppliers_count": loaded_suppliers_count,
        "validation_errors": validation_errors,
        "type_conversion_errors": type_conversion_errors,
        "neo4j_errors": neo4j_errors
    }
    logging.info(f"CSV supplier processing finished. Summary: {summary}")
    return summary

if __name__ == "__main__":
    csv_path = "data/sample_suppliers.csv"

    import os
    if not os.path.exists(csv_path):
        logging.error(f"Sample CSV file '{csv_path}' not found. Ensure you are in the project root directory or the path is correct.")
    else:
        processing_summary = None
        try:
            with Neo4jConnector() as connector_instance:
                processing_summary = process_suppliers_csv(csv_path, connector_instance)
        except ServiceUnavailable:
            logging.error("Neo4j service is unavailable. Running CSV validation for suppliers without Neo4j loading.")
            processing_summary = process_suppliers_csv(csv_path, None)
        except Exception as e:
            logging.error(f"Failed to initialize Neo4jConnector or other critical error: {e}. Running CSV validation for suppliers without Neo4j loading.")
            processing_summary = process_suppliers_csv(csv_path, None)

        if processing_summary:
            print("\n--- Supplier Processing Summary ---")
            for key, value in processing_summary.items():
                print(f"{key.replace('_', ' ').title()}: {value}")
        else:
            print("Supplier processing could not be completed due to an early critical error.")
