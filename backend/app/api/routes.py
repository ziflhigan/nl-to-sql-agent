"""
API Routes for NL-to-SQL Agent

This module implements the Flask API routes that provide HTTP endpoints
for the NL-to-SQL agent functionality. All routes follow RESTful principles
and return consistent JSON responses.

Endpoints:
- POST /api/v1/chat - Process natural language queries
- GET /api/v1/health - Basic application health check
- GET /api/v1/status - Comprehensive service status and statistics

Response Format:
All endpoints return JSON in the following format:
{
    "data": <response_data> | null,
    "error": null | {
        "code": <http_status_code>,
        "message": "<user_friendly_message>",
        "type": "<error_type>"
    }
}

Rate Limiting and Security:
- Input validation on all endpoints
- SQL injection prevention
- Request size limits
- Error message sanitization
"""

import time
from typing import Dict, Any, Optional
from datetime import datetime
from flask import request, jsonify, current_app, g
from werkzeug.exceptions import BadRequest

from . import api_bp
from backend.app.utils.logger import get_logger, log_function_call, log_exception
from .. import DatabaseError
from ..services.agent_service import AgentTimeoutError, AgentExecutionError, AgentError
from ..services.llm_service import LLMRateLimitError, LLMTimeoutError, LLMError

# Initialize logger for this module
logger = get_logger(__name__)

# Request size limit (1MB)
MAX_REQUEST_SIZE = 1024 * 1024

# Rate limiting constants
MAX_QUESTION_LENGTH = 1000
MIN_QUESTION_LENGTH = 3


def get_request_id() -> str:
    """Generate a unique request ID for tracking."""
    return f"req_{int(time.time() * 1000)}"


def validate_json_request() -> Dict[str, Any]:
    """
    Validate and parse JSON request body.

    Returns:
        Parsed JSON data

    Raises:
        BadRequest: If request is invalid
    """
    if not request.is_json:
        raise BadRequest("Content-Type must be application/json")

    if request.content_length and request.content_length > MAX_REQUEST_SIZE:
        raise BadRequest(f"Request size too large (max: {MAX_REQUEST_SIZE} bytes)")

    try:
        data = request.get_json(force=True)
        if data is None:
            raise BadRequest("Request body must contain valid JSON")
        return data

    except Exception as e:
        logger.warning(f"Invalid JSON in request: {e}")
        raise BadRequest("Invalid JSON format")


def validate_question(question: str) -> str:
    """
    Validate and sanitize user question.

    Args:
        question: Raw question from user

    Returns:
        Sanitized question

    Raises:
        BadRequest: If question is invalid
    """
    if not question or not isinstance(question, str):
        raise BadRequest("Question must be a non-empty string")

    question = question.strip()

    if len(question) < MIN_QUESTION_LENGTH:
        raise BadRequest(f"Question too short (minimum: {MIN_QUESTION_LENGTH} characters)")

    if len(question) > MAX_QUESTION_LENGTH:
        raise BadRequest(f"Question too long (maximum: {MAX_QUESTION_LENGTH} characters)")

    # Basic sanitization - remove potentially harmful characters
    forbidden_chars = ['\x00', '\x01', '\x02', '\x03', '\x04', '\x05']
    for char in forbidden_chars:
        if char in question:
            raise BadRequest("Question contains invalid characters")

    return question


def create_success_response(data: Any, request_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Create standardized success response.

    Args:
        data: Response data
        request_id: Optional request ID for tracking

    Returns:
        Formatted success response
    """
    response = {
        "data": data,
        "error": None
    }

    if request_id:
        response["request_id"] = request_id

    return response


def create_error_response(message: str, error_type: str = "error",
                          status_code: int = 400, request_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Create standardized error response.

    Args:
        message: Error message for user
        error_type: Type of error for categorization
        status_code: HTTP status code
        request_id: Optional request ID for tracking

    Returns:
        Formatted error response
    """
    response = {
        "data": None,
        "error": {
            "code": status_code,
            "message": message,
            "type": error_type
        }
    }

    if request_id:
        response["request_id"] = request_id

    return response


@api_bp.route('/health', methods=['GET'])
def health_check():
    """
    Basic health check endpoint.

    Returns simple status to verify the API is running.
    Used by load balancers and monitoring systems for quick health checks.

    Returns:
        JSON response with basic health status
    """
    try:
        log_function_call("health_check")

        # Basic health check - just verify app is responding
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "environment": current_app.config_instance.FLASK_ENV
        }

        logger.debug("Health check completed successfully")
        return jsonify(create_success_response(health_data)), 200

    except Exception as e:
        log_exception(logger, e, "health_check")
        return jsonify(create_error_response(
            "Health check failed",
            "health_error",
            500
        )), 500


