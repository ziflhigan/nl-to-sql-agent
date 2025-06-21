"""
Main Application Runner for NL-to-SQL Agent

This module serves as the entry point for the Flask application,
handling application creation, configuration, and server startup.

Features:
- Application initialization using factory pattern
- Environment-based configuration
- Development and production server setup
- Graceful error handling and logging
- Application lifecycle management

Usage:
    Development:
        python app.py

    Production (with Gunicorn):
        gunicorn -w 4 -b 0.0.0.0:5000 app:app

    Environment Variables:
        FLASK_ENV: development|production|testing
        FLASK_DEBUG: True|False
        FLASK_HOST: Host to bind to (default: 0.0.0.0)
        FLASK_PORT: Port to bind to (default: 5000)
"""

import signal
import sys
from typing import Optional

from backend.app import create_app, validate_app_health
from backend.app.config import get_config, ConfigurationError
from backend.app.utils.logger import get_logger, log_exception

# Initialize logger for this module
logger = get_logger(__name__)

# Global application instance
app: Optional[object] = None


def create_application() -> object:
    """
    Create and configure the Flask application.

    Returns:
        Configured Flask application instance

    Raises:
        SystemExit: If application creation fails
    """
    try:
        logger.info("Starting NL-to-SQL Agent application")

        # Load configuration
        custom_config = get_config()
        logger.info(f"Configuration loaded for environment: {custom_config.FLASK_ENV}")

        # Create Flask application
        flask_app = create_app(custom_config)

        # Validate application health
        app_health_status = validate_app_health(flask_app)
        if not app_health_status.get("overall_healthy", False):
            logger.warning("Application health check indicates issues:")
            for service, status in app_health_status.get("services", {}).items():
                if isinstance(status, dict) and not status.get("connected", True):
                    logger.warning(f"  - {service}: {status}")
        else:
            logger.info("Application health check passed - all services healthy")

        # Log application summary
        _log_application_summary(custom_config, app_health_status)

        return flask_app

    except ConfigurationError as err:
        logger.error(f"Configuration error: {err}")
        print(f"Configuration Error: {err}")
        print("Please check your .env file and ensure all required variables are set.")
        sys.exit(1)

    except Exception as err:
        log_exception(logger, err, "application creation")
        print(f"Failed to start application: {err}")
        sys.exit(1)


def _log_application_summary(custom_config, app_health_status):
    """Log application startup summary."""
    logger.info("=" * 60)
    logger.info("NL-to-SQL Agent Application Started")
    logger.info("=" * 60)
    logger.info(f"Environment: {custom_config.FLASK_ENV}")
    logger.info(f"Debug Mode: {custom_config.FLASK_DEBUG}")
    logger.info(f"Host: {custom_config.FLASK_HOST}")
    logger.info(f"Port: {custom_config.FLASK_PORT}")
    logger.info(f"LLM Model: {custom_config.GEMINI_MODEL_NAME}")
    logger.info(f"Database: {custom_config.DATABASE_URI.split('://')[0]}")
    logger.info(f"Overall Health: {'✓ Healthy' if app_health_status.get('overall_healthy') else '⚠ Issues detected'}")
    logger.info("=" * 60)
    logger.info("Available Endpoints:")
    logger.info("  GET  /                  - Application info")
    logger.info("  GET  /api/v1/health     - Health check")
    logger.info("  GET  /api/v1/status     - Service status")
    logger.info("  GET  /api/v1/tables     - Database tables")
    logger.info("  POST /api/v1/chat       - NL-to-SQL queries")
    logger.info("=" * 60)


def setup_signal_handlers(flask_app):
    """Set up signal handlers for graceful shutdown."""

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully")

        # Cleanup services
        try:
            if hasattr(flask_app, 'agent_service') and flask_app.agent_service:
                flask_app.agent_service.close()
            if hasattr(flask_app, 'llm_service') and flask_app.llm_service:
                flask_app.llm_service.close()
            if hasattr(flask_app, 'database_service') and flask_app.database_service:
                flask_app.database_service.close()
            logger.info("Services cleanup completed")
        except Exception as err:
            logger.error(f"Error during cleanup: {err}")

        sys.exit(0)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def run_development_server(flask_app):
    """
    Run the Flask development server.

    Args:
        flask_app: Flask application instance
    """
    try:
        custom_config = flask_app.config_instance

        logger.info("Starting development server")
        logger.info(f"Server will be available at: http://{custom_config.FLASK_HOST}:{custom_config.FLASK_PORT}")

        # Set up signal handlers
        setup_signal_handlers(flask_app)

        # Run the development server
        flask_app.run(
            host=custom_config.FLASK_HOST,
            port=custom_config.FLASK_PORT,
            debug=custom_config.FLASK_DEBUG,
            use_reloader=False,  # Disable reloader to prevent duplicate initialization
            threaded=True  # Enable threading for concurrent requests
        )

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as err:
        log_exception(logger, err, "development server")
        raise


def run_production_server(flask_app):
    """
    Run the application with production WSGI server.

    Args:
        flask_app: Flask application instance
    """
    logger.info("Production server mode - use a WSGI server like Gunicorn")
    logger.info("Example: gunicorn -w 4 -b 0.0.0.0:5000 app:app")

    # In production, this will be called by the WSGI server
    return flask_app


def main():
    """Main application entry point."""
    try:
        # Create application
        global app
        app = create_application()

        # Determine how to run based on environment
        custom_config = app.config_instance

        if custom_config.FLASK_ENV == 'development':
            run_development_server(app)
        else:
            # For production, just return the app (WSGI server will handle it)
            return app

    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as err:
        log_exception(logger, err, "main")
        sys.exit(1)


def health_check():
    """
    Standalone health check function for monitoring systems.

    Returns:
        0 if healthy, 1 if unhealthy
    """
    try:
        if app is None:
            print("Application not initialized")
            return 1

        app_health_status = validate_app_health(app)
        if app_health_status.get("overall_healthy", False):
            print("Application is healthy")
            return 0
        else:
            print("Application has health issues")
            return 1

    except Exception as err:
        print(f"Health check failed: {err}")
        return 1


# Create application instance for WSGI servers
app = create_application()

if __name__ == '__main__':
    # Check for special commands
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == 'health':
            sys.exit(health_check())
        elif command == 'config':
            try:
                config = get_config()
                summary = config.get_config_summary()
                print("Configuration Summary:")
                for key, value in summary.items():
                    print(f"  {key}: {value}")
            except Exception as e:
                print(f"Error loading configuration: {e}")
                sys.exit(1)
        elif command == 'test-services':
            try:
                print("Testing services...")
                health_status = validate_app_health(app)

                print(f"Overall Health: {'✓ Healthy' if health_status.get('overall_healthy') else '✗ Issues'}")

                for service_name, service_status in health_status.get('services', {}).items():
                    if isinstance(service_status, dict):
                        connected = service_status.get('connected', service_status.get('initialized', False))
                        status_icon = '✓' if connected else '✗'
                        print(f"  {service_name.title()}: {status_icon} {'Connected' if connected else 'Disconnected'}")

            except Exception as e:
                print(f"Service test failed: {e}")
                sys.exit(1)
        else:
            print(f"Unknown command: {command}")
            print("Available commands:")
            print("  health       - Check application health")
            print("  config       - Show configuration summary")
            print("  test-services - Test all services")
            sys.exit(1)
    else:
        # Normal startup
        main()
