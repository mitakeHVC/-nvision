# Project Title: Data Schema and Transformation Implementation

## Overview

This project aims to implement the data schemas, relationships, and transformation logic outlined in the `data_schema_and_transformation_proposal.md` document for E-commerce, CRM, and Shared/Support systems, primarily targeting Neo4j and ChromaDB.

## Project Status: Phase 1 - E-commerce Data Completed

This initial phase focused on establishing the foundational elements for E-commerce data.

**Key Accomplishments from Phase 1:**
*   **Data Models (`src/data_models/ec_models.py`):**
    *   Pydantic models created for `Customer`, `Product`, `Category`, `Order`, `OrderItem` (as relationship properties), `Supplier`, and `CustomerReview`.
    *   Includes data validation rules (e.g., `PositiveInt`, `EmailStr`, field constraints).
*   **Neo4j Schema (`src/neo4j_setup/ec_schema.cypher`):**
    *   Conceptual Cypher schema defining node labels (`ECCustomer`, `Product`, `Category`, `Order`, `Supplier`, `Review`), their properties, relationships (`PLACED`, `CONTAINS`, `BELONGS_TO`, `SUPPLIED_BY`, `WROTE_REVIEW`, `HAS_REVIEW`), and actual statements for unique constraints and indexes.
*   **Neo4j Connector (`src/neo4j_utils/connector.py`):**
    *   A reusable Python module using the official `neo4j` driver to manage database connections and execute Cypher queries, configurable via environment variables.
*   **Sample Data (`data/` directory):**
    *   `sample_products.csv`
    *   `sample_customers.csv`
    *   `sample_orders.csv` (includes order item data)
    *   `sample_suppliers.csv`
    *   `sample_reviews.csv`
*   **Ingestion Scripts (`src/ingestion/` directory):**
    *   Python scripts developed for each E-commerce entity to read data from its respective CSV file, validate it using Pydantic models, and load it into Neo4j (including nodes and relationships).
        *   `ingest_products.py`
        *   `ingest_customers.py`
        *   `ingest_orders.py`
        *   `ingest_suppliers.py`
        *   `ingest_reviews.py`
*   **Testing (`tests/` directory):**
    *   Comprehensive unit and integration tests (`pytest`) for all Pydantic data models and each of the E-commerce ingestion scripts, ensuring data validation logic and Neo4j interactions function correctly.
*   **Design Documents:**
    *   `data_schema_and_transformation_proposal.md`: The core proposal document.
    *   `docs/data_ingestion_framework.md`: Conceptual design for the overall data ingestion framework.

**Shared & CRM Foundational Models (Also part of initial setup):**
* **Shared/Support System Data Models (`src/data_models/shared_models.py`):** Pydantic models for `ChatSession`, `ChatMessage`.
* **CRM System Data Models (`src/data_models/crm_models.py`):** Pydantic models for `Contact`, `Company`, `Interaction`, `Deal`, `User`.
* **Neo4j Schemas (`src/neo4j_setup/crm_shared_schema.cypher`):** Conceptual Cypher schema for CRM & Shared system nodes, relationships, constraints, and indexes.

## Key Features
*   **Pydantic Data Models:** For data validation and structure.
*   **Neo4j Graph Schema:** Defining nodes, relationships, constraints, and indexes.
*   **Data Ingestion Scripts:** Python scripts for populating Neo4j from CSV files.
*   **Testing:** Unit and integration tests for data models and ingestion processes.

## Modules/Components

*   **`src/data_models/`**: Contains Pydantic models for:
    *   `ec_models.py`: E-commerce entities (Customer, Product, Order, etc.).
    *   `crm_models.py`: CRM entities (Contact, Company, Deal, etc.).
    *   `shared_models.py`: Shared/Support entities (ChatSession, ChatMessage, etc.).
*   **`src/neo4j_setup/`**:
    *   `ec_schema.cypher`: Cypher statements for E-commerce schema.
    *   `crm_shared_schema.cypher`: Cypher statements for CRM and Shared systems schema.
*   **`src/neo4j_utils/`**:
    *   `connector.py`: Module for managing Neo4j database connections.
*   **`src/ingestion/`**: Python scripts for data ingestion (details below).
*   **`data/`**: Sample CSV data files for E-commerce entities.
*   **`tests/`**: Pytest unit and integration tests.
*   **`docs/`**: Design and proposal documents.

## Getting Started

