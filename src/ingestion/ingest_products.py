import csv
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import ValidationError as PydanticValidationError

from src.data_models.ec_models import Product, Category
from src.neo4j_utils.connector import Neo4jConnector
from neo4j.exceptions import Neo4jError, ServiceUnavailable # For specific error handling if needed

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Safely parse a datetime string from common formats, returning None if empty or invalid."""
    if not value:
        return None
    # Attempt common datetime formats
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

def _parse_float(value: Optional[str]) -> Optional[float]:
    """Safely parse a float string, returning None if empty, invalid, or non-numeric."""
    if value is None or value.strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        logging.warning(f"Could not parse float string: '{value}'")
        return None

def process_products_csv(csv_file_path: str, connector: Optional[Neo4jConnector] = None) -> Dict[str, Any]:
    """
    Reads product data from a CSV file, validates it using Pydantic models,
    logs successes or errors, and optionally loads data into Neo4j.

    Args:
        csv_file_path (str): The path to the CSV file.
        connector (Neo4jConnector, optional): An instance of Neo4jConnector for DB operations.
                                              If None, Neo4j loading steps are skipped.

    Returns:
        Dict[str, Any]: A summary of the processing.
    """
    processed_rows = 0
    validated_products_count = 0
    validated_categories_count = 0 # Counts unique category instances created from CSV rows
    loaded_products_count = 0
    loaded_categories_count = 0 # Counts MERGE operations for categories
    relationships_created_count = 0
    validation_errors = 0
    type_conversion_errors = 0
    neo4j_errors = 0

    # Store Pydantic instances if we need them later (e.g. for relationship creation)
    # For this script, we process and load row by row.
    # For more complex scenarios (e.g. bulk loading), storing them might be useful.

    logging.info(f"Starting CSV processing for file: {csv_file_path}. Neo4j loading: {'Enabled' if connector else 'Disabled'}")

    try:
        with open(csv_file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row_num, row in enumerate(reader, 1):
                processed_rows += 1
                product_id_str = row.get('ProductID', f'ROW_{row_num}')
                log_prefix = f"Row {row_num} (ProductID: {product_id_str}):"

                try:
                    # Prepare data for Product model
                    product_data_raw = {
                        'ProductID': row.get('ProductID'),
                        'ProductName': row.get('ProductName'),
                        'Description': row.get('ProductDescription'),
                        'SKU': row.get('SKU'),
                        'CategoryID': row.get('CategoryID'),
                        'SupplierID': row.get('SupplierID'),
                        'Price': row.get('Price'),
                        'StockQuantity': row.get('StockQuantity'),
                        'ImagePath': row.get('ImagePath'),
                        'DateAdded': row.get('DateAdded')
                    }

                    product_data_typed = {
                        'ProductID': _parse_int(product_data_raw['ProductID']),
                        'ProductName': product_data_raw['ProductName'],
                        'Description': product_data_raw['Description'],
                        'SKU': product_data_raw['SKU'],
                        'CategoryID': _parse_int(product_data_raw['CategoryID']),
                        'SupplierID': _parse_int(product_data_raw['SupplierID']),
                        'Price': _parse_float(product_data_raw['Price']),
                        'StockQuantity': _parse_int(product_data_raw['StockQuantity']),
                        'ImagePath': product_data_raw['ImagePath'],
                        'DateAdded': _parse_datetime(product_data_raw['DateAdded'])
                    }

                    product_instance = Product(**product_data_typed)
                    validated_products_count += 1
                    logging.info(f"{log_prefix} Product validated: {product_instance.ProductID} - {product_instance.ProductName}")

                    category_instance = None
                    if product_instance.CategoryID: # Only process category if Product has a CategoryID
                        category_data_typed = {
                            'CategoryID': product_instance.CategoryID, # Use already validated CategoryID
                            'CategoryName': row.get('CategoryName'), # Get CategoryName from row
                            'Description': None # Not in CSV
                        }
                        category_instance = Category(**category_data_typed)
                        validated_categories_count +=1
                        logging.info(f"{log_prefix} Category validated: {category_instance.CategoryID} - {category_instance.CategoryName}")

                    # Load into Neo4j if connector is provided
                    if connector:
                        # 1. Merge Category Node
                        if category_instance:
                            cat_props = category_instance.model_dump(exclude_none=True)
                            # Ensure categoryID is in props for the SET clause if MERGE is on categoryID only
                            cat_props['categoryID'] = category_instance.CategoryID

                            query_cat = "MERGE (c:Category {categoryID: $categoryID}) SET c = $props RETURN c.categoryID"
                            params_cat = {"categoryID": category_instance.CategoryID, "props": cat_props}
                            try:
                                result_cat = connector.execute_query(query_cat, params_cat, tx_type='write')
                                if result_cat:
                                    logging.info(f"{log_prefix} Category node MERGED: {result_cat[0]['c.categoryID']}")
                                    loaded_categories_count +=1
                                else: # Should not happen if query is correct and returns ID
                                    logging.warning(f"{log_prefix} Category MERGE did not return ID for {category_instance.CategoryID}")
                            except Neo4jError as e:
                                logging.error(f"{log_prefix} Neo4j error merging Category {category_instance.CategoryID}: {e}")
                                neo4j_errors += 1
                                continue # Skip product and relationship if category fails

                        # 2. Merge Product Node
                        prod_props = product_instance.model_dump(exclude_none=True)
                        # Ensure productID is in props for the SET clause
                        prod_props['productID'] = product_instance.ProductID

                        query_prod = "MERGE (p:Product {productID: $productID}) SET p = $props RETURN p.productID"
                        params_prod = {"productID": product_instance.ProductID, "props": prod_props}
                        try:
                            result_prod = connector.execute_query(query_prod, params_prod, tx_type='write')
                            if result_prod:
                                logging.info(f"{log_prefix} Product node MERGED: {result_prod[0]['p.productID']}")
                                loaded_products_count += 1
                            else:
                                logging.warning(f"{log_prefix} Product MERGE did not return ID for {product_instance.ProductID}")

                            # 3. Merge BELONGS_TO Relationship (only if category and product were successful)
                            if category_instance and result_prod : # Check if product merge was successful
                                query_rel = (
                                    "MATCH (p:Product {productID: $productID}) "
                                    "MATCH (c:Category {categoryID: $categoryID}) "
                                    "MERGE (p)-[r:BELONGS_TO]->(c) "
                                    "RETURN type(r) AS rel_type"
                                )
                                params_rel = {
                                    "productID": product_instance.ProductID,
                                    "categoryID": category_instance.CategoryID
                                }
                                result_rel = connector.execute_query(query_rel, params_rel, tx_type='write')
                                if result_rel:
                                    logging.info(f"{log_prefix} Relationship Product {product_instance.ProductID} -BELONGS_TO-> Category {category_instance.CategoryID} MERGED.")
                                    relationships_created_count +=1
                                else:
                                    logging.warning(f"{log_prefix} BELONGS_TO MERGE did not return for P:{product_instance.ProductID} C:{category_instance.CategoryID}")

                        except Neo4jError as e:
                            logging.error(f"{log_prefix} Neo4j error merging Product {product_instance.ProductID} or its relationship: {e}")
                            neo4j_errors += 1

                except PydanticValidationError as e:
                    logging.error(f"{log_prefix} Validation error: {e.errors()} for data {dict(row)}")
                    validation_errors += 1
                except Exception as e:
                    logging.error(f"{log_prefix} Unexpected error processing row: {e} for data {dict(row)}", exc_info=True)
                    type_conversion_errors +=1



    except FileNotFoundError:
        logging.error(f"Error: CSV file not found at {csv_file_path}")
        # Initialize all count fields for the summary if file not found
        return {
            "status": "Failed", "message": f"File not found: {csv_file_path}",
            "processed_rows": 0, "validated_products_count": 0, "validated_categories_count": 0,
            "loaded_products_count": 0, "loaded_categories_count": 0, "relationships_created_count": 0,
            "validation_errors": 0, "type_conversion_errors": 0, "neo4j_errors": 0
        }
    except Exception as e:
        logging.error(f"An unexpected error occurred during CSV file processing: {e}", exc_info=True)
        # Populate all fields in summary, even if some are zero
        return {
            "status": "Failed", "message": f"Unexpected error: {e}",
            "processed_rows": processed_rows, "validated_products_count": validated_products_count,
            "validated_categories_count": validated_categories_count,
            "loaded_products_count": loaded_products_count, "loaded_categories_count": loaded_categories_count,
            "relationships_created_count": relationships_created_count,
            "validation_errors": validation_errors, "type_conversion_errors": type_conversion_errors,
            "neo4j_errors": neo4j_errors
        }

    summary = {
        "status": "Completed",
        "csv_file_path": csv_file_path,
        "processed_rows": processed_rows,
        "validated_products_count": validated_products_count,
        "validated_categories_count": validated_categories_count,
        "loaded_products_count": loaded_products_count,
        "loaded_categories_count": loaded_categories_count,
        "relationships_created_count": relationships_created_count,
        "validation_errors": validation_errors,
        "type_conversion_errors": type_conversion_errors,
        "neo4j_errors": neo4j_errors
    }
    logging.info(f"CSV processing finished. Summary: {summary}")
    return summary

if __name__ == "__main__":
    csv_path = "data/sample_products.csv"

    import os
    if not os.path.exists(csv_path):
        logging.error(f"Sample CSV file '{csv_path}' not found. Ensure you are in the project root directory or the path is correct.")
        logging.error("You may need to run the script that generates 'data/sample_products.csv' first if applicable.")
    else:
        # Attempt to connect to Neo4j
        connector_instance = None
        try:
            # Using 'with' ensures connector.close() is called
            with Neo4jConnector() as connector_instance:
                processing_summary = process_products_csv(csv_path, connector_instance)
        except ServiceUnavailable:
            logging.error("Neo4j service is unavailable. Running CSV validation without Neo4j loading.")
            # Fallback to processing without Neo4j if connection fails at startup
            processing_summary = process_products_csv(csv_path, None) # Pass None for connector
        except Exception as e: # Catch other potential errors from Neo4jConnector init
            logging.error(f"Failed to initialize Neo4jConnector: {e}. Running CSV validation without Neo4j loading.")
            processing_summary = process_products_csv(csv_path, None)

        print("\n--- Processing Summary ---")
        for key, value in processing_summary.items():
            print(f"{key.replace('_', ' ').title()}: {value}")
