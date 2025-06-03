# Required dependency: neo4j
# Example: pip install neo4j
import os
from neo4j import GraphDatabase, unit_of_work
from neo4j.exceptions import Neo4jError, ServiceUnavailable, CypherSyntaxError

class Neo4jConnector:
    """
    A connector class for interacting with a Neo4j database.

    Manages the Neo4j driver instance, provides methods for query execution,
    and handles connection parameters via environment variables with defaults.
    Supports use as a context manager to ensure connections are closed.
    """

    def __init__(self, uri=None, username=None, password=None):
        """
        Initializes the Neo4jConnector.

        Connection parameters are sourced from environment variables (NEO4J_URI,
        NEO4J_USERNAME, NEO4J_PASSWORD) if not provided directly.
        Defaults are used for local development if no parameters are found.

        Args:
            uri (str, optional): The URI for the Neo4j database.
                                 Defaults to os.environ.get('NEO4J_URI', 'bolt://localhost:7687').
            username (str, optional): The username for authentication.
                                      Defaults to os.environ.get('NEO4J_USERNAME', 'neo4j').
            password (str, optional): The password for authentication.
                                      Defaults to os.environ.get('NEO4J_PASSWORD', 'password').

        Raises:
            ServiceUnavailable: If the driver cannot be initialized (e.g., database not reachable).
        """
        db_uri = uri or os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
        db_username = username or os.environ.get('NEO4J_USERNAME', 'neo4j')
        db_password = password or os.environ.get('NEO4J_PASSWORD', 'password')

        self._driver = None
        try:
            self._driver = GraphDatabase.driver(db_uri, auth=(db_username, db_password))
            # Verify connection by trying to fetch server info or a simple query
            self._driver.verify_connectivity()
            print(f"Successfully connected to Neo4j at {db_uri}")
        except ServiceUnavailable as e:
            print(f"Error: Could not connect to Neo4j at {db_uri}. Details: {e}")
            raise  # Re-raise the exception after logging
        except Exception as e: # Catch other potential auth errors etc.
            print(f"Error: Failed to initialize Neo4j driver. Details: {e}")
            raise

    def close(self):
        """Closes the Neo4j driver connection if it's open."""
        if self._driver is not None:
            try:
                self._driver.close()
                print("Neo4j connection closed.")
            except Exception as e:
                print(f"Error while closing Neo4j connection: {e}")

    def execute_query(self, query: str, parameters: dict = None, db: str = None, tx_type: str = 'write'):
        """
        Executes a Cypher query against the Neo4j database.

        Args:
            query (str): The Cypher query to execute.
            parameters (dict, optional): A dictionary of parameters for the query. Defaults to None.
            db (str, optional): The name of the database to execute the query against.
                                Defaults to the default database of the driver.
            tx_type (str, optional): The type of transaction. Can be 'read' or 'write'.
                                     Defaults to 'write'. 'read' uses execute_read,
                                     'write' uses execute_write.

        Returns:
            list: A list of records (dictionaries) returned by the query.
                  Returns an empty list if the query yields no data or on error.
            None: Returns None if a significant error occurs during session/transaction.

        Raises:
            CypherSyntaxError: If the query has a syntax error.
            Neo4jError: For other Neo4j-related errors during query execution.
            Exception: For unexpected errors.
        """
        if self._driver is None:
            print("Error: Driver not initialized. Cannot execute query.")
            return None # Or raise an exception

        records = []
        summary = None

        session_params = {}
        if db:
            session_params['database'] = db

        try:
            with self._driver.session(**session_params) as session:
                if tx_type == 'read':
                    result = session.execute_read(
                        self._run_transaction_function, query, parameters
                    )
                elif tx_type == 'write':
                    result = session.execute_write(
                        self._run_transaction_function, query, parameters
                    )
                else:
                    raise ValueError(f"Invalid tx_type: {tx_type}. Must be 'read' or 'write'.")

                # Process results if any
                if result: # result from _run_transaction_function is the list of records
                    records = result
                # Accessing summary might be different if we want it from the Result object
                # For now, _run_transaction_function returns the list of records directly.
                # If you need detailed summary (counters, etc.), the transaction function would need to return the Result object
                # and then process summary here. This example focuses on returning data.

        except CypherSyntaxError as e:
            print(f"Cypher syntax error in query: {query}\nParameters: {parameters}\nError: {e}")
            raise
        except Neo4jError as e:
            print(f"Neo4j error executing query: {query}\nParameters: {parameters}\nError: {e}")
            # Depending on policy, might raise, or return empty/None
            raise
        except ValueError as e: # For invalid tx_type
            print(f"ValueError: {e}")
            raise
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            raise # Re-raise unexpected errors

        return records

    @staticmethod
    @unit_of_work(timeout=5.0) # Example timeout for transaction
    def _run_transaction_function(tx, query, parameters=None):
        """Helper function to run a query within a transaction."""
        result = tx.run(query, parameters)
        return [record.data() for record in result]

    def __enter__(self):
        """Enables use of the connector in a 'with' statement."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Closes the connection when exiting a 'with' statement."""
        self.close()

# Conceptual Example Usage (typically in another script)
if __name__ == "__main__":
    print("Attempting to connect to Neo4j using Neo4jConnector...")

    # Ensure Neo4j is running and accessible with credentials (defaults or from ENV)
    # For this example to run, you might need a local Neo4j instance.
    # E.g., docker run --rm -p 7687:7687 -p 7474:7474 -e NEO4J_AUTH=neo4j/password neo4j:latest

    created_nodes = 0
    try:
        with Neo4jConnector() as connector:
            # Example: Create some data (Write transaction)
            connector.execute_query(
                "MERGE (p:Person {name: $name}) RETURN p",
                parameters={"name": "Alice"},
                tx_type='write'
            )
            print("Created or merged Alice.")
            created_nodes +=1

            connector.execute_query(
                "MERGE (p:Person {name: $name}) RETURN p",
                parameters={"name": "Bob"},
                tx_type='write'
            )
            print("Created or merged Bob.")
            created_nodes +=1

            # Example: Read data
            results = connector.execute_query("MATCH (n:Person) RETURN n.name AS name, elementId(n) as id LIMIT 5", tx_type='read')
            if results:
                print("\nFound people:")
                for record in results:
                    print(f"- Name: {record['name']}, ID: {record['id']}")
            else:
                print("\nNo people found or error in query.")

            # Example: Count nodes (Read transaction)
            count_results = connector.execute_query("MATCH (n) RETURN count(n) AS node_count", tx_type='read')
            if count_results:
                print(f"\nTotal node count: {count_results[0]['node_count']}")

    except ServiceUnavailable:
        print("Neo4j service is unavailable. Please ensure Neo4j is running and accessible.")
    except CypherSyntaxError as e:
        print(f"A Cypher syntax error occurred: {e}")
    except Neo4jError as e:
        print(f"A Neo4j specific error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during the example usage: {e}")
    finally:
        # Optional: Clean up test data if needed, though MERGE is idempotent
        if created_nodes > 0:
            try:
                with Neo4jConnector() as connector:
                    connector.execute_query("MATCH (p:Person {name: 'Alice'}) DELETE p", tx_type='write')
                    connector.execute_query("MATCH (p:Person {name: 'Bob'}) DELETE p", tx_type='write')
                    print("\nCleaned up test Person nodes.")
            except Exception as e:
                print(f"Error during cleanup: {e}")
        print("Neo4j connector example finished.")
