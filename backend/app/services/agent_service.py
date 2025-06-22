"""
Agent Service for NL-to-SQL Agent

This module provides the orchestration layer that combines LLM and Database
services to create and manage the LangChain SQL agent. It is responsible for
agent lifecycle management, query processing, and result formatting.

Features:
- LangChain SQL agent creation and management
- Integration of LLM and Database services
- Agent lifecycle management (initialization, cleanup)
- Query processing with error handling and timeouts
- Result formatting and intermediate step tracking
- Agent performance monitoring and statistics
- Configurable agent behavior and safety settings

Usage:
    from app.services.agent_service import AgentService
    from app.services.llm_service import LLMService
    from app.services.database_service import DatabaseService
    from app.config import get_config

    config = get_config()
    llm_service = LLMService(config)
    db_service = DatabaseService(config)

    agent_service = AgentService(config, llm_service, db_service)
    result = agent_service.invoke_agent("Show me all customers from the USA")
"""

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError, Future
from datetime import datetime
from typing import Dict, Any, Optional

from langchain.agents import AgentExecutor
from langchain_community.agent_toolkits import create_sql_agent, SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase

from backend.app.config import Config
from backend.app.services.database_service import DatabaseService
from backend.app.services.llm_service import LLMService
from backend.app.utils.logger import get_logger, log_exception, log_function_call
from backend.app.utils.react_loop_utils import (
    process_intermediate_steps,
    generate_step_summary,
    generate_execution_flow
)

logger = get_logger(__name__)


class AgentError(Exception):
    """Base exception for agent-related errors."""
    pass


class AgentInitializationError(AgentError):
    """Exception raised when agent initialization fails."""
    pass


class AgentExecutionError(AgentError):
    """Exception raised when agent execution fails."""
    pass


class AgentTimeoutError(AgentError):
    """Exception raised when agent execution exceeds timeout."""
    pass


