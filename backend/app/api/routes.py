"""
Streaming API Routes for Real-time ReAct Loop Processing

This module provides Server-Sent Events (SSE) endpoints for streaming
the agent's thought process in real-time.
"""

import time
from datetime import datetime
from typing import Dict, Any

from flask import request, jsonify, current_app, Response
from werkzeug.exceptions import BadRequest

from backend.app.utils.logger import get_logger, log_function_call, log_exception
from . import api_bp

# Initialize logger for this module
logger = get_logger(__name__)

# Request size limit (1MB)
MAX_REQUEST_SIZE = 1024 * 1024
MAX_QUESTION_LENGTH = 1000
MIN_QUESTION_LENGTH = 3


def get_request_id() -> str:
    """Generate a unique request ID for tracking."""
    return f"req_{int(time.time() * 1000)}"


def validate_streaming_request() -> Dict[str, Any]:
    """
    Validate and parse streaming request.

    Returns:
        Parsed request data

    Raises:
        BadRequest: If request is invalid
    """
    # For streaming, we can accept both JSON and form data
    if request.is_json:
        try:
            data = request.get_json(force=True)
            if data is None:
                raise BadRequest("Request body must contain valid JSON")
            return data
        except Exception as e:
            logger.warning(f"Invalid JSON in streaming request: {e}")
            raise BadRequest("Invalid JSON format")
    else:
        # Handle form data or query parameters
        question = request.form.get('question') or request.args.get('question')
        if not question:
            raise BadRequest("Question parameter is required")

        return {
            'question': question,
            'include_intermediate_steps': True  # Always true for streaming
        }


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