### Prerequisites
*   Python 3.9+
*   Neo4j Database ( AuraDB, local instance, or Docker)
*   ChromaDB (for vector embeddings - future phase)
*   Poetry (for dependency management)

### Installation
1.  Clone the repository:
    ```bash
    git clone <repository-url>
    cd <repository-name>
    ```
2.  Install dependencies using Poetry:
    ```bash
    poetry install
    ```

### Configuration
Set up the following environment variables for Neo4j connection (e.g., in a `.env` file):
*   `NEO4J_URI` (default: `bolt://localhost:7687`)
*   `NEO4J_USERNAME` (default: `neo4j`)
*   `NEO4J_PASSWORD` (default: `password`)

The Neo4j connector module (`src/neo4j_utils/connector.py`) uses these variables.

## Running E-commerce Data Ingestion Scripts

The following scripts ingest data for the E-commerce system. Ensure Neo4j is running and accessible.

### Product Ingestion Script (`src/ingestion/ingest_products.py`)
*   **Purpose:** Ingests product and category data from `data/sample_products.csv`. Creates/merges `Product` and `Category` nodes and `BELONGS_TO` relationships.
*   **Run:** `python -m src.ingestion.ingest_products`
*   **Input:** `data/sample_products.csv`

### Customer Ingestion Script (`src/ingestion/ingest_customers.py`)
*   **Purpose:** Ingests customer data from `data/sample_customers.csv`. Creates/merges `ECCustomer` nodes.
*   **Run:** `python -m src.ingestion.ingest_customers`
*   **Input:** `data/sample_customers.csv`

### Order Ingestion Script (`src/ingestion/ingest_orders.py`)
*   **Purpose:** Ingests order and order item data from `data/sample_orders.csv`. Creates/merges `Order` nodes, `PLACED` relationships from `ECCustomer` to `Order`, and `CONTAINS` relationships from `Order` to `Product` (with item properties like quantity and unit price).
*   **Run:** `python -m src.ingestion.ingest_orders`
*   **Input:** `data/sample_orders.csv`

### Supplier Ingestion Script (`src/ingestion/ingest_suppliers.py`)
*   **Purpose:** Ingests supplier data from `data/sample_suppliers.csv`. Creates/merges `Supplier` nodes and `SUPPLIED_BY` relationships between Products and Suppliers (Note: `SUPPLIED_BY` relationship logic might need to be added or clarified if not already present in the script, based on `ec_schema.cypher`).
*   **Run:** `python -m src.ingestion.ingest_suppliers`
*   **Input:** `data/sample_suppliers.csv`

### Customer Review Ingestion Script (`src/ingestion/ingest_reviews.py`)
*   **Purpose:** Ingests customer review data from `data/sample_reviews.csv`. Creates/merges `Review` nodes, `WROTE_REVIEW` relationships from `ECCustomer` to `Review`, and `HAS_REVIEW` relationships from `Product` to `Review`.
*   **Run:** `python -m src.ingestion.ingest_reviews`
*   **Input:** `data/sample_reviews.csv`

## Future Work / Next Steps: Phase 2 - CRM & Shared Systems Data Ingestion

The project will now proceed with:
*   **Development of data ingestion scripts for CRM system entities:**
    *   `Contact`, `Company`, `Interaction`, `Deal`, `User`.
    *   This includes creating/merging nodes and establishing defined relationships within the CRM context (e.g., `WORKS_FOR`, `PARTICIPATED_IN`).
*   **Development of data ingestion scripts for Shared/Support system entities (Chat):**
    *   `ChatSession`, `ChatMessage`.
    *   Includes node creation and relationships like `HAS_MESSAGE`, `PARTICIPATED_IN_CHAT`.
*   **Cross-System Relationship Implementation:** Focus on creating relationships that link entities across different domains (e.g., `EC_CUSTOMER --IS_SAME_AS--> CRM_CONTACT`).
*   **ChromaDB Integration:** Begin implementation of vector embedding strategies (as outlined in `data_schema_and_transformation_proposal.md`) and data ingestion logic for ChromaDB using relevant text fields from all systems.
*   **Testing:** Continue to develop unit and integration tests for all new ingestion scripts and components.
*   **Refinement:** Enhance error handling, monitoring, and explore orchestration options for the ingestion pipelines as complexity grows.

## Contributing
Contributions are welcome! Please refer to the `CONTRIBUTING.md` file (if available) or follow standard fork-and-pull-request procedures. Ensure your code adheres to existing style and includes tests.

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.
