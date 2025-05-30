# Data Ingestion Framework - Conceptual Design

## 1. Introduction

### Purpose
The purpose of this Data Ingestion Framework is to provide a robust and scalable solution for extracting data from various source systems, transforming it according to predefined schemas and business rules, and loading it into target data stores, specifically Neo4j (for graph data) and ChromaDB (for vector embeddings). This framework will ensure data integrity, consistency, and timeliness, supporting the overall data analysis and application goals outlined in the `data_schema_and_transformation_proposal.md`.

### Overview of Systems
The framework will handle data from three primary systems:
*   **E-commerce (EC) System:** Customer transactions, product information, order histories, reviews, etc.
*   **Customer Relationship Management (CRM) System:** Customer interactions, company details, sales activities, user information.
*   **Shared/Support System (Chat):** Customer support chat sessions and messages.

These systems generate data that needs to be integrated and modeled to provide a unified view for analysis and operational use cases.

## 2. Data Sources

### Types of Data Sources
Data may originate from a variety of sources, including but not limited to:
*   **E-commerce System:**
    *   Relational Databases (e.g., PostgreSQL, MySQL)
    *   NoSQL Databases (e.g., MongoDB for product catalogs or user sessions)
    *   CSV/JSON exports from existing platforms
    *   Real-time event streams or message queues (e.g., Kafka, RabbitMQ for orders, stock updates)
    *   Third-party APIs (e.g., payment gateways, shipping providers)
*   **CRM System:**
    *   SaaS CRM platforms (e.g., Salesforce, HubSpot) via APIs
    *   Existing relational databases
    *   Data exports (CSV, Excel)
*   **Shared/Support System (Chat):**
    *   Chat platform APIs (e.g., Intercom, Zendesk Chat)
    *   Database backups or logs from chat services
    *   Webhook notifications for new chat events

### Data Formats
The framework must be capable of handling various data formats:
*   **Structured:** Database rows, CSV, TSV, Parquet
*   **Semi-structured:** JSON, XML
*   **Unstructured:** Plain text from chat logs or review texts (primarily for embedding).

## 3. Data Extraction Layer

### Methods for Extraction
*   **Database Connectors:** Standard libraries (e.g., psycopg2 for PostgreSQL, mysql.connector for MySQL) or ORM tools (e.g., SQLAlchemy) for SQL databases. Specific drivers for NoSQL databases.
*   **API Clients:** Custom or third-party Python libraries (e.g., `requests`, `aiohttp`) for REST/GraphQL APIs. SDKs provided by SaaS vendors.
*   **File Parsers:** Libraries like `pandas` for CSV/JSON, `xml.etree.ElementTree` for XML.
*   **Message Queue Consumers:** Libraries like `kafka-python` or `pika` (for RabbitMQ).

### Batch vs. Real-time
*   **Batch Extraction:** Suitable for full historical loads, nightly updates from systems that don't offer real-time feeds. Implemented via scheduled jobs.
*   **Real-time/Near Real-time Extraction:** For systems providing event streams, webhooks, or message queues. This allows for more immediate updates in Neo4j and ChromaDB. Requires an event-driven architecture component.

### Authentication and Authorization
*   Securely manage credentials (e.g., API keys, database passwords) using environment variables, secrets management tools (e.g., HashiCorp Vault, AWS Secrets Manager), or configuration files with appropriate permissions.
*   Implement OAuth 2.0 or other relevant authentication flows for APIs.
*   Ensure service accounts used for extraction have least-privilege access to data sources.

## 4. Data Transformation Layer

### Mapping to Pydantic Models
*   Source data fields will be mapped to the attributes of the Pydantic models defined in `src/data_models/ec_models.py`, `src/data_models/shared_models.py`, and `src/data_models/crm_models.py`.
*   This step involves selecting relevant fields, renaming them if necessary (Pydantic aliases help here), and performing initial data type conversions.

