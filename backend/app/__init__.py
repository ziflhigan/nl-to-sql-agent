"""
Flask Application Factory for NL-to-SQL Agent

This module implements the Flask application factory pattern, providing
a clean way to create and configure the Flask application with all
necessary extensions, blueprints, and error handlers.

Features:
- Application factory pattern for flexible instantiation
- Configuration loading and validation
- Extension initialization (CORS, logging)
- Blueprint registration with URL prefixes
- Global error handlers for consistent API responses
- Application lifecycle management
- Health monitoring integration

Usage:
    from app import create_app

    app = create_app()
    app.run(debug=True)
"""

import atexit
import logging
from typing import Optional, Dict, Any

from flask import Flask, jsonify, request
from flask_cors import CORS

from backend.app.config import Config, get_config, ConfigurationError
from backend.app.services.agent_service import create_agent_service, AgentError
from backend.app.services.database_service import create_database_service, DatabaseError
from backend.app.services.llm_service import create_llm_service, LLMError
from backend.app.utils.logger import get_logger

# Initialize logger for this module
logger = get_logger(__name__)


class ApplicationError(Exception):
    """Custom exception for application-level errors."""
    pass


def create_app(config_class: Optional[Config] = None, testing: bool = False) -> Flask:
    """
    Application factory function that creates and configures Flask application.

    Args:
        config_class: Optional configuration class instance
        testing: Whether to configure for testing environment

    Returns:
        Configured Flask application instance

    Raises:
        ApplicationError: If application creation fails
    """
    try:
        logger.info("Creating Flask application")

        # Create Flask app instance
        app = Flask(__name__)

        # Load and validate configuration
        if config_class is None:
            config_class = get_config()

        app.config.from_object(config_class)

        # Store config reference for easy access
        app.config_instance = config_class

        # Configure for testing if specified
        if testing:
            app.config['TESTING'] = True
            logger.info("Application configured for testing")

        # Initialize extensions
        _initialize_extensions(app)

        # Initialize services (stored in app context for access across requests)
        _initialize_services(app)

        # Register blueprints
        _register_blueprints(app)

        # Register error handlers
        _register_error_handlers(app)

        # Register application lifecycle handlers
        _register_lifecycle_handlers(app)

        # Log application creation success
        logger.info(f"Flask application created successfully (env: {config_class.FLASK_ENV})")

        return app

    except Exception as e:
        error_msg = f"Failed to create Flask application: {e}"
        logger.error(error_msg)
        raise ApplicationError(error_msg) from e


def _initialize_extensions(app: Flask) -> None:
    """
    Initialize Flask extensions.

    Args:
        app: Flask application instance
    """
    try:
        logger.info("Initializing Flask extensions")

        # Initialize CORS
        cors_origins = app.config_instance.CORS_ORIGINS
        CORS(app,
             resources={
                 r"/api/*": {
                     "origins": cors_origins,
                     "methods": ["GET", "POST", "OPTIONS"],
                     "allow_headers": ["Content-Type", "Authorization"]
                 }
             },
             supports_credentials=False)

        logger.info(f"CORS initialized with origins: {cors_origins}")

        # Configure Flask's built-in logger to use our logging system
        _configure_flask_logging(app)

        logger.info("Flask extensions initialized successfully")

    except Exception as e:
        error_msg = f"Failed to initialize extensions: {e}"
        logger.error(error_msg)
        raise ApplicationError(error_msg) from e


def _configure_flask_logging(app: Flask) -> None:
    """Configure Flask's logging to integrate with our logging system."""
    # Disable Flask's default logging to avoid duplication
    if not app.config.get('TESTING'):
        # Get Flask's logger
        flask_logger = logging.getLogger('werkzeug')

        # Set level based on debug mode
        if app.config_instance.FLASK_DEBUG:
            flask_logger.setLevel(logging.INFO)
        else:
            flask_logger.setLevel(logging.WARNING)


