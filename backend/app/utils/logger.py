"""
Centralized Logging Utility for NL-to-SQL Agent

This module provides a comprehensive logging system with the following features:
- Dual output: console and file logging
- Daily log rotation with timestamp prefixes
- Separate directories for different log levels
- Thread-safe operations for concurrent Flask requests
- Configurable log levels and formatting
- Automatic directory creation

Usage:
    from app.utils.logger import get_logger

    logger = get_logger(__name__)
    logger.info("This is an info message")
    logger.error("This is an error message")

Log Files Structure:
    logs/
    ├── info/
    │   ├── 2025-06-21_info.log
    │   ├── 2025-06-22_info.log
    │   └── ...
    └── error/
        ├── 2025-06-21_error.log
        ├── 2025-06-22_error.log
        └── ...
"""

import logging
import logging.handlers
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict

# Thread-safe lock for logger initialization
_logger_lock = threading.Lock()
_initialized_loggers: Dict[str, logging.Logger] = {}


class TimestampedFileHandler(logging.handlers.TimedRotatingFileHandler):
    """
    Custom file handler that creates daily log files with timestamp prefixes.

    Extends TimedRotatingFileHandler to use {YYYY-MM-DD}_level.log format
    instead of the default rotation suffix.
    """

    def __init__(self, log_dir: str, level_name: str, **kwargs):
        """
        Initialize the timestamped file handler.

        Args:
            log_dir: Directory to store log files
            level_name: Log level name (info, error, etc.)
            **kwargs: Additional arguments for TimedRotatingFileHandler
        """
        self.log_dir = Path(log_dir)
        self.level_name = level_name.lower()

        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with current date
        self.base_filename = self._get_current_filename()

        # Initialize parent class with daily rotation
        super().__init__(
            filename=str(self.base_filename),
            when='midnight',
            interval=1,
            backupCount=kwargs.get('backupCount', 30),  # Keep 30 days by default
            encoding='utf-8',
            **{k: v for k, v in kwargs.items() if k != 'backupCount'}
        )

    def _get_current_filename(self) -> Path:
        """Generate filename with current date prefix."""
        date_str = datetime.now().strftime('%Y-%m-%d')
        return self.log_dir / f"{date_str}_{self.level_name}.log"

    def doRollover(self):
        """
        Perform log rollover with timestamp-based filenames.

        Override the parent method to use our custom naming convention.
        """
        if self.stream:
            self.stream.close()
            self.stream = None  # type: ignore

        # Update filename for new day
        self.base_filename = self._get_current_filename()
        self.baseFilename = str(self.base_filename)

        # Clean up old log files if backup count is exceeded
        self._cleanup_old_logs()

        # Open new file
        if not self.delay:
            self.stream = self._open()

    def _cleanup_old_logs(self):
        """Remove old log files beyond the backup count."""
        if self.backupCount > 0:
            log_files = list(self.log_dir.glob(f"*_{self.level_name}.log"))
            log_files.sort(key=lambda f: f.stat().st_mtime)

            while len(log_files) > self.backupCount:
                oldest_file = log_files.pop(0)
                try:
                    oldest_file.unlink()
                except OSError:
                    pass  # File might be in use, skip silently


class ColoredConsoleFormatter(logging.Formatter):
    """
    Console formatter with color coding for different log levels.

    Provides visual distinction between log levels in console output.
    """

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',  # Cyan
        'INFO': '\033[32m',  # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',  # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'  # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with color coding."""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']

        # Add color to level name
        record.levelname = f"{color}{record.levelname}{reset}"

        return super().format(record)


class LoggerConfig:
    """Configuration class for logging system."""

    def __init__(self):
        """Initialize logger configuration from environment variables."""
        project_root = Path(__file__).resolve().parents[2]

        self.log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        self.log_to_file = os.getenv('LOG_TO_FILE', 'True').lower() == 'true'
        self.log_to_console = os.getenv('LOG_TO_CONSOLE', 'True').lower() == 'true'
        self.log_max_file_size = int(os.getenv('LOG_MAX_FILE_SIZE', '10')) * 1024 * 1024  # MB to bytes
        self.log_backup_count = int(os.getenv('LOG_BACKUP_COUNT', '30'))

        # Log directories
        self.base_log_dir = project_root / 'logs'
        self.info_log_dir = self.base_log_dir / 'info'
        self.error_log_dir = self.base_log_dir / 'error'

        # Formatters
        self.file_format = (
            '%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s'
        )
        self.console_format = (
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
        )

        # Validate log level
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level not in valid_levels:
            self.log_level = 'INFO'