### Data Validation
*   Pydantic models will serve as the primary mechanism for data validation. Upon instantiation with source data, Pydantic will automatically enforce data types and validation rules (e.g., `PositiveInt`, `EmailStr`, value ranges).
*   Invalid records will be flagged, logged, and potentially routed to an error handling process or dead-letter queue.

### Data Cleaning and Preprocessing
*   **Handling Missing Values:** Define strategies for missing data (e.g., fill with defaults, leave as `None` if model allows, or flag as error if required).
*   **Normalization:** Standardize data formats (e.g., date formats, phone numbers, addresses). Convert text to a consistent case (e.g., lowercase) for certain fields before embedding.
*   **Deduplication:** Implement logic to identify and handle duplicate records, if necessary, before loading.
*   **Data Type Coercion:** Explicitly convert data types where Pydantic's default coercion might not be sufficient or to handle source system inconsistencies.

### Identifying Relationships for Neo4j
*   Logic to extract foreign key information (e.g., `CustomerID` on an Order record) from the source data.
*   This information will be used in the Data Loading Layer to create relationships between corresponding nodes in Neo4j (e.g., an `ECCustomer` node and an `Order` node).
*   For many-to-many relationships not directly represented by foreign keys in source tables (e.g. `Order` to `Product` via `OrderItems`), the transformation layer will need to process the intermediary data (like `OrderItems`) to prepare for relationship creation with properties.

### Preparing Text Data for ChromaDB
*   Based on Section 3 of `data_schema_and_transformation_proposal.md`:
    *   Identify text fields specified for embedding (e.g., `Product.Description`, `CustomerReview.ReviewText`, `ChatMessage.MessageText`).
    *   Implement the composite document strategy (e.g., combining `Product.ProductName` and `Product.Description`).
    *   Perform any necessary text cleaning specific to embedding quality (e.g., removing special characters, HTML tags, stop word removal if deemed necessary by the embedding model strategy).

## 5. Data Loading Layer

### Loading into Neo4j
*   **Node Creation/Update:**
    *   Use Cypher queries, potentially via a Neo4j Python driver (e.g., `neo4j-driver`).
    *   Employ `MERGE` operations to create nodes if they don't exist or update them if they do, based on their primary keys (e.g., `MERGE (c:ECCustomer {customerID: $id}) SET c += $props`).
    *   Ensure compliance with the Neo4j schema defined in `src/neo4j_setup/ec_schema.cypher` (and future CRM/Shared schema files), including constraints and indexes.
*   **Relationship Creation/Update:**
    *   After ensuring source and target nodes exist, create relationships using `MERGE` or `CREATE`.
    *   Example: `MATCH (c:ECCustomer {customerID: $cid}), (o:Order {orderID: $oid}) MERGE (c)-[r:PLACED]->(o) SET r += $props`.
    *   Properties on relationships (e.g., `quantity` on `CONTAINS`) will be set during creation.
*   **Batch Operations and Transaction Management:**
    *   Group multiple Cypher statements into batches (e.g., using `UNWIND` with a list of records) for improved performance.
    *   Wrap operations for a set of related data (e.g., an order and its items) within explicit transactions to ensure atomicity.

### Loading into ChromaDB
*   **Generating Vector Embeddings:**
    *   Utilize a chosen sentence transformer model or other embedding model (e.g., from Hugging Face, OpenAI).
    *   The transformation layer provides the prepared text; this layer passes it to the embedding model.
*   **Storing Embeddings and Metadata:**
    *   Connect to ChromaDB using its client library.
    *   Store the generated vector embeddings along with their corresponding IDs (e.g., `ProductID`, `ReviewID`) and the metadata specified in Section 3.3 of the `data_schema_and_transformation_proposal.md`.
*   **Creating/Updating Collections:**
    *   Ensure target collections exist in ChromaDB. Collections might be per entity type (e.g., "products", "reviews").
    *   Use `add` or `upsert` methods to load data into collections.

