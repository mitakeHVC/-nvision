import csv
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Set
from pydantic import BaseModel, PositiveInt, PositiveFloat, Field, ValidationError as PydanticValidationError

from src.data_models.ec_models import Order # Using the existing Order Pydantic model
from src.neo4j_utils.connector import Neo4jConnector
from neo4j.exceptions import Neo4jError, ServiceUnavailable

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Helper functions for parsing (can be moved to a shared utility module later)
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

# Internal Pydantic model for validating OrderItem attributes from CSV before creating relationship
class CSVOrderItemData(BaseModel):
    OrderItemID: PositiveInt
    ProductID: PositiveInt
    Quantity: PositiveInt # Assuming quantity must be positive
    UnitPrice: PositiveFloat # Assuming unit price must be positive (or NonNegativeFloat if 0 is allowed)

    # Calculated field, not directly from CSV for this model
    # TotalItemPrice: Optional[PositiveFloat] = None


def process_orders_csv(csv_file_path: str, connector: Optional[Neo4jConnector] = None) -> Dict[str, Any]:
    """
    Reads order and order item data from a CSV, validates it, and loads into Neo4j.
    """
    processed_rows = 0
    validated_orders_count = 0 # Unique orders validated
    validated_items_count = 0  # Valid order items from rows

    loaded_orders_count = 0    # Unique orders loaded to Neo4j
    loaded_items_relationships_count = 0 # CONTAINS relationships created
    placed_relationships_count = 0 # PLACED relationships created

    validation_errors = 0
    type_conversion_errors = 0
    neo4j_errors = 0

    processed_order_ids: Set[int] = set() # To track if Order node and PLACED rel were made

    logging.info(f"Starting CSV processing for order data: {csv_file_path}. Neo4j loading: {'Enabled' if connector else 'Disabled'}")

    try:
        with open(csv_file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row_num, row in enumerate(reader, 1):
                processed_rows += 1
                order_id_str = row.get('OrderID', f'ROW_{row_num}')
                item_id_str = row.get('OrderItemID', f'ITEM_ROW_{row_num}')
                log_prefix = f"Row {row_num} (OrderID: {order_id_str}, ItemID: {item_id_str}):"

                order_instance = None
                order_data_valid = False

                try:
                    # --- Order Data Validation (once per OrderID) ---
                    current_order_id = _parse_int(row.get('OrderID'))
                    if not current_order_id: # Essential for processing
                        logging.error(f"{log_prefix} Missing or invalid OrderID. Skipping row.")
                        validation_errors +=1
                        continue

                    if current_order_id not in processed_order_ids:
                        order_data_typed = {
                            'OrderID': current_order_id,
                            'CustomerID': _parse_int(row.get('CustomerID')),
                            'OrderDate': _parse_datetime(row.get('OrderDate')),
                            'OrderStatus': row.get('OrderStatus'),
                            'TotalAmount': _parse_float(row.get('OrderTotalAmount')), # CSV header
                            'ShippingAddress': row.get('ShippingAddress'),
                            'BillingAddress': row.get('BillingAddress')
                        }
                        order_instance = Order(**order_data_typed)
                        validated_orders_count += 1
                        order_data_valid = True # Mark as validated for this OrderID iteration
                        logging.info(f"{log_prefix} Order Pydantic-validated: {order_instance.OrderID}")

                        if connector:
                            order_props = order_instance.model_dump(exclude_none=True)
                            order_props['orderID'] = order_instance.OrderID # Ensure merge key is in props

                            # Query 1: Merge Order node
                            # Query 2: Match Customer, Merge PLACED relationship
                            # Combining into one query for atomicity if possible, or run sequentially.
                            # For simplicity and clarity, running sequentially for now.

                            query_order = "MERGE (o:Order {orderID: $orderID}) SET o = $props RETURN o.orderID"
                            params_order = {"orderID": order_instance.OrderID, "props": order_props}

                            query_placed_rel = (
                                "MATCH (o:Order {orderID: $orderID}) "
                                "MATCH (c:ECCustomer {customerID: $customerID}) "
                                "MERGE (c)-[r:PLACED]->(o) "
                                "ON CREATE SET r.date = $orderDate RETURN type(r) as rel_type"
                            )
                            params_placed_rel = {
                                "orderID": order_instance.OrderID,
                                "customerID": order_instance.CustomerID,
                                "orderDate": order_instance.OrderDate # Use validated datetime
                            }

                            try:
                                result_order = connector.execute_query(query_order, params_order, tx_type='write')
                                if result_order and result_order[0]['o.orderID'] == order_instance.OrderID:
                                    logging.info(f"{log_prefix} Order node MERGED: {order_instance.OrderID}")
                                    loaded_orders_count +=1

                                    # Only attempt PLACED if CustomerID exists
                                    if order_instance.CustomerID:
                                        result_placed = connector.execute_query(query_placed_rel, params_placed_rel, tx_type='write')
                                        if result_placed:
                                            logging.info(f"{log_prefix} PLACED relationship MERGED for Order {order_instance.OrderID} to Customer {order_instance.CustomerID}")
                                            placed_relationships_count +=1
                                        else:
                                            logging.warning(f"{log_prefix} PLACED relationship MERGE failed or no return for Order {order_instance.OrderID}")
                                            neo4j_errors +=1 # Or specific counter
                                    else:
                                        logging.warning(f"{log_prefix} Order {order_instance.OrderID} has no CustomerID, skipping PLACED relationship.")
                                    processed_order_ids.add(current_order_id) # Mark OrderID as processed
                                else:
                                    logging.error(f"{log_prefix} Order MERGE failed for {order_instance.OrderID}")
                                    neo4j_errors += 1
                                    order_data_valid = False # Don't process items if order failed to load
                            except Neo4jError as e:
                                logging.error(f"{log_prefix} Neo4j error processing Order {current_order_id} or PLACED rel: {e}")
                                neo4j_errors += 1
                                order_data_valid = False # Don't process items if order failed to load
                            except Exception as e:
                                logging.error(f"{log_prefix} Unexpected error during Neo4j Order ops for {current_order_id}: {e}", exc_info=True)
                                neo4j_errors += 1
                                order_data_valid = False
                    else: # No connector, but order Pydantic validation was successful
                        processed_order_ids.add(current_order_id) # Mark as Pydantic-validated for item processing

                    # --- OrderItem Data Validation and Relationship Loading ---
                    # This part runs for every row, assuming its Order part was processed or already existed.
                    # If order_data_valid is False (due to Neo4j error for a new order), items for it are skipped.
                    # If current_order_id in processed_order_ids (and was previously valid), items can be processed.

                    if current_order_id not in processed_order_ids and not order_data_valid:
                        # This case means it's a new OrderID in the CSV, but its Order data failed Pydantic or Neo4j.
                        # Items for this order should be skipped.
                        logging.warning(f"{log_prefix} Skipping item because its new Order data failed to process/load.")
                        continue # to next row

                    # At this point, the Order (current_order_id) is considered Pydantic-valid (if new)
                    # or was already processed. If loading to Neo4j and it failed, order_data_valid would be false.
                    # We only proceed to load items if the order is conceptually sound (Pydantic-valid)
                    # AND if using Neo4j, its node creation was successful for new orders.

                    item_data_typed = {
                        'OrderItemID': _parse_int(row.get('OrderItemID')),
                        'ProductID': _parse_int(row.get('ProductID')),
                        'Quantity': _parse_int(row.get('Quantity')),
                        'UnitPrice': _parse_float(row.get('UnitPrice'))
                    }
                    item_instance = CSVOrderItemData(**item_data_typed) # Use internal Pydantic model for item attributes
                    validated_items_count += 1
                    logging.info(f"{log_prefix} OrderItem Pydantic-validated: {item_instance.OrderItemID}")

                    if connector and (current_order_id in processed_order_ids or order_data_valid):
                        # order_data_valid implies the order MERGE was successful for a new order in this iteration.
                        # current_order_id in processed_order_ids implies the order was processed in a *previous* iteration.
                        total_item_price = (item_instance.Quantity or 0) * (item_instance.UnitPrice or 0.0)

                        query_contains_rel = (
                            "MATCH (o:Order {orderID: $orderID}) "
                            "MATCH (p:Product {productID: $productID}) "
                            "MERGE (o)-[r:CONTAINS {orderItemID: $orderItemID}]->(p) "
                            "SET r.quantity = $quantity, r.unitPrice = $unitPrice, r.totalItemPrice = $totalItemPrice "
                            "RETURN type(r) as rel_type"
                        )
                        params_contains_rel = {
                            "orderID": current_order_id,
                            "productID": item_instance.ProductID,
                            "orderItemID": item_instance.OrderItemID,
                            "quantity": item_instance.Quantity,
                            "unitPrice": item_instance.UnitPrice,
                            "totalItemPrice": total_item_price
                        }
                        try:
                            result_contains = connector.execute_query(query_contains_rel, params_contains_rel, tx_type='write')
                            if result_contains:
                                logging.info(f"{log_prefix} CONTAINS relationship MERGED for OrderItem {item_instance.OrderItemID}")
                                loaded_items_relationships_count += 1
                            else:
                                logging.warning(f"{log_prefix} CONTAINS relationship MERGE failed or no return for OrderItem {item_instance.OrderItemID}")
                                neo4j_errors +=1
                        except Neo4jError as e:
                            logging.error(f"{log_prefix} Neo4j error processing CONTAINS rel for OrderItem {item_instance.OrderItemID}: {e}")
                            neo4j_errors += 1
                        except Exception as e:
                            logging.error(f"{log_prefix} Unexpected error during Neo4j CONTAINS ops for {item_instance.OrderItemID}: {e}", exc_info=True)
                            neo4j_errors += 1

                except PydanticValidationError as e:
                    logging.error(f"{log_prefix} Validation error: {e.errors()} for data {dict(row)}")
                    validation_errors += 1
                except Exception as e:
                    logging.error(f"{log_prefix} Unexpected error processing row: {e} for data {dict(row)}", exc_info=True)
                    type_conversion_errors +=1

    except FileNotFoundError:
        logging.error(f"Error: CSV file not found at {csv_file_path}")
        return {"status": "Failed", "message": f"File not found: {csv_file_path}", "processed_rows": 0, "validated_orders_count":0, "validated_items_count":0, "loaded_orders_count":0, "loaded_items_relationships_count":0, "placed_relationships_count":0, "validation_errors":0, "type_conversion_errors":0, "neo4j_errors":0}
    except Exception as e:
        logging.error(f"An unexpected error occurred during CSV file processing: {e}", exc_info=True)
        return {"status": "Failed", "message": f"Unexpected error: {e}", "processed_rows": processed_rows, "validated_orders_count":validated_orders_count, "validated_items_count":validated_items_count, "loaded_orders_count":loaded_orders_count, "loaded_items_relationships_count":loaded_items_relationships_count, "placed_relationships_count":placed_relationships_count, "validation_errors":validation_errors, "type_conversion_errors":type_conversion_errors, "neo4j_errors":neo4j_errors}

    summary = {
        "status": "Completed",
        "csv_file_path": csv_file_path,
        "processed_rows": processed_rows,
        "validated_orders_count": validated_orders_count,
        "validated_items_count": validated_items_count,
        "loaded_orders_count": loaded_orders_count,
        "placed_relationships_count": placed_relationships_count,
        "loaded_items_relationships_count": loaded_items_relationships_count,
        "validation_errors": validation_errors,
        "type_conversion_errors": type_conversion_errors,
        "neo4j_errors": neo4j_errors
    }
    logging.info(f"CSV order processing finished. Summary: {summary}")
    return summary

if __name__ == "__main__":
    csv_path = "data/sample_orders.csv"

    import os
    if not os.path.exists(csv_path):
        logging.error(f"Sample CSV file '{csv_path}' not found. Ensure you are in the project root directory or the path is correct.")
    else:
        processing_summary = None
        try:
            # Using 'with' ensures connector.close() is called if initialized here
            with Neo4jConnector() as connector_instance:
                processing_summary = process_orders_csv(csv_path, connector_instance)
        except ServiceUnavailable:
            logging.error("Neo4j service is unavailable. Running CSV validation for orders without Neo4j loading.")
            processing_summary = process_orders_csv(csv_path, None) # Pass None for connector
        except Exception as e:
            logging.error(f"Failed to initialize Neo4jConnector or other critical error: {e}. Running CSV validation for orders without Neo4j loading.")
            processing_summary = process_orders_csv(csv_path, None)

        if processing_summary:
            print("\n--- Order Processing Summary ---")
            for key, value in processing_summary.items():
                print(f"{key.replace('_', ' ').title()}: {value}")
        else:
            print("Order processing could not be completed due to an early critical error.")