def _initialize_services(app: Flask) -> None:
    """
    Initialize application services and store in app context.

    Args:
        app: Flask application instance
    """
    try:
        logger.info("Initializing application services")

        config = app.config_instance

        # Create services
        logger.info("Creating database service")
        database_service = create_database_service(config)

        logger.info("Creating LLM service")
        llm_service = create_llm_service(config)

        logger.info("Creating agent service")
        agent_service = create_agent_service(config, llm_service, database_service)

        # Store services in app context for access in routes
        app.database_service = database_service
        app.llm_service = llm_service
        app.agent_service = agent_service

        # Validate all services are healthy
        _validate_services_health(app)

        logger.info("Application services initialized successfully")

    except Exception as e:
        error_msg = f"Failed to initialize services: {e}"
        logger.error(error_msg)
        raise ApplicationError(error_msg) from e


def _validate_services_health(app: Flask) -> None:
    """Validate that all services are healthy during startup."""
    try:
        logger.info("Validating services health")

        # Test database service
        if not app.database_service.test_connection():
            raise ApplicationError("Database service health check failed")

        # Test LLM service
        if not app.llm_service.test_connection():
            raise ApplicationError("LLM service health check failed")

        # Agent service health is validated during its initialization
        agent_status = app.agent_service.get_agent_status()
        if not agent_status.get('initialized', False):
            raise ApplicationError("Agent service initialization failed")

        logger.info("All services health validation passed")

    except Exception as e:
        error_msg = f"Services health validation failed: {e}"
        logger.error(error_msg)
        raise ApplicationError(error_msg) from e


def _register_blueprints(app: Flask) -> None:
    """
    Register Flask blueprints with URL prefixes.

    Args:
        app: Flask application instance
    """
    try:
        logger.info("Registering Flask blueprints")

        # Import and register API blueprint
        from backend.app.api import api_bp
        app.register_blueprint(api_bp, url_prefix='/api/v1')

        logger.info("API blueprint registered with prefix: /api/v1")

        # Register root route for basic application info
        @app.route('/')
        def root():
            """Root endpoint with basic application information."""
            return jsonify({
                "name": "NL-to-SQL Agent API",
                "version": "1.0.0",
                "status": "running",
                "environment": app.config_instance.FLASK_ENV,
                "endpoints": {
                    "health": "/api/v1/health",
                    "status": "/api/v1/status",
                    "chat": "/api/v1/chat"
                },
                "documentation": "API for natural language to SQL query conversion"
            })

        logger.info("Flask blueprints registered successfully")

    except Exception as e:
        error_msg = f"Failed to register blueprints: {e}"
        logger.error(error_msg)
        raise ApplicationError(error_msg) from e


def _register_error_handlers(app: Flask) -> None:
    """
    Register global error handlers for consistent API responses.

    Args:
        app: Flask application instance
    """
    try:
        logger.info("Registering error handlers")

        @app.errorhandler(400)
        def bad_request(error):
            """Handle bad request errors."""
            logger.warning(f"Bad request: {request.url} - {error}")
            return jsonify({
                "data": None,
                "error": {
                    "code": 400,
                    "message": "Bad request. Please check your input and try again.",
                    "type": "validation_error"
                }
            }), 400

        @app.errorhandler(404)
        def not_found(error):
            """Handle not found errors."""
            logger.warning(f"Not found: {request.url}")
            return jsonify({
                "data": None,
                "error": {
                    "code": 404,
                    "message": "Endpoint not found. Please check the URL and try again.",
                    "type": "not_found"
                }
            }), 404

        @app.errorhandler(405)
        def method_not_allowed(error):
            """Handle method not allowed errors."""
            logger.warning(f"Method not allowed: {request.method} {request.url}")
            return jsonify({
                "data": None,
                "error": {
                    "code": 405,
                    "message": f"Method {request.method} not allowed for this endpoint.",
                    "type": "method_not_allowed"
                }
            }), 405

        @app.errorhandler(500)
        def internal_server_error(error):
            """Handle internal server errors."""
            logger.error(f"Internal server error: {request.url} - {error}")
            return jsonify({
                "data": None,
                "error": {
                    "code": 500,
                    "message": "An internal server error occurred. Please try again later.",
                    "type": "internal_error"
                }
            }), 500

        # Service-specific error handlers
        @app.errorhandler(DatabaseError)
        def handle_database_error(error):
            """Handle database service errors."""
            logger.error(f"Database error: {error}")
            return jsonify({
                "data": None,
                "error": {
                    "code": 503,
                    "message": "Database service error. Please try again later.",
                    "type": "database_error"
                }
            }), 503

        @app.errorhandler(LLMError)
        def handle_llm_error(error):
            """Handle LLM service errors."""
            logger.error(f"LLM error: {error}")
            return jsonify({
                "data": None,
                "error": {
                    "code": 503,
                    "message": "AI service error. Please try again later.",
                    "type": "llm_error"
                }
            }), 503

        @app.errorhandler(AgentError)
        def handle_agent_error(error):
            """Handle agent service errors."""
            logger.error(f"Agent error: {error}")
            return jsonify({
                "data": None,
                "error": {
                    "code": 503,
                    "message": "Agent service error. Please try again later.",
                    "type": "agent_error"
                }
            }), 503

        @app.errorhandler(ConfigurationError)
        def handle_configuration_error(error):
            """Handle configuration errors."""
            logger.error(f"Configuration error: {error}")
            return jsonify({
                "data": None,
                "error": {
                    "code": 500,
                    "message": "Application configuration error.",
                    "type": "configuration_error"
                }
            }), 500

        logger.info("Error handlers registered successfully")

    except Exception as e:
        error_msg = f"Failed to register error handlers: {e}"
        logger.error(error_msg)
        raise ApplicationError(error_msg) from e