## 6. Workflow Orchestration & Scheduling

### Tools/Methods
*   **Apache Airflow:** A robust option for complex workflows, offering scheduling, dependency management, UI for monitoring, and retries. DAGs would be defined in Python.
*   **Custom Python Scripts with Schedulers:** Simpler for less complex needs, using libraries like `schedule` or system tools like `cron` for batch jobs.
*   **Serverless Functions (e.g., AWS Lambda, Google Cloud Functions):** Suitable for event-driven ingestion triggered by S3 events, message queue messages, or API Gateway calls.
*   **Workflow Engines (e.g., Prefect, Dagster):** Modern alternatives to Airflow.

### Dependencies and Scheduling
*   Define clear dependencies between tasks (e.g., customer data must be loaded before order data if orders reference customers).
*   Schedule batch jobs based on data availability and business requirements (e.g., nightly, hourly).
*   Implement triggers for event-driven pipelines (e.g., a new CSV file landing in an S3 bucket, a message arriving in a Kafka topic).

## 7. Error Handling and Logging

### Error Detection and Handling
*   Implement try-except blocks around critical operations (extraction, transformation, API calls, database operations).
*   Validate responses from APIs and database operations.
*   For batch jobs, decide on a strategy for partial failures (e.g., skip problematic record and continue, or fail the entire batch).
*   Implement Dead-Letter Queues (DLQs) for messages/records that cannot be processed after several retries.

### Retry Mechanisms
*   Implement exponential backoff and jitter for retrying failed API calls or database connections.
*   Configure retries at the task level in orchestration tools like Airflow.

### Logging Framework
*   Use a standardized logging library (e.g., Python's `logging` module).
*   Log key information: job start/end times, records processed, errors encountered (with tracebacks), data source/destination details.
*   Structure logs for easy parsing and analysis (e.g., JSON format).
*   Consider centralized logging solutions (e.g., ELK stack, Splunk, AWS CloudWatch Logs).

### Alerting
*   Set up alerts for critical failures in ingestion pipelines (e.g., via email, Slack notifications).
*   Integrate with monitoring systems to trigger alerts based on error thresholds.

## 8. Monitoring

### Key Metrics
*   **Data Volume:** Number of records extracted, transformed, loaded. Size of data processed.
*   **Error Rates:** Number and percentage of records failing at each stage.
*   **Latency:** Time taken for data to move from source to destination. End-to-end pipeline duration.
*   **Resource Utilization:** CPU, memory, network usage of ingestion jobs/services.
*   **API Rate Limits:** Monitor usage against API rate limits of source systems.
*   **Queue Depths:** For event-driven systems, monitor message queue depths.

### Potential Tools
*   **Orchestration Tool UI:** Airflow, Prefect, Dagster provide dashboards.
*   **Prometheus & Grafana:** For time-series metrics and visualization.
*   **Cloud Provider Monitoring:** AWS CloudWatch, Google Cloud Monitoring, Azure Monitor.
*   **Application Performance Monitoring (APM) tools:** Datadog, New Relic.

## 9. Testing Strategy for Ingestion Pipelines

### Unit Tests
*   Test individual transformation functions, mapping logic, and data cleaning rules.
*   Use mock data or Pydantic models to create sample inputs.
*   Verify that transformations produce the expected output format and values.

### Integration Tests
*   Test interactions between components (e.g., extraction from a mock API and transformation).
*   Test database connectivity and basic loading operations into mock/dev instances of Neo4j and ChromaDB.

### End-to-End Tests
*   Create small, representative sets of sample data for each source system.
*   Run the entire ingestion pipeline with this sample data.
*   Verify that data is correctly extracted, transformed, and loaded into the target Neo4j and ChromaDB instances, including node/relationship creation and vector embedding generation.
*   Validate data integrity and consistency in the target systems.

This framework aims to be modular and adaptable, allowing for the integration of new data sources and destinations as the project evolves.