@api_bp.route('/status', methods=['GET'])
def status_check():
    """
    Comprehensive status endpoint.

    Returns detailed status information about all services,
    including health, statistics, and configuration.
    Used for monitoring, debugging, and administrative purposes.

    Returns:
        JSON response with comprehensive service status
    """
    try:
        request_id = get_request_id()
        log_function_call("status_check", (), {"request_id": request_id})

        start_time = time.time()

        # Get services from app context
        database_service = getattr(current_app, 'database_service', None)
        llm_service = getattr(current_app, 'llm_service', None)
        agent_service = getattr(current_app, 'agent_service', None)

        # Collect status from all services
        status_data = {
            "application": {
                "status": "running",
                "environment": current_app.config_instance.FLASK_ENV,
                "debug_mode": current_app.config_instance.FLASK_DEBUG,
                "timestamp": datetime.now().isoformat()
            },
            "services": {},
            "overall_healthy": True
        }

        # Database service status
        if database_service:
            try:
                db_status = database_service.get_health_status()
                db_info = database_service.get_database_info()
                status_data["services"]["database"] = {
                    "health": db_status,
                    "info": db_info
                }
                if not db_status.get("connected", False):
                    status_data["overall_healthy"] = False
            except Exception as e:
                log_exception(logger, e, "database status check")
                status_data["services"]["database"] = {"error": "Status check failed"}
                status_data["overall_healthy"] = False

        # LLM service status
        if llm_service:
            try:
                llm_status = llm_service.get_health_status()
                llm_info = llm_service.get_model_info()
                llm_stats = llm_service.get_usage_statistics()
                status_data["services"]["llm"] = {
                    "health": llm_status,
                    "info": llm_info,
                    "statistics": llm_stats
                }
                if not llm_status.get("connected", False):
                    status_data["overall_healthy"] = False
            except Exception as e:
                log_exception(logger, e, "LLM status check")
                status_data["services"]["llm"] = {"error": "Status check failed"}
                status_data["overall_healthy"] = False

        # Agent service status
        if agent_service:
            try:
                agent_status = agent_service.get_agent_status()
                agent_stats = agent_service.get_usage_statistics()
                agent_db_info = agent_service.get_database_info()
                status_data["services"]["agent"] = {
                    "status": agent_status,
                    "statistics": agent_stats,
                    "database_info": agent_db_info
                }
                if not agent_status.get("initialized", False):
                    status_data["overall_healthy"] = False
            except Exception as e:
                log_exception(logger, e, "agent status check")
                status_data["services"]["agent"] = {"error": "Status check failed"}
                status_data["overall_healthy"] = False

        # Update application status based on service health
        if not status_data["overall_healthy"]:
            status_data["application"]["status"] = "degraded"

        # Add response metadata
        end_time = time.time()
        status_data["response_time"] = round(end_time - start_time, 3)

        logger.info(f"Status check completed (overall_healthy: {status_data['overall_healthy']}, "
                    f"response_time: {status_data['response_time']}s)")

        return jsonify(create_success_response(status_data, request_id)), 200

    except Exception as e:
        log_exception(logger, e, "status_check")
        return jsonify(create_error_response(
            "Status check failed",
            "status_error",
            500,
            request_id
        )), 500