@api_bp.route('/chat/stream', methods=['POST', 'GET'])
def chat_stream():
    """
    Real-time streaming chat endpoint using Server-Sent Events (SSE).

    This endpoint streams the agent's thought process in real-time as it executes,
    providing immediate feedback to users about what the AI is thinking and doing.

    Request Methods:
        POST: Send question in JSON body
        GET: Send question as query parameter (for easier testing)

    Request Body (POST):
        {
            "question": "string (required)"
        }

    Query Parameters (GET):
        ?question=<your_question>

    Response:
        Server-Sent Events stream with the following event types:
        - execution_start: Query processing begins
        - agent_action: AI takes an action (with thought process)
        - agent_observation: Result from the action
        - agent_finish: Final answer generated
        - agent_error: Error occurred
        - execution_summary: Execution completed
        - execution_complete: Stream ends
        - heartbeat: Keep-alive signal

    Headers:
        Content-Type: text/event-stream
        Cache-Control: no-cache
        Connection: keep-alive
        Access-Control-Allow-Origin: *
    """
    request_id = get_request_id()

    try:
        log_function_call("chat_stream", (), {"request_id": request_id})

        # Validate request
        try:
            data = validate_streaming_request()
        except BadRequest as e:
            logger.warning(f"Invalid streaming request: {e}")

            # For streaming, we need to return an error event
            def error_stream():
                yield (f"event: error\ndata: {{'type': 'error', "
                       f"'message': '{str(e)}', "
                       f"'request_id': '{request_id}'}}\n\n")

            return Response(
                error_stream(),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type'
                }
            )

        # Extract and validate question
        question = data.get('question', '')
        try:
            question = validate_question(question)
        except BadRequest as e:
            logger.warning(f"Invalid question in streaming request: {e}")

            def error_stream():
                yield (f"event: error\ndata: {{'type': 'validation_error', "
                       f"'message': '{str(e)}', "
                       f"'request_id': '{request_id}'}}\n\n")

            return Response(
                error_stream(),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type'
                }
            )

        # Get streaming agent service
        streaming_agent_service = getattr(current_app, 'streaming_agent_service', None)
        if not streaming_agent_service:
            logger.error("Streaming agent service not available")

            def error_stream():
                yield (f"event: error\ndata: {{'type': 'service_error', "
                       f"'message': 'Streaming service not available', "
                       f"'request_id': '{request_id}'}}\n\n")

            return Response(
                error_stream(),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type'
                }
            )

        # Log the streaming request
        question_preview = question[:100] + "..." if len(question) > 100 else question
        logger.info(f"Starting streaming chat for question: {question_preview}")

        # Create the streaming response
        def generate_stream():
            try:
                for event_data in streaming_agent_service.stream_agent_execution(question):
                    yield event_data

            except Exception as exc:
                log_exception(logger, exc, "streaming chat execution")
                error_event = (f"event: error\ndata: {{'type': 'execution_error', "
                               f"'message': 'Streaming execution failed', "
                               f"'request_id': '{request_id}'}}\n\n")
                yield error_event

        return Response(
            generate_stream(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'X-Request-ID': request_id
            }
        )

    except Exception as e:
        log_exception(logger, e, "chat_stream endpoint")

        def error_stream():
            yield (f"event: error\ndata: {{'type': 'internal_error', "
                   f"'message': 'Unexpected error occurred', "
                   f"'request_id': '{request_id}'}}\n\n")

        return Response(
            error_stream(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        )


@api_bp.route('/chat', methods=['POST'])
def chat():
    """
    Traditional chat endpoint (non-streaming) for backward compatibility.

    This endpoint works the same as before, returning all results at once
    after the agent has finished execution.
    """
    request_id = get_request_id()

    try:
        log_function_call("chat", (), {"request_id": request_id})
        start_time = time.time()

        # Validate request format
        if not request.is_json:
            return jsonify({
                "data": None,
                "error": {
                    "code": 400,
                    "message": "Content-Type must be application/json",
                    "type": "validation_error"
                },
                "success": False,
                "request_id": request_id
            }), 400

        try:
            data = request.get_json(force=True)
            if data is None:
                raise BadRequest("Request body must contain valid JSON")
        except Exception as e:
            logger.warning(f"Invalid JSON in request: {e}")
            return jsonify({
                "data": None,
                "error": {
                    "code": 400,
                    "message": "Invalid JSON format",
                    "type": "validation_error"
                },
                "success": False,
                "request_id": request_id
            }), 400

        # Extract and validate question
        question = data.get('question', '')
        try:
            question = validate_question(question)
        except BadRequest as e:
            logger.warning(f"Invalid question: {e}")
            return jsonify({
                "data": None,
                "error": {
                    "code": 400,
                    "message": str(e),
                    "type": "validation_error"
                },
                "success": False,
                "request_id": request_id
            }), 400

        # For non-streaming, we can use either the regular or streaming agent service
        agent_service = getattr(current_app, 'agent_service', None)
        if not agent_service:
            logger.error("Agent service not available")
            return jsonify({
                "data": None,
                "error": {
                    "code": 503,
                    "message": "Agent service not available",
                    "type": "service_error"
                },
                "success": False,
                "request_id": request_id
            }), 503

        # Extract optional parameters
        include_intermediate_steps = data.get('include_intermediate_steps', True)

        # Log the incoming question
        question_preview = question[:100] + "..." if len(question) > 100 else question
        logger.info(f"Processing non-streaming chat request: {question_preview}")

        # Execute agent query (traditional way)
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

            result["timing"] = {
                "agent_execution_time": result.get('execution_time', 0),
                "total_response_time": round(total_time, 2),
                "processing_overhead": round(total_time - result.get('execution_time', 0), 2)
            }

            logger.info(f"Non-streaming chat request completed successfully "
                        f"(agent_time: {result.get('execution_time', 0)}s, "
                        f"total_time: {total_time:.2f}s)")

            return jsonify({
                "data": result,
                "error": None,
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id
            }), 200

        except Exception as e:
            logger.error(f"Agent execution error: {e}")
            return jsonify({
                "data": None,
                "error": {
                    "code": 500,
                    "message": "Agent execution failed",
                    "type": "execution_error"
                },
                "success": False,
                "request_id": request_id
            }), 500

    except Exception as e:
        log_exception(logger, e, "chat endpoint")
        return jsonify({
            "data": None,
            "error": {
                "code": 500,
                "message": "An unexpected error occurred",
                "type": "internal_error"
            },
            "success": False,
            "request_id": request_id
        }), 500


@api_bp.route('/health', methods=['GET'])
def health_check():
    """
    Basic health check endpoint.
    """
    try:
        log_function_call("health_check")

        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "environment": current_app.config_instance.FLASK_ENV,
            "features": {
                "streaming": True,
                "real_time_react": True,
                "traditional_chat": True
            }
        }

        logger.debug("Health check completed successfully")
        return jsonify({
            "data": health_data,
            "error": None,
            "success": True,
            "timestamp": datetime.now().isoformat()
        }), 200

    except Exception as e:
        log_exception(logger, e, "health_check")
        return jsonify({
            "data": None,
            "error": {
                "code": 500,
                "message": "Health check failed",
                "type": "health_error"
            },
            "success": False,
            "timestamp": datetime.now().isoformat()
        }), 500


