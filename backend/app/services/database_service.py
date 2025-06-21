"""
Database Service for NL-to-SQL Agent

This module provides a dedicated service for managing database connections,
health checks, and SQL operations using SQLAlchemy. It is completely decoupled
from LLM logic and can be used independently.

Features:
- SQLAlchemy database connection management
- Connection pooling and health monitoring
- Schema inspection and metadata retrieval
- Query execution with error handling
- Database connectivity testing
- Connection lifecycle management

Usage:
    from app.services.database_service import DatabaseService
    from app.config import get_config

    config = get_config()
    db_service = DatabaseService(config)

    # Test connection
    if db_service.test_connection():
        tables = db_service.get_table_names()
        print(f"Available tables: {tables}")
"""

import time
from contextlib import contextmanager
from typing import List, Dict, Any, Optional

from sqlalchemy import create_engine, text, inspect, MetaData
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, OperationalError, TimeoutError
from sqlalchemy.pool import StaticPool, QueuePool

from backend.app.config import Config
from backend.app.utils import get_logger, log_exception

# Initialize logger for this module
logger = get_logger(__name__)


class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Exception raised when database connection fails."""
    pass


class DatabaseQueryError(DatabaseError):
    """Exception raised when database query execution fails."""
    pass


def _mask_uri(uri: str) -> str:
    """Mask sensitive information in database URI for logging."""
    if '://' in uri:
        scheme, rest = uri.split('://', 1)
        if '@' in rest:
            # Has credentials
            credentials, location = rest.split('@', 1)
            return f"{scheme}://***@{location}"
        return uri
    return uri


class DatabaseService:
    """
    Database service that manages SQLAlchemy connections and operations.

    This service provides a clean interface for database operations while
    handling connection pooling, error recovery, and health monitoring.
    """

    def __init__(self, custom_config: Config):
        """
        Initialize the database service.

        Args:
            custom_config: Application configuration instance
        """
        self.config = custom_config
        self.engine: Optional[Engine] = None
        self._metadata: Optional[MetaData] = None
        self._last_health_check: Optional[float] = None
        self._health_check_interval = 300  # 5 minutes

        logger.info("Initializing DatabaseService")
        self._initialize_engine()
        self._verify_connection()
        logger.info("DatabaseService initialized successfully")

    def _initialize_engine(self) -> None:
        """Initialize SQLAlchemy engine with appropriate configuration."""
        try:
            database_uri = self.config.DATABASE_URI
            logger.info(f"Creating database engine for: {_mask_uri(database_uri)}")

            # Configure engine parameters based on database type
            engine_kwargs = self._get_engine_kwargs(database_uri)

            self.engine = create_engine(database_uri, **engine_kwargs)
            logger.info("Database engine created successfully")

        except Exception as err:
            error_msg = f"Failed to create database engine: {err}"
            logger.error(error_msg)
            raise DatabaseConnectionError(error_msg) from err

    def _get_engine_kwargs(self, database_uri: str) -> Dict[str, Any]:
        """
        Get engine configuration based on database type.

        Args:
            database_uri: Database connection URI

        Returns:
            Dictionary of engine configuration parameters
        """
        kwargs = {
            'echo': self.config.FLASK_DEBUG,  # Log SQL queries in debug mode
            'future': True,  # Use SQLAlchemy 2.0 style
        }

        if database_uri.startswith('sqlite:'):
            # SQLite-specific configuration
            kwargs.update({
                'poolclass': StaticPool,
                'connect_args': {
                    'check_same_thread': False,  # Allow multi-threading
                    'timeout': self.config.DATABASE_POOL_TIMEOUT
                }
            })
            logger.debug("Using SQLite engine configuration")

        else:
            # PostgreSQL/MySQL configuration
            kwargs.update({
                'poolclass': QueuePool,
                'pool_size': self.config.DATABASE_POOL_SIZE,
                'pool_timeout': self.config.DATABASE_POOL_TIMEOUT,
                'pool_recycle': 3600,  # Recycle connections every hour
                'pool_pre_ping': True,  # Verify connections before use
            })
            logger.debug("Using connection pooling configuration")

        return kwargs

    def _verify_connection(self) -> None:
        """Verify database connection during initialization."""
        if not self.test_connection():
            raise DatabaseConnectionError("Failed to establish database connection during initialization")

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.

        Yields:
            SQLAlchemy Connection object

        Raises:
            DatabaseConnectionError: If connection cannot be established
        """
        if not self.engine:
            raise DatabaseConnectionError("Database engine not initialized")

        connection = None
        try:
            connection = self.engine.connect()
            logger.debug("Database connection acquired")
            yield connection

        except OperationalError as err:
            error_msg = f"Database operational error: {err}"
            logger.error(error_msg)
            raise DatabaseConnectionError(error_msg) from err

        except TimeoutError as err:
            error_msg = f"Database connection timeout: {err}"
            logger.error(error_msg)
            raise DatabaseConnectionError(error_msg) from err

        except SQLAlchemyError as err:
            error_msg = f"SQLAlchemy error: {err}"
            logger.error(error_msg)
            raise DatabaseError(error_msg) from err

        finally:
            if connection:
                connection.close()
                logger.debug("Database connection released")

    def test_connection(self) -> bool:
        """
        Test database connectivity.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                # Simple query to test connection
                custom_result = conn.execute(text("SELECT 1"))
                custom_result.fetchone()
                logger.debug("Database connection test successful")
                self._last_health_check = time.time()
                return True

        except Exception as err:
            log_exception(logger, err, "database connection test")
            return False

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive database health status.

        Returns:
            Dictionary with health status information
        """
        status = {
            'connected': False,
            'last_check': self._last_health_check,
            'engine_status': 'not_initialized' if not self.engine else 'initialized',
            'database_type': None,
            'connection_info': {}
        }

        try:
            if self.engine:
                status['database_type'] = self.engine.dialect.name
                status['connection_info'] = {
                    'pool_size': getattr(self.engine.pool, 'size', 'N/A'),
                    'checked_out': getattr(self.engine.pool, 'checked_out', 'N/A'),
                    'checked_in': getattr(self.engine.pool, 'checked_in', 'N/A'),
                }

            # Perform connection test if it's been a while
            current_time = time.time()
            if (not self._last_health_check or
                    current_time - self._last_health_check > self._health_check_interval):
                status['connected'] = self.test_connection()
            else:
                status['connected'] = True  # Assume healthy if recently checked

        except Exception as err:
            log_exception(logger, err, "health status check")
            status['error'] = str(err)

        return status

    def get_table_names(self) -> List[str]:
        """
        Get list of all table names in the database.

        Returns:
            List of table names

        Raises:
            DatabaseError: If unable to retrieve table names
        """
        try:
            with self.get_connection() as conn:
                inspector = inspect(conn)
                tables = inspector.get_table_names()
                logger.debug(f"Retrieved {len(tables)} table names")
                return tables

        except Exception as err:
            error_msg = f"Failed to retrieve table names: {err}"
            logger.error(error_msg)
            raise DatabaseError(error_msg) from err

    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """
        Get detailed schema information for a specific table.

        Args:
            table_name: Name of the table

        Returns:
            Dictionary with table schema information

        Raises:
            DatabaseError: If unable to retrieve table schema
        """
        try:
            with self.get_connection() as conn:
                inspector = inspect(conn)

                # Get column information
                columns = inspector.get_columns(table_name)

                # Get primary key information
                pk_constraint = inspector.get_pk_constraint(table_name)

                # Get foreign key information
                foreign_keys = inspector.get_foreign_keys(table_name)

                # Get index information
                indexes = inspector.get_indexes(table_name)

                schema_info = {
                    'table_name': table_name,
                    'columns': columns,
                    'primary_key': pk_constraint,
                    'foreign_keys': foreign_keys,
                    'indexes': indexes
                }

                logger.debug(f"Retrieved schema for table: {table_name}")
                return schema_info

        except Exception as err:
            error_msg = f"Failed to retrieve schema for table '{table_name}': {err}"
            logger.error(error_msg)
            raise DatabaseError(error_msg) from err

    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results.

        Args:
            query: SQL query string
            parameters: Optional query parameters

        Returns:
            List of dictionaries representing query results

        Raises:
            DatabaseQueryError: If query execution fails
        """
        if not query.strip():
            raise DatabaseQueryError("Query cannot be empty")

        # Security check - prevent destructive operations
        query_upper = query.upper().strip()
        destructive_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']

        for keyword in destructive_keywords:
            if query_upper.startswith(keyword):
                error_msg = f"Destructive SQL operations are not allowed: {keyword}"
                logger.warning(f"Blocked destructive query: {query[:100]}...")
                raise DatabaseQueryError(error_msg)

        try:
            with self.get_connection() as conn:
                logger.debug(f"Executing query: {query[:100]}{'...' if len(query) > 100 else ''}")

                # Execute query with optional parameters
                if parameters:
                    custom_result = conn.execute(text(query), parameters)
                else:
                    custom_result = conn.execute(text(query))

                # Convert results to list of dictionaries
                rows = custom_result.fetchall()
                column_names = custom_result.keys()

                results = [dict(zip(column_names, row)) for row in rows]

                logger.info(f"Query executed successfully, returned {len(results)} rows")
                return results

        except SQLAlchemyError as err:
            error_msg = f"SQL execution error: {err}"
            logger.error(error_msg)
            raise DatabaseQueryError(error_msg) from err

        except Exception as err:
            error_msg = f"Unexpected error during query execution: {err}"
            logger.error(error_msg)
            raise DatabaseQueryError(error_msg) from err

    def get_database_info(self) -> Dict[str, Any]:
        """
        Get comprehensive database information.

        Returns:
            Dictionary with database metadata
        """
        try:
            db_info = {
                'database_type': self.engine.dialect.name if self.engine else None,
                'database_uri': _mask_uri(self.config.DATABASE_URI),
                'total_tables': 0,
                'table_names': [],
                'health_status': self.get_health_status()
            }

            if self.test_connection():
                table_names = self.get_table_names()
                db_info['total_tables'] = len(table_names)
                db_info['table_names'] = table_names

            return db_info

        except Exception as err:
            log_exception(logger, err, "get_database_info")
            return {'error': str(err)}

    def close(self) -> None:
        """Close database engine and cleanup resources."""
        if self.engine:
            logger.info("Closing database engine")
            self.engine.dispose()
            self.engine = None
            logger.info("Database engine closed successfully")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.close()

    def __repr__(self) -> str:
        """String representation of database service."""
        db_type = self.engine.dialect.name if self.engine else 'Unknown'
        return f"DatabaseService(type={db_type}, connected={self.test_connection()})"


def create_database_service(custom_config: Optional[Config] = None) -> DatabaseService:
    """
    Factory function to create a database service instance.

    Args:
        custom_config: Optional configuration instance

    Returns:
        Configured DatabaseService instance
    """
    if custom_config is None:
        from backend.app.config import get_config
        custom_config = get_config()

    return DatabaseService(custom_config)


if __name__ == "__main__":
    """Test database service when module is executed directly."""
    print("Testing DatabaseService...")

    try:
        from backend.app.config import get_config

        # Load configuration
        config = get_config()

        # Create database service
        with create_database_service(config) as db_service:
            print(f"Database service: {db_service}")

            # Test connection
            if db_service.test_connection():
                print("✓ Database connection successful")

                # Get database info
                info = db_service.get_database_info()
                print(f"✓ Database type: {info['database_type']}")
                print(f"✓ Total tables: {info['total_tables']}")

                if info['table_names']:
                    print(f"✓ Tables: {', '.join(info['table_names'][:5])}" +
                          ("..." if len(info['table_names']) > 5 else ""))

                # Test simple query
                try:
                    result = db_service.execute_query("SELECT 1 as test_column")
                    print(f"✓ Test query successful: {result}")
                except Exception as e:
                    print(f"✗ Test query failed: {e}")

            else:
                print("✗ Database connection failed")

    except Exception as e:
        print(f"✗ DatabaseService test failed: {e}")
        import traceback

        traceback.print_exc()
