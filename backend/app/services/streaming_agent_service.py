"""
Streaming Agent Service for Real-time ReAct Loop Processing

This enhanced version provides real-time streaming of the agent's thought process
using custom callback handlers and server-sent events.
"""

import json
import threading
import time
from datetime import datetime
from queue import Queue, Empty
from typing import Dict, Any, Optional, Generator

from langchain.agents import AgentExecutor
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import AgentAction, AgentFinish
from langchain_community.agent_toolkits import create_sql_agent, SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase

from backend.app.config import Config
from backend.app.services.database_service import DatabaseService
from backend.app.services.llm_service import LLMService
from backend.app.utils.logger import get_logger
from backend.app.utils.react_loop_utils import (
    extract_thought_from_log,
    categorize_tool_action,
    format_sql_query,
    detect_result_type
)

logger = get_logger(__name__)


class StreamingCallbackHandler(BaseCallbackHandler):
    """
    Custom callback handler that captures agent execution steps in real-time
    and streams them via a queue.
    """

    def __init__(self, event_queue: Queue):
        super().__init__()
        self.event_queue = event_queue
        self.step_counter = 0
        self.current_thought = None

    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> None:
        """Called when the agent takes an action."""
        self.step_counter += 1

        # Extract thought from the action log
        thought = extract_thought_from_log(action.log)

        # Get tool information
        tool_info = categorize_tool_action(action.tool)

        # Format tool input
        formatted_input = action.tool_input
        if action.tool == 'sql_db_query' and isinstance(action.tool_input, str):
            formatted_input = format_sql_query(action.tool_input)

        # Create action event
        action_event = {
            "type": "agent_action",
            "step_number": self.step_counter,
            "timestamp": datetime.now().isoformat(),
            "thought": thought,
            "action": {
                "tool": action.tool,
                "category": tool_info['category'],
                "description": tool_info['description'],
                "purpose": tool_info['purpose'],
                "input": formatted_input,
                "raw_input": action.tool_input
            }
        }

        # Stream the action
        self.event_queue.put(action_event)

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Called when a tool finishes execution."""
        # Get the tool name from kwargs if available
        tool_name = kwargs.get('name', 'unknown')

        # Create observation event
        observation_event = {
            "type": "agent_observation",
            "step_number": self.step_counter,
            "timestamp": datetime.now().isoformat(),
            "observation": {
                "result": output,
                "result_type": detect_result_type(output, tool_name),
                "success": len(output.strip()) > 0 if output else False
            }
        }

        # Stream the observation
        self.event_queue.put(observation_event)

    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> None:
        """Called when the agent finishes execution."""
        finish_event = {
            "type": "agent_finish",
            "timestamp": datetime.now().isoformat(),
            "final_answer": finish.return_values.get("output", "No answer generated"),
            "total_steps": self.step_counter
        }

        # Stream the final answer
        self.event_queue.put(finish_event)

    def on_chain_error(self, error: Exception, **kwargs: Any) -> None:
        """Called when an error occurs."""
        error_event = {
            "type": "agent_error",
            "timestamp": datetime.now().isoformat(),
            "error": {
                "message": str(error),
                "type": type(error).__name__
            }
        }

        self.event_queue.put(error_event)


class StreamingAgentService:
    """
    Enhanced Agent Service that provides real-time streaming of the ReAct loop process.
    """

    def __init__(self, custom_config: Config, custom_llm_service: LLMService, database_service: DatabaseService):
        """Initialize the streaming agent service."""
        self.config = custom_config
        self.llm_service = custom_llm_service
        self.database_service = database_service

        # Agent-related attributes
        self.agent_executor: Optional[AgentExecutor] = None
        self.sql_database: Optional[SQLDatabase] = None
        self.toolkit: Optional[SQLDatabaseToolkit] = None

        # Statistics
        self._total_queries = 0
        self._successful_queries = 0
        self._failed_queries = 0

        logger.info("Initializing StreamingAgentService")
        self._validate_dependencies()
        self._initialize_agent()
        logger.info("StreamingAgentService initialized successfully")

    def _validate_dependencies(self) -> None:
        """Validate that required services are properly initialized."""
        if not self.llm_service or not self.llm_service.llm:
            raise Exception("LLM service is not properly initialized")

        if not self.llm_service.test_connection():
            raise Exception("LLM service connection test failed")

        if not self.database_service or not self.database_service.engine:
            raise Exception("Database service is not properly initialized")

        if not self.database_service.test_connection():
            raise Exception("Database service connection test failed")

    def _initialize_agent(self) -> None:
        """Initialize the LangChain SQL agent."""
        try:
            # Create SQLDatabase instance for LangChain
            self.sql_database = SQLDatabase.from_uri(
                database_uri=self.config.DATABASE_URI,
                include_tables=None,
                sample_rows_in_table_info=3
            )

            # Create SQL toolkit
            self.toolkit = SQLDatabaseToolkit(
                db=self.sql_database,
                llm=self.llm_service.llm
            )

            # Create agent executor
            self.agent_executor = create_sql_agent(
                llm=self.llm_service.llm,
                toolkit=self.toolkit,
                verbose=self.config.AGENT_VERBOSE,
                agent_type=self.config.AGENT_TYPE,
                max_iterations=self.config.AGENT_MAX_ITERATIONS,
                max_execution_time=self.config.AGENT_MAX_EXECUTION_TIME,
                early_stopping_method="generate",
                handle_parsing_errors=True,
                return_intermediate_steps=False  # We handle this with callbacks
            )

            logger.info("Streaming SQL agent created successfully")

        except Exception as err:
            logger.error(f"Failed to initialize streaming SQL agent: {err}")
            raise

    def stream_agent_execution(self, question: str) -> Generator[str, None, None]:
        """
        Stream the agent execution in real-time.

        Args:
            question: Natural language question

        Yields:
            Server-sent event formatted strings
        """
        if not question or not question.strip():
            yield f"data: {json.dumps({'type': 'error', 'message': 'Question cannot be empty'})}\n\n"
            return

        if not self.agent_executor:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Agent not initialized'})}\n\n"
            return

        # Create event queue for streaming
        event_queue = Queue()

        # Create streaming callback handler
        streaming_handler = StreamingCallbackHandler(event_queue)

        # Start execution in separate thread
        execution_thread = threading.Thread(
            target=self._execute_agent_with_callbacks,
            args=(question, streaming_handler, event_queue)
        )

        # Send initial event
        start_event = {
            "type": "execution_start",
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "query_id": f"query_{int(time.time())}"
        }
        yield f"data: {json.dumps(start_event)}\n\n"

        # Start execution
        execution_thread.start()

        # Stream events as they come
        execution_finished = False
        while not execution_finished:
            try:
                # Get event from queue (timeout to avoid blocking)
                event = event_queue.get(timeout=1.0)

                # Send event to client
                yield f"data: {json.dumps(event)}\n\n"

                # Check if execution is finished
                if event.get("type") in ["agent_finish", "agent_error"]:
                    execution_finished = True

            except Empty:
                # Send heartbeat to keep connection alive
                heartbeat = {
                    "type": "heartbeat",
                    "timestamp": datetime.now().isoformat()
                }
                yield f"data: {json.dumps(heartbeat)}\n\n"

                # Check if thread is still alive
                if not execution_thread.is_alive():
                    break

        # Wait for thread to finish
        execution_thread.join(timeout=5.0)

        # Send completion event
        completion_event = {
            "type": "execution_complete",
            "timestamp": datetime.now().isoformat()
        }
        yield f"data: {json.dumps(completion_event)}\n\n"

    def _execute_agent_with_callbacks(self, question: str, streaming_handler: StreamingCallbackHandler,
                                      event_queue: Queue) -> None:
        """Execute the agent with streaming callbacks."""
        try:
            self._total_queries += 1
            start_time = time.time()

            # Execute agent with callback
            result = self.agent_executor.invoke(
                {"input": question},
                config={"callbacks": [streaming_handler]}
            )

            end_time = time.time()
            execution_time = end_time - start_time

            # Send execution summary
            summary_event = {
                "type": "execution_summary",
                "timestamp": datetime.now().isoformat(),
                "execution_time": round(execution_time, 2),
                "success": True
            }
            event_queue.put(summary_event)

            self._successful_queries += 1

        except Exception as e:
            logger.error(f"Agent execution error: {e}")

            error_event = {
                "type": "agent_error",
                "timestamp": datetime.now().isoformat(),
                "error": {
                    "message": str(e),
                    "type": type(e).__name__
                }
            }
            event_queue.put(error_event)

            self._failed_queries += 1

    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get usage statistics."""
        success_rate = (
            (self._successful_queries / self._total_queries * 100)
            if self._total_queries > 0 else 0
        )

        return {
            "total_queries": self._total_queries,
            "successful_queries": self._successful_queries,
            "failed_queries": self._failed_queries,
            "success_rate_percent": round(success_rate, 2)
        }

    def get_agent_status(self) -> Dict[str, Any]:
        """Get agent status information."""
        return {
            "initialized": self.agent_executor is not None,
            "streaming_enabled": True,
            "llm_service_status": self.llm_service.get_health_status(),
            "database_service_status": self.database_service.get_health_status(),
            "agent_configuration": {
                "agent_type": self.config.AGENT_TYPE,
                "max_iterations": self.config.AGENT_MAX_ITERATIONS,
                "max_execution_time": self.config.AGENT_MAX_EXECUTION_TIME,
                "verbose": self.config.AGENT_VERBOSE
            },
            "statistics": self.get_usage_statistics(),
            "available_tables": list(self.sql_database.get_usable_table_names()) if self.sql_database else []
        }


def create_streaming_agent_service(custom_config: Optional[Config] = None,
                                   custom_llm_service: Optional[LLMService] = None,
                                   database_service: Optional[DatabaseService] = None) -> StreamingAgentService:
    """Factory function to create a streaming agent service instance."""
    if custom_config is None:
        from backend.app.config import get_config
        custom_config = get_config()

    if custom_llm_service is None:
        from backend.app.services.llm_service import create_llm_service
        custom_llm_service = create_llm_service(custom_config)

    if database_service is None:
        from backend.app.services.database_service import create_database_service
        database_service = create_database_service(custom_config)

    return StreamingAgentService(custom_config, custom_llm_service, database_service)