class AgentService:
    """
    Agent service that orchestrates LLM and Database services to provide
    natural language to SQL query functionality using LangChain agents.

    This service acts as a composition layer, bringing together the LLM and
    Database services to create a cohesive agent experience.
    """

    def __init__(self, custom_config: Config, custom_llm_service: LLMService, database_service: DatabaseService):
        """
        Initialize the agent service.

        Args:
            custom_config: Application configuration instance
            custom_llm_service: Initialized LLM service instance
            database_service: Initialized database service instance
        """
        self.config = custom_config
        self.llm_service = custom_llm_service
        self.database_service = database_service

        # Agent-related attributes
        self.agent_executor: Optional[AgentExecutor] = None
        self.sql_database: Optional[SQLDatabase] = None
        self.toolkit: Optional[SQLDatabaseToolkit] = None

        # Statistics and monitoring
        self._total_queries = 0
        self._successful_queries = 0
        self._failed_queries = 0
        self._total_execution_time = 0.0
        self._last_query_time: Optional[datetime] = None
        self._initialization_time: Optional[datetime] = None

        logger.info("Initializing AgentService")
        self._validate_dependencies()
        self._initialize_agent()
        logger.info("AgentService initialized successfully")

    def _validate_dependencies(self) -> None:
        """Validate that required services are properly initialized."""
        try:
            # Check LLM service
            if not self.llm_service or not self.llm_service.llm:
                raise AgentInitializationError("LLM service is not properly initialized")

            if not self.llm_service.test_connection():
                raise AgentInitializationError("LLM service connection test failed")

            # Check Database service
            if not self.database_service or not self.database_service.engine:
                raise AgentInitializationError("Database service is not properly initialized")

            if not self.database_service.test_connection():
                raise AgentInitializationError("Database service connection test failed")

            logger.info("Agent service dependencies validated successfully")

        except Exception as err:
            error_msg = f"Agent service dependency validation failed: {err}"
            logger.error(error_msg)
            raise AgentInitializationError(error_msg) from err

    def _initialize_agent(self) -> None:
        """Initialize the LangChain SQL agent with toolkit."""
        try:
            start_time = time.time()
            logger.info("Creating LangChain SQL agent")

            # Create SQLDatabase instance for LangChain
            self.sql_database = SQLDatabase.from_uri(
                database_uri=self.config.DATABASE_URI,
                include_tables=None,  # Include all tables by default
                sample_rows_in_table_info=3  # Include sample data in table descriptions
            )

            # Create SQL toolkit
            self.toolkit = SQLDatabaseToolkit(
                db=self.sql_database,
                llm=self.llm_service.llm
            )

            # Create agent executor with comprehensive configuration
            self.agent_executor = create_sql_agent(
                llm=self.llm_service.llm,
                toolkit=self.toolkit,
                verbose=self.config.AGENT_VERBOSE,
                agent_type=self.config.AGENT_TYPE,
                max_iterations=self.config.AGENT_MAX_ITERATIONS,
                max_execution_time=self.config.AGENT_MAX_EXECUTION_TIME,
                early_stopping_method="generate",  # Stop when final answer is generated
                handle_parsing_errors=True,  # Gracefully handle LLM parsing errors
                return_intermediate_steps=True  # Return full execution trace
            )

            end_time = time.time()
            initialization_time = end_time - start_time
            self._initialization_time = datetime.now()

            logger.info(f"SQL agent created successfully (initialization time: {initialization_time:.2f}s)")

            # Validate agent functionality
            self._validate_agent_functionality()

        except Exception as err:
            error_msg = f"Failed to initialize SQL agent: {err}"
            logger.error(error_msg)
            raise AgentInitializationError(error_msg) from err

    def _validate_agent_functionality(self) -> None:
        """Validate that the agent can perform basic operations."""
        try:
            logger.debug("Validating agent functionality")

            # Test that the agent can list tables
            tables = list(self.sql_database.get_usable_table_names())
            if not tables:
                logger.warning("No tables found in database")
            else:
                logger.info(f"Agent has access to {len(tables)} tables: {', '.join(tables[:5])}" +
                            ("..." if len(tables) > 5 else ""))

            # Test table info retrieval
            if tables:
                sample_table = tables[0]
                table_info = self.sql_database.get_table_info([sample_table])
                if table_info:
                    logger.debug(f"Successfully retrieved info for table: {sample_table}")
                else:
                    logger.warning(f"Could not retrieve info for table: {sample_table}")

            logger.info("Agent functionality validation completed")

        except Exception as err:
            logger.warning(f"Agent functionality validation encountered issues: {err}")
            # Don't raise exception here as this is just a validation check

    def invoke_agent(self, question: str, include_intermediate_steps: bool = True) -> Dict[str, Any]:
        """
        Invoke the SQL agent with a natural language question.

        Args:
            question: Natural language question about the database
            include_intermediate_steps: Whether to include execution trace

        Returns:
            Dictionary containing the agent's response and metadata

        Raises:
            AgentExecutionError: If agent execution fails
            AgentTimeoutError: If execution exceeds timeout
        """
        if not question or not question.strip():
            raise AgentExecutionError("Question cannot be empty")

        if not self.agent_executor:
            raise AgentExecutionError("Agent not properly initialized")

        # Update statistics
        self._total_queries += 1
        self._last_query_time = datetime.now()

        log_function_call("invoke_agent", (question,), {"include_intermediate_steps": include_intermediate_steps})

        try:
            start_time = time.time()
            logger.info(f"Executing agent query: {question[:100]}{'...' if len(question) > 100 else ''}")

            # Execute agent with timeout handling
            custom_result = self._execute_with_timeout(question)

            end_time = time.time()
            execution_time = end_time - start_time
            self._total_execution_time += execution_time

            # Process and format result
            formatted_result = self._format_agent_result(
                custom_result,
                execution_time,
                include_intermediate_steps
            )

            self._successful_queries += 1
            logger.info(f"Agent query completed successfully (time: {execution_time:.2f}s)")

            return formatted_result

        except AgentTimeoutError:
            self._failed_queries += 1
            raise

        except Exception as err:
            self._failed_queries += 1
            error_msg = f"Agent execution failed: {err}"
            logger.error(error_msg)
            log_exception(logger, err, "agent execution")
            raise AgentExecutionError(error_msg) from err

    def _execute_with_timeout(self, question: str) -> Dict[str, Any]:
        """
        Execute agent query with timeout handling.

        Args:
            question: Question to execute

        Returns:
            Agent execution result

        Raises:
            AgentTimeoutError: If execution exceeds timeout
        """
        timeout = self.config.AGENT_MAX_EXECUTION_TIME
        payload: Dict[str, Any] = {"input": question}

        try:
            # Use ThreadPoolExecutor to handle timeout
            with ThreadPoolExecutor(max_workers=1) as executor:
                future: Future[dict[str, Any]] = executor.submit(
                    lambda: self.agent_executor.invoke(payload)
                )

                try:
                    future_result = future.result(timeout=timeout)
                    return future_result

                except FutureTimeoutError:
                    error_msg = f"Agent execution timed out after {timeout} seconds"
                    logger.error(error_msg)
                    raise AgentTimeoutError(error_msg)

        except AgentTimeoutError:
            raise
        except Exception as err:
            # Re-raise as execution error
            raise AgentExecutionError(f"Agent execution failed: {err}") from err

    def _format_agent_result(self, custom_result: Dict[str, Any], execution_time: float,
                             include_intermediate_steps: bool) -> Dict[str, Any]:
        """
        Format agent execution result for consistent API response.

        Args:
            custom_result: Raw agent execution result
            execution_time: Execution time in seconds
            include_intermediate_steps: Whether to include execution trace

        Returns:
            Formatted result dictionary
        """
        formatted = {
            "answer": custom_result.get("output", "No answer generated"),
            "execution_time": round(execution_time, 2),
            "timestamp": datetime.now().isoformat(),
            "query_id": f"query_{int(time.time())}"
        }

        # Enhanced intermediate steps processing
        if include_intermediate_steps and "intermediate_steps" in custom_result:
            react_steps = process_intermediate_steps(custom_result["intermediate_steps"])

            formatted["react_loop"] = {
                "steps": react_steps,
                "total_steps": len(react_steps),
                "step_summary": generate_step_summary(react_steps),
                "execution_flow": generate_execution_flow(react_steps)
            }

        # Enhanced metadata
        formatted["metadata"] = {
            "agent_type": self.config.AGENT_TYPE,
            "model_name": self.config.GEMINI_MODEL_NAME,
            "database_type": self.database_service.engine.dialect.name if self.database_service.engine else "unknown",
            "total_iterations": len(custom_result.get("intermediate_steps", [])),
            "success": True,
            "processing_details": {
                "thought_extraction": "enabled",
                "sql_formatting": "enabled",
                "tool_categorization": "enabled"
            }
        }

        return formatted

    def get_agent_status(self) -> Dict[str, Any]:
        """
        Get comprehensive agent status and health information.

        Returns:
            Dictionary with agent status information
        """
        custom_status = {
            "initialized": self.agent_executor is not None,
            "llm_service_status": self.llm_service.get_health_status(),
            "database_service_status": self.database_service.get_health_status(),
            "agent_configuration": {
                "agent_type": self.config.AGENT_TYPE,
                "max_iterations": self.config.AGENT_MAX_ITERATIONS,
                "max_execution_time": self.config.AGENT_MAX_EXECUTION_TIME,
                "verbose": self.config.AGENT_VERBOSE
            },
            "statistics": self.get_usage_statistics(),
            "available_tables": [],
            "initialization_time": self._initialization_time.isoformat() if self._initialization_time else None
        }

        # Get available tables if agent is initialized
        if self.sql_database:
            try:
                custom_status["available_tables"] = list(self.sql_database.get_usable_table_names())
            except Exception as err:
                logger.warning(f"Could not retrieve table names: {err}")
                custom_status["available_tables"] = []

        return custom_status

    def get_usage_statistics(self) -> Dict[str, Any]:
        """
        Get agent usage statistics.

        Returns:
            Dictionary with usage statistics
        """
        avg_execution_time = (
            self._total_execution_time / self._successful_queries
            if self._successful_queries > 0 else 0
        )

        success_rate = (
            (self._successful_queries / self._total_queries * 100)
            if self._total_queries > 0 else 0
        )

        return {
            "total_queries": self._total_queries,
            "successful_queries": self._successful_queries,
            "failed_queries": self._failed_queries,
            "success_rate_percent": round(success_rate, 2),
            "total_execution_time": round(self._total_execution_time, 2),
            "average_execution_time": round(avg_execution_time, 2),
            "last_query_time": self._last_query_time.isoformat() if self._last_query_time else None
        }

    def get_database_info(self) -> Dict[str, Any]:
        """
        Get database information accessible to the agent.

        Returns:
            Dictionary with database information
        """
        if not self.sql_database:
            return {"error": "Agent not initialized"}

        try:
            return {
                "database_type": self.database_service.engine.dialect.name,
                "available_tables": self.sql_database.get_usable_table_names(),
                "sample_table_info": self._get_sample_table_info()
            }
        except Exception as err:
            log_exception(logger, err, "get_database_info")
            return {"error": str(err)}

    def _get_sample_table_info(self) -> Dict[str, str]:
        """Get sample table information for a few tables."""
        try:
            tables = self.sql_database.get_usable_table_names()
            sample_info = {}

            # Get info for first 3 tables
            for table in tables[:3]:
                try:
                    info = self.sql_database.get_table_info([table])
                    sample_info[table] = info[:200] + "..." if len(info) > 200 else info
                except Exception as err:
                    sample_info[table] = f"Error retrieving info: {err}"

            return sample_info
        except Exception:
            return {}

    def close(self) -> None:
        """Clean up agent service resources."""
        logger.info("Closing AgentService")

        if self.agent_executor:
            self.agent_executor = None

        if self.toolkit:
            self.toolkit = None

        if self.sql_database:
            self.sql_database = None

        logger.info("AgentService closed successfully")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.close()

    def __repr__(self) -> str:
        """String representation of agent service."""
        initialized = self.agent_executor is not None
        success_rate = (
            (self._successful_queries / self._total_queries * 100)
            if self._total_queries > 0 else 0
        )
        return (f"AgentService(initialized={initialized}, queries={self._total_queries}, "
                f"success_rate={success_rate:.1f}%)")