@api_bp.route('/status', methods=['GET'])
def status_check():
    """
    Comprehensive status endpoint with streaming capabilities info.
    """
    try:
        request_id = get_request_id()
        log_function_call("status_check", (), {"request_id": request_id})

        start_time = time.time()

        # Get services from app context
        database_service = getattr(current_app, 'database_service', None)
        llm_service = getattr(current_app, 'llm_service', None)
        agent_service = getattr(current_app, 'agent_service', None)
        streaming_agent_service = getattr(current_app, 'streaming_agent_service', None)

        # Collect status from all services
        status_data = {
            "application": {
                "status": "running",
                "environment": current_app.config_instance.FLASK_ENV,
                "debug_mode": current_app.config_instance.FLASK_DEBUG,
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0"
            },
            "services": {},
            "overall_healthy": True,
            "capabilities": {
                "real_time_streaming": streaming_agent_service is not None,
                "traditional_chat": agent_service is not None,
                "react_loop_processing": True,
                "sql_query_formatting": True,
                "thought_extraction": True,
                "server_sent_events": True
            }
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

        # Traditional agent service status
        if agent_service:
            try:
                agent_status = agent_service.get_agent_status()
                agent_stats = agent_service.get_usage_statistics()
                status_data["services"]["agent"] = {
                    "type": "traditional",
                    "status": agent_status,
                    "statistics": agent_stats
                }
                if not agent_status.get("initialized", False):
                    status_data["overall_healthy"] = False
            except Exception as e:
                log_exception(logger, e, "agent status check")
                status_data["services"]["agent"] = {"error": "Status check failed"}
                status_data["overall_healthy"] = False

        # Streaming agent service status
        if streaming_agent_service:
            try:
                streaming_status = streaming_agent_service.get_agent_status()
                streaming_stats = streaming_agent_service.get_usage_statistics()
                status_data["services"]["streaming_agent"] = {
                    "type": "streaming",
                    "status": streaming_status,
                    "statistics": streaming_stats
                }
                if not streaming_status.get("initialized", False):
                    status_data["overall_healthy"] = False
            except Exception as e:
                log_exception(logger, e, "streaming agent status check")
                status_data["services"]["streaming_agent"] = {"error": "Status check failed"}
                status_data["overall_healthy"] = False

        # Update application status based on service health
        if not status_data["overall_healthy"]:
            status_data["application"]["status"] = "degraded"

        # Add response metadata
        end_time = time.time()
        status_data["response_time"] = round(end_time - start_time, 3)

        logger.info(f"Status check completed (overall_healthy: {status_data['overall_healthy']}, "
                    f"response_time: {status_data['response_time']}s)")

        return jsonify({
            "data": status_data,
            "error": None,
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id
        }), 200

    except Exception as e:
        log_exception(logger, e, "status_check")
        return jsonify({
            "data": None,
            "error": {
                "code": 500,
                "message": "Status check failed",
                "type": "status_error"
            },
            "success": False,
            "request_id": request_id
        }), 500


# CORS preflight handler for streaming endpoint
@api_bp.route('/chat/stream', methods=['OPTIONS'])
def chat_stream_options():
    """Handle CORS preflight requests for the streaming endpoint."""
    response = Response()
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Max-Age'] = '86400'
    return response
