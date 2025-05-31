# Project Title: Data Schema and Transformation Implementation

This project aims to implement the data schemas, relationships, and transformation logic outlined in the `data_schema_and_transformation_proposal.md` document for E-commerce, CRM, and Shared/Support systems, primarily targeting Neo4j and ChromaDB.

## Phase 1: E-commerce Data - Completed

This phase focused on establishing the foundational elements for E-commerce data.

**Key Accomplishments:**
-   **Data Models (`src/data_models/ec_models.py`):**
    -   Pydantic models created for `Customer`, `Product`, `Category`, `Order`, `OrderItem` (as relationship properties), `Supplier`, and `CustomerReview`.
    -   Includes data validation rules (e.g., `PositiveInt`, `EmailStr`, field constraints).
-   **Neo4j Schema (`src/neo4j_setup/ec_schema.cypher`):**
    -   Conceptual Cypher schema defining node labels (`ECCustomer`, `Product`, `Category`, `Order`, `Supplier`, `Review`), their properties, relationships (`PLACED`, `CONTAINS`, `BELONGS_TO`, `SUPPLIED_BY`, `WROTE_REVIEW`, `HAS_REVIEW`), and actual statements for unique constraints and indexes.
-   **Neo4j Connector (`src/neo4j_utils/connector.py`):**
    -   A reusable Python module using the official `neo4j` driver to manage database connections and execute Cypher queries, configurable via environment variables.
-   **Sample Data (`data/` directory):**
    -   `sample_products.csv`
    -   `sample_customers.csv`
    -   `sample_orders.csv` (includes order item data)
    -   `sample_suppliers.csv`
    -   `sample_reviews.csv`
-   **Ingestion Scripts (`src/ingestion/` directory):**
    -   Python scripts developed for each E-commerce entity to read data from its respective CSV file, validate it using Pydantic models, and load it into Neo4j (including nodes and relationships).
        -   `ingest_products.py`
        -   `ingest_customers.py`
        -   `ingest_orders.py`
        -   `ingest_suppliers.py`
        -   `ingest_reviews.py`
-   **Testing (`tests/` directory):**
    -   Comprehensive unit and integration tests (`pytest`) for all Pydantic data models and each of the E-commerce ingestion scripts, ensuring data validation logic and Neo4j interactions function correctly.
-   **Design Documents:**
    -   `data_schema_and_transformation_proposal.md`: The core proposal document.
    -   `docs/data_ingestion_framework.md`: Conceptual design for the overall data ingestion framework.

**Shared & CRM Foundational Models (Also part of initial setup):**
- **Shared/Support System Data Models (`src/data_models/shared_models.py`):** Pydantic models for `ChatSession`, `ChatMessage`.
- **CRM System Data Models (`src/data_models/crm_models.py`):** Pydantic models for `Contact`, `Company`, `Interaction`, `Deal`, `User`.
- **Neo4j Schemas (`src/neo4j_setup/crm_shared_schema.cypher`):** Conceptual Cypher schema for CRM & Shared system nodes, relationships, constraints, and indexes.


## Data Ingestion Scripts

This section describes specific scripts for ingesting data into Neo4j. Common dependencies include `neo4j` and `pydantic`. Neo4j connection is configured via `NEO4J_URI`, `NEO4J_USERNAME`, and `NEO4J_PASSWORD` environment variables (defaults: `bolt://localhost:7687`, `neo4j`, `password`).

### Product Ingestion Script (`src/ingestion/ingest_products.py`)
-   **Purpose:** Ingests product and category data from `data/sample_products.csv`. Creates/merges `Product` and `Category` nodes and `BELONGS_TO` relationships.
-   **Run:** `python -m src.ingestion.ingest_products`
-   **Input:** `data/sample_products.csv`

### Customer Ingestion Script (`src/ingestion/ingest_customers.py`)
-   **Purpose:** Ingests customer data from `data/sample_customers.csv`. Creates/merges `ECCustomer` nodes.
-   **Run:** `python -m src.ingestion.ingest_customers`
-   **Input:** `data/sample_customers.csv`

### Order Ingestion Script (`src/ingestion/ingest_orders.py`)
-   **Purpose:** Ingests order and order item data from `data/sample_orders.csv`. Creates/merges `Order` nodes, `PLACED` relationships from `ECCustomer` to `Order`, and `CONTAINS` relationships from `Order` to `Product` (with item properties like quantity and unit price).
-   **Run:** `python -m src.ingestion.ingest_orders`
-   **Input:** `data/sample_orders.csv`

### Supplier Ingestion Script (`src/ingestion/ingest_suppliers.py`)
-   **Purpose:** Ingests supplier data from `data/sample_suppliers.csv`. Creates/merges `Supplier` nodes.
-   **Run:** `python -m src.ingestion.ingest_suppliers`
-   **Input:** `data/sample_suppliers.csv`

### Customer Review Ingestion Script (`src/ingestion/ingest_reviews.py`)
-   **Purpose:** Ingests customer review data from `data/sample_reviews.csv`. Creates/merges `Review` nodes, `WROTE_REVIEW` relationships from `ECCustomer` to `Review`, and `HAS_REVIEW` relationships from `Product` to `Review`.
-   **Run:** `python -m src.ingestion.ingest_reviews`
-   **Input:** `data/sample_reviews.csv`

## Next Steps: Phase 2 - CRM & Shared Systems Data Ingestion

The project will now proceed with:
-   **Development of data ingestion scripts for CRM system entities:**
    -   `Contact`, `Company`, `Interaction`, `Deal`, `User`.
    -   This includes creating/merging nodes and establishing defined relationships within the CRM context (e.g., `WORKS_FOR`, `PARTICIPATED_IN`).
-   **Development of data ingestion scripts for Shared/Support system entities (Chat):**
    -   `ChatSession`, `ChatMessage`.
    -   Includes node creation and relationships like `HAS_MESSAGE`, `PARTICIPATED_IN_CHAT`.
-   **Cross-System Relationship Implementation:** Focus on creating relationships that link entities across different domains (e.g., `EC_CUSTOMER --IS_SAME_AS--> CRM_CONTACT`).
-   **ChromaDB Integration:** Begin implementation of vector embedding strategies (as outlined in `data_schema_and_transformation_proposal.md`) and data ingestion logic for ChromaDB using relevant text fields from all systems.
-   **Testing:** Continue to develop unit and integration tests for all new ingestion scripts and components.
-   **Refinement:** Enhance error handling, monitoring, and explore orchestration options for the ingestion pipelines as complexity grows.
