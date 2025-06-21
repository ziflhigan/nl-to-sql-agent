"""
API Blueprint for NL-to-SQL Agent

This module defines the Flask Blueprint for the API endpoints,
providing a modular and organized approach to route management.

The API blueprint contains all endpoints related to the NL-to-SQL
functionality, including chat, health checks, and status monitoring.

Blueprint Structure:
- /health - Basic health check endpoint
- /status - Comprehensive service status and statistics
- /chat - Main NL-to-SQL query endpoint

All endpoints follow consistent JSON response format:
{
    "data": <response_data>,
    "error": null | <error_object>
}

Usage:
    from app.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api/v1')
"""

from flask import Blueprint

# Create the API blueprint
api_bp = Blueprint(
    'api',
    __name__,
    url_prefix='/api/v1'
)

# Import routes to register them with the blueprint
# This must be done after blueprint creation to avoid circular imports
from . import routes

# Blueprint metadata
__version__ = "1.0.0"
__description__ = "NL-to-SQL Agent API Blueprint"

# Export the blueprint for use in the main application
__all__ = ['api_bp']
