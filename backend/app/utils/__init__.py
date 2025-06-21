"""
Utilities Package for NL-to-SQL Agent

This package contains utility modules that provide common functionality
across the application, including logging, configuration helpers, and
other shared utilities.

Available modules:
- logger: Centralized logging system with file rotation and console output
"""

from .logger import get_logger, log_function_call, log_exception

# Package metadata
__version__ = "1.0.0"
__author__ = "NL-to-SQL Agent Team"

# Export main utility functions for easy import
__all__ = [
    'get_logger',
    'log_function_call',
    'log_exception'
]