@api_bp.route('/chat', methods=['POST'])
def chat():
    """
    Main chat endpoint for natural language to SQL queries.

    Processes user questions in natural language and returns SQL query results
    along with natural language explanations.

    Request Body:
        {
            "question": "string",
            "include_intermediate_steps": boolean (optional, default: true)
        }

    Response:
        {
            "data": {
                "answer": "string",
                "execution_time": float,
                "timestamp": "string",
                "query_id": "string",
                "intermediate_steps": [...] (if requested),
                "metadata": {...}
            },
            "error": null
        }

    Returns:
        JSON response with query results or error information
    """
    request_id = get_request_id()

    try:
        log_function_call("chat", (), {"request_id": request_id})
        start_time = time.time()

        # Validate request format
        try:
            data = validate_json_request()
        except BadRequest as e:
            logger.warning(f"Invalid chat request format: {e}")
            return jsonify(create_error_response(
                str(e),
                "validation_error",
                400,
                request_id
            )), 400

        # Extract and validate question
        question = data.get('question', '')
        try:
            question = validate_question(question)
        except BadRequest as e:
            logger.warning(f"Invalid question: {e}")
            return jsonify(create_error_response(
                str(e),
                "validation_error",
                400,
                request_id
            )), 400

        # Extract optional parameters
        include_intermediate_steps = data.get('include_intermediate_steps', True)

        # Get agent service
        agent_service = getattr(current_app, 'agent_service', None)
        if not agent_service:
            logger.error("Agent service not available")
            return jsonify(create_error_response(
                "Agent service not available",
                "service_error",
                503,
                request_id
            )), 503

        # Log the incoming question (truncated for security)
        question_preview = question[:100] + "..." if len(question) > 100 else question
        logger.info(f"Processing chat request: {question_preview}")

        # Execute agent query
        try:
            result = agent_service.invoke_agent(
                question=question,
                include_intermediate_steps=include_intermediate_steps
            )

            # Add request tracking information
            result["request_id"] = request_id
            result["question"] = question

            # Calculate total response time
            end_time = time.time()
            total_time = end_time - start_time

            logger.info(f"Chat request completed successfully "
                        f"(agent_time: {result.get('execution_time', 0)}s, "
                        f"total_time: {total_time:.2f}s)")

            return jsonify(create_success_response(result, request_id)), 200

        except AgentTimeoutError as e:
            logger.warning(f"Agent timeout: {e}")
            return jsonify(create_error_response(
                "Query took too long to process. Please try a simpler question.",
                "timeout_error",
                408,
                request_id
            )), 408

        except LLMRateLimitError as e:
            logger.warning(f"LLM rate limit: {e}")
            return jsonify(create_error_response(
                "AI service rate limit reached. Please try again in a few minutes.",
                "rate_limit_error",
                429,
                request_id
            )), 429

        except LLMTimeoutError as e:
            logger.warning(f"LLM timeout: {e}")
            return jsonify(create_error_response(
                "AI service timeout. Please try again later.",
                "timeout_error",
                408,
                request_id
            )), 408

        except AgentExecutionError as e:
            logger.error(f"Agent execution error: {e}")
            return jsonify(create_error_response(
                "Unable to process your question. Please try rephrasing it.",
                "execution_error",
                422,
                request_id
            )), 422

        except DatabaseError as e:
            logger.error(f"Database error during chat: {e}")
            return jsonify(create_error_response(
                "Database service error. Please try again later.",
                "database_error",
                503,
                request_id
            )), 503

        except LLMError as e:
            logger.error(f"LLM error during chat: {e}")
            return jsonify(create_error_response(
                "AI service error. Please try again later.",
                "llm_error",
                503,
                request_id
            )), 503

        except AgentError as e:
            logger.error(f"Agent error during chat: {e}")
            return jsonify(create_error_response(
                "Agent service error. Please try again later.",
                "agent_error",
                503,
                request_id
            )), 503

    except Exception as e:
        log_exception(logger, e, "chat endpoint")
        return jsonify(create_error_response(
            "An unexpected error occurred. Please try again later.",
            "internal_error",
            500,
            request_id
        )), 500


@api_bp.route('/tables', methods=['GET'])
def get_tables():
    """
    Get information about available database tables.

    Returns list of tables and their basic schema information.
    Useful for understanding what data is available for querying.

    Returns:
        JSON response with table information
    """
    try:
        request_id = get_request_id()
        log_function_call("get_tables", (), {"request_id": request_id})

        # Get database service
        database_service = getattr(current_app, 'database_service', None)
        if not database_service:
            return jsonify(create_error_response(
                "Database service not available",
                "service_error",
                503,
                request_id
            )), 503

        # Get table information
        table_names = database_service.get_table_names()

        tables_info = {
            "total_tables": len(table_names),
            "table_names": table_names,
            "database_type": database_service.engine.dialect.name if database_service.engine else "unknown"
        }

        logger.info(f"Retrieved information for {len(table_names)} tables")
        return jsonify(create_success_response(tables_info, request_id)), 200

    except DatabaseError as e:
        log_exception(logger, e, "get_tables")
        return jsonify(create_error_response(
            "Unable to retrieve table information",
            "database_error",
            503,
            request_id
        )), 503

    except Exception as e:
        log_exception(logger, e, "get_tables")
        return jsonify(create_error_response(
            "Failed to retrieve table information",
            "internal_error",
            500,
            request_id
        )), 500


# Blueprint error handlers (specific to this blueprint)
@api_bp.errorhandler(413)
def payload_too_large(error):
    """Handle payload too large errors."""
    logger.warning("Request payload too large")
    return jsonify(create_error_response(
        "Request payload too large",
        "payload_error",
        413
    )), 413


@api_bp.errorhandler(429)
def rate_limit_exceeded(error):
    """Handle rate limit errors."""
    logger.warning("Rate limit exceeded")
    return jsonify(create_error_response(
        "Rate limit exceeded. Please try again later.",
        "rate_limit_error",
        429
    )), 429