def setup_logger(name: str, config: LoggerConfig) -> logging.Logger:
    """
    Set up a logger with file and console handlers.

    Args:
        name: Logger name (typically __name__ from calling module)
        config: Logger configuration object

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.log_level))

    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()

    # File handlers for different log levels
    if config.log_to_file:
        # Info and above to info directory
        info_handler = TimestampedFileHandler(
            log_dir=str(config.info_log_dir),
            level_name='info',
            backupCount=config.log_backup_count
        )
        info_handler.setLevel(logging.INFO)
        info_handler.setFormatter(logging.Formatter(config.file_format))
        logger.addHandler(info_handler)

        # Error and above to error directory
        error_handler = TimestampedFileHandler(
            log_dir=str(config.error_log_dir),
            level_name='error',
            backupCount=config.log_backup_count
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(config.file_format))
        logger.addHandler(error_handler)

    # Console handler
    if config.log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, config.log_level))
        console_handler.setFormatter(ColoredConsoleFormatter(config.console_format))
        logger.addHandler(console_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger instance with consistent configuration.

    This function implements thread-safe singleton pattern for loggers.
    Each unique name gets one logger instance that persists for the
    application lifetime.

    Args:
        name: Logger name (typically __name__ from calling module)

    Returns:
        Configured logger instance

    Example:
        from app.utils.logger import get_logger

        logger = get_logger(__name__)
        logger.info("Application started")
        logger.error("An error occurred", exc_info=True)
    """
    with _logger_lock:
        if name not in _initialized_loggers:
            config = LoggerConfig()
            _initialized_loggers[name] = setup_logger(name, config)

        return _initialized_loggers[name]


def log_function_call(func_name: str, args: tuple = (), kwargs: dict = None) -> None:
    """
    Utility function to log function calls with parameters.

    Useful for debugging and tracing application flow.

    Args:
        func_name: Name of the function being called
        args: Positional arguments passed to function
        kwargs: Keyword arguments passed to function
    """
    logger = get_logger('function_calls')
    kwargs = kwargs or {}

    args_str = ', '.join(str(arg) for arg in args)
    kwargs_str = ', '.join(f"{k}={v}" for k, v in kwargs.items())

    params = ', '.join(filter(None, [args_str, kwargs_str]))
    logger.debug(f"Calling {func_name}({params})")


def log_exception(logger: logging.Logger, exception: Exception, context: str = "") -> None:
    """
    Utility function to log exceptions with full context.

    Args:
        logger: Logger instance to use
        exception: Exception instance to log
        context: Additional context about where the exception occurred
    """
    context_msg = f" in {context}" if context else ""
    logger.error(
        f"Exception occurred{context_msg}: {type(exception).__name__}: {str(exception)}",
        exc_info=True
    )


# Initialize base logger for this module
_module_logger = get_logger(__name__)
_module_logger.info("Logging utility initialized successfully")


def test_logging_system():
    """
    Test function to verify logging system functionality.

    This function creates test logs at different levels to verify
    that the logging system is working correctly.
    """
    test_logger = get_logger('test_logger')

    test_logger.debug("Debug message - detailed information for troubleshooting")
    test_logger.info("Info message - general application flow information")
    test_logger.warning("Warning message - something unexpected but not critical")
    test_logger.error("Error message - something went wrong but application continues")
    test_logger.critical("Critical message - serious error that might stop application")

    # Test exception logging
    try:
        raise ValueError("This is a test exception")
    except ValueError as e:
        log_exception(test_logger, e, "test_logging_system function")

    test_logger.info("Logging system test completed")


if __name__ == "__main__":
    """Run logging system test when module is executed directly."""
    print("Testing logging system...")
    test_logging_system()
    print("Check logs/info/ and logs/error/ directories for log files.")