def _register_lifecycle_handlers(app: Flask) -> None:
    """
    Register application lifecycle handlers for cleanup.

    Args:
        app: Flask application instance
    """
    try:
        logger.info("Registering lifecycle handlers")

        def cleanup_services():
            """Clean up application services on shutdown."""
            try:
                logger.info("Cleaning up application services")

                if hasattr(app, 'agent_service') and app.agent_service:
                    app.agent_service.close()

                if hasattr(app, 'llm_service') and app.llm_service:
                    app.llm_service.close()

                if hasattr(app, 'database_service') and app.database_service:
                    app.database_service.close()

                logger.info("Application services cleaned up successfully")

            except Exception as e:
                logger.error(f"Error during service cleanup: {e}")

        # Register cleanup function to run on application shutdown
        atexit.register(cleanup_services)

        # Flask teardown handler
        @app.teardown_appcontext
        def close_services(error):
            """Handle per-request cleanup if needed."""
            if error:
                logger.error(f"Request error: {error}")

        logger.info("Lifecycle handlers registered successfully")

    except Exception as e:
        error_msg = f"Failed to register lifecycle handlers: {e}"
        logger.error(error_msg)
        raise ApplicationError(error_msg) from e


def get_services_from_app(app: Flask) -> tuple:
    """
    Get services from Flask app context.

    Args:
        app: Flask application instance

    Returns:
        Tuple of (database_service, llm_service, agent_service)
    """
    return (
        getattr(app, 'database_service', None),
        getattr(app, 'llm_service', None),
        getattr(app, 'agent_service', None)
    )


def validate_app_health(app: Flask) -> Dict[str, Any]:
    """
    Validate application health by checking all services.

    Args:
        app: Flask application instance

    Returns:
        Dictionary with health status
    """
    try:
        db_service, llm_service, agent_service = get_services_from_app(app)

        health_status = {
            "application": {
                "status": "healthy",
                "environment": app.config_instance.FLASK_ENV,
                "debug_mode": app.config_instance.FLASK_DEBUG
            },
            "services": {},
            "overall_healthy": True
        }

        # Check each service
        if db_service:
            db_health = db_service.get_health_status()
            health_status["services"]["database"] = db_health
            if not db_health.get("connected", False):
                health_status["overall_healthy"] = False

        if llm_service:
            llm_health = llm_service.get_health_status()
            health_status["services"]["llm"] = llm_health
            if not llm_health.get("connected", False):
                health_status["overall_healthy"] = False

        if agent_service:
            agent_status = agent_service.get_agent_status()
            health_status["services"]["agent"] = agent_status
            if not agent_status.get("initialized", False):
                health_status["overall_healthy"] = False

        if not health_status["overall_healthy"]:
            health_status["application"]["status"] = "degraded"

        return health_status

    except Exception as e:
        logger.error(f"Health validation error: {e}")
        return {
            "application": {"status": "unhealthy"},
            "services": {},
            "overall_healthy": False,
            "error": str(e)
        }
