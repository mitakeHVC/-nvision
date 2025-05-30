# Project Title: Data Schema and Transformation Implementation

This project aims to implement the data schemas, relationships, and transformation logic outlined in the `data_schema_and_transformation_proposal.md` document.

## Current Status

- **E-commerce (EC) Data Models:** Python Pydantic models for the EC system entities (Customers, Products, Categories, Orders, OrderItems, Suppliers, CustomerReviews) have been created and are located in `src/data_models/ec_models.py`. These models include basic data validation.
- **Shared/Support System Data Models:** Pydantic models for Chat (`ChatSession`, `ChatMessage`) are in `src/data_models/shared_models.py`.
- **CRM System Data Models:** Pydantic models for CRM entities (`Contact`, `Company`, `Interaction`, `Deal`, `User`) are in `src/data_models/crm_models.py`.
- **Neo4j Schemas:** Conceptual Cypher schemas (nodes, relationships, constraints, indexes) for EC, CRM, and Shared systems are defined in `src/neo4j_setup/`.
- **Neo4j Connector:** A utility module `src/neo4j_utils/connector.py` for managing Neo4j connections is available.
- **Sample Data:** Sample product data is available in `data/sample_products.csv`.
- **Product Ingestion Script:** A script `src/ingestion/ingest_products.py` can read, validate, and load product data from CSV into Neo4j.
- **Unit & Integration Tests:** Tests for data models and the product ingestion script are in the `tests/` directory.
- **Design Documents:**
    - `data_schema_and_transformation_proposal.md`
    - `docs/data_ingestion_framework.md`

## Data Ingestion

This section describes scripts and processes for ingesting data into the target systems (Neo4j, ChromaDB).

### Product Ingestion Script (`src/ingestion/ingest_products.py`)

**1. Purpose:**
This script is responsible for ingesting product data from a sample CSV file (`data/sample_products.csv`). It performs the following actions:
- Reads product and associated category information from each row in the CSV.
- Validates the data against the `Product` and `Category` Pydantic models (defined in `src/data_models/ec_models.py`).
- Logs validation successes and errors.
- If validation is successful and a Neo4j connection is available, it loads the data into a Neo4j database by:
    - Creating or merging `Product` nodes.
    - Creating or merging `Category` nodes.
    - Establishing `BELONGS_TO` relationships between `Product` and `Category` nodes.

**2. Dependencies:**
The script requires the following Python libraries:
- `neo4j` (official Neo4j Python driver)
- `pydantic` (for data validation)

These dependencies should ideally be listed in a `requirements.txt` file for the project.

**3. Configuration:**
Neo4j database connection parameters are configured via environment variables. If these variables are not set, the script uses default values suitable for a local Neo4j instance.
- `NEO4J_URI`: The Bolt URI for the Neo4j database.
    - Default: `bolt://localhost:7687`
- `NEO4J_USERNAME`: The username for Neo4j authentication.
    - Default: `neo4j`
- `NEO4J_PASSWORD`: The password for Neo4j authentication.
    - Default: `password`

**4. Running the Script:**
To run the script from the root directory of this repository, use the following command:
```bash
python -m src.ingestion.ingest_products
```
When executed, the script will:
- Attempt to connect to the Neo4j database using the configured parameters.
- Read product data from `data/sample_products.csv`.
- Validate each product and its associated category.
- Log validation results.
- If Neo4j is connected, load valid data into the database.
- Print a summary of processing, including counts of processed rows, validated items, loaded items, and any errors encountered.
- If Neo4j is unavailable, the script will still perform CSV reading and validation but will skip the data loading steps.

**5. Input Data:**
The script expects the input data in CSV format. A sample input file is provided at:
`data/sample_products.csv`

The CSV file should include headers such as `ProductID`, `ProductName`, `ProductDescription`, `SKU`, `CategoryID`, `CategoryName`, `SupplierID`, `Price`, `StockQuantity`, `ImagePath`, and `DateAdded`.

## Next Steps

The project will proceed with:
- Development of data ingestion scripts for CRM and Shared/Support systems.
- Implementation of ChromaDB vector embedding strategies and data ingestion logic.
- Enhancements to error handling, monitoring, and orchestration of ingestion pipelines.