def create_agent_service(custom_config: Optional[Config] = None,
                         custom_llm_service: Optional[LLMService] = None,
                         database_service: Optional[DatabaseService] = None) -> AgentService:
    """
    Factory function to create an agent service instance.

    Args:
        custom_config: Optional configuration instance
        custom_llm_service: Optional LLM service instance
        database_service: Optional database service instance

    Returns:
        Configured AgentService instance
    """
    if custom_config is None:
        from backend.app.config import get_config
        custom_config = get_config()

    if custom_llm_service is None:
        from backend.app.services.llm_service import create_llm_service
        custom_llm_service = create_llm_service(custom_config)

    if database_service is None:
        from backend.app.services.database_service import create_database_service
        database_service = create_database_service(custom_config)

    return AgentService(custom_config, custom_llm_service, database_service)


if __name__ == "__main__":
    """Test agent service when module is executed directly."""
    print("Testing AgentService...")

    try:
        from backend.app.config import get_config
        from backend.app.services.llm_service import create_llm_service
        from backend.app.services.database_service import create_database_service

        # Load configuration
        config = get_config()

        # Create services
        llm_service = create_llm_service(config)
        db_service = create_database_service(config)

        # Create agent service
        with create_agent_service(config, llm_service, db_service) as agent_service:
            print(f"Agent service: {agent_service}")

            # Get agent status
            status = agent_service.get_agent_status()
            print(f"✓ Agent initialized: {status['initialized']}")
            print(f"✓ Available tables: {len(status['available_tables'])}")

            if status['available_tables']:
                print(f"  Tables: {', '.join(status['available_tables'][:3])}" +
                      ("..." if len(status['available_tables']) > 3 else ""))

            # Test simple query
            try:
                test_question = "How many tables are in this database and list all of their name?"
                result = agent_service.invoke_agent(test_question)
                print(f"✓ Test query successful:")
                print(f"  Question: {test_question}")
                print(f"  Answer: {result['answer'][:100]}{'...' if len(result['answer']) > 100 else ''}")
                print(f"  Execution time: {result['execution_time']}s")

            except Exception as e:
                print(f"✗ Test query failed: {e}")

            # Get usage statistics
            stats = agent_service.get_usage_statistics()
            print(f"✓ Total queries: {stats['total_queries']}")
            print(f"✓ Success rate: {stats['success_rate_percent']}%")

    except Exception as e:
        print(f"✗ AgentService test failed: {e}")
        import traceback

        traceback.print_exc()
