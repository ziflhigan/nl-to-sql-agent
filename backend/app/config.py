"""
Configuration Management for NL-to-SQL Agent

This module provides centralized configuration management with:
- Environment variable loading with validation
- Type conversion and default values
- Configuration validation and error handling
- Integration with logging system
- Support for different environments (development, production, testing)

Usage:
    from app.config import Config

    config = Config()
    api_key = config.GOOGLE_API_KEY
    db_uri = config.DATABASE_URI
"""

import os
from pathlib import Path
from typing import Optional, Any, Dict, Literal

from dotenv import load_dotenv

from ..app.utils.logger import get_logger

# Initialize logger for this module
logger = get_logger(__name__)


class ConfigurationError(Exception):
    """Custom exception for configuration-related errors."""
    pass


def _get_env(key: str, default: Any = None) -> str:
    """Get environment variable with optional default."""
    value = os.environ.get(key, default)
    if value is None:
        logger.debug(f"Environment variable '{key}' not set, no default provided")
    return value


def _get_required_env(key: str) -> str:
    """Get required environment variable, raise error if not found."""
    value = os.environ.get(key)
    if not value:
        error_msg = f"Required environment variable '{key}' not set"
        logger.error(error_msg)
        raise ConfigurationError(error_msg)
    return value


def _get_bool_env(key: str, default: bool = False) -> bool:
    """Get boolean environment variable."""
    value = _get_env(key, str(default)).lower()
    return value in ('true', '1', 'yes', 'on', 'enabled')


def _get_int_env(key: str, default: int, min_val: Optional[int] = None,
                 max_val: Optional[int] = None) -> int:
    """Get integer environment variable with validation."""
    try:
        value = int(_get_env(key, str(default)))

        if min_val is not None and value < min_val:
            logger.warning(f"'{key}' value {value} below minimum {min_val}, using minimum")
            return min_val

        if max_val is not None and value > max_val:
            logger.warning(f"'{key}' value {value} above maximum {max_val}, using maximum")
            return max_val

        return value

    except ValueError:
        logger.warning(f"Invalid integer value for '{key}', using default {default}")
        return default


def _get_float_env(key: str, default: float, min_val: Optional[float] = None,
                   max_val: Optional[float] = None) -> float:
    """Get float environment variable with validation."""
    try:
        value = float(_get_env(key, str(default)))

        if min_val is not None and value < min_val:
            logger.warning(f"'{key}' value {value} below minimum {min_val}, using minimum")
            return min_val

        if max_val is not None and value > max_val:
            logger.warning(f"'{key}' value {value} above maximum {max_val}, using maximum")
            return max_val

        return value

    except ValueError:
        logger.warning(f"Invalid float value for '{key}', using default {default}")
        return default


def _load_environment(env_file: Optional[str] = None) -> None:
    """Load environment variables from .env file."""
    try:
        if env_file:
            env_path = Path(env_file)
        else:
            # Look for .env file in current directory and parent directories
            env_path = Path('.env')
            if not env_path.exists():
                env_path = Path('../.env')
                if not env_path.exists():
                    env_path = Path('backend/.env')

        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"Environment variables loaded from {env_path}")
        else:
            logger.warning("No .env file found, using system environment variables only")

    except Exception as err:
        logger.error(f"Error loading environment file: {err}")
        raise ConfigurationError(f"Failed to load environment configuration: {err}")


class Config:
    """
    Application configuration class that loads and validates settings
    from environment variables with comprehensive error handling.

    This class follows the 12-factor app methodology for configuration
    management, storing config in environment variables.
    """

    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration by loading environment variables.

        Args:
            env_file: Optional path to .env file. If None, uses default .env
        """
        _load_environment(env_file)
        self._validate_configuration()
        logger.info("Configuration loaded and validated successfully")

    @property
    def GOOGLE_API_KEY(self) -> str:
        """Google Gemini API key for LLM access."""
        return _get_required_env('GOOGLE_API_KEY')

    @property
    def GEMINI_MODEL_NAME(self) -> str:
        """Gemini model name to use for SQL agent."""
        return _get_env('GEMINI_MODEL_NAME', 'gemini-1.5-flash-latest')

    @property
    def LLM_TEMPERATURE(self) -> float:
        """LLM temperature setting (0.0 for deterministic, 1.0 for creative)."""
        return _get_float_env('LLM_TEMPERATURE', 0.0, min_val=0.0, max_val=1.0)

    @property
    def LLM_MAX_RETRIES(self) -> int:
        """Maximum number of retries for LLM API calls."""
        return _get_int_env('LLM_MAX_RETRIES', 2, min_val=0, max_val=10)

    @property
    def LLM_TIMEOUT(self) -> int:
        """Timeout for LLM API calls in seconds."""
        return _get_int_env('LLM_TIMEOUT', 30, min_val=5, max_val=300)

    @property
    def DATABASE_URI(self) -> str:
        """Database connection URI."""
        return _get_required_env('DATABASE_URI')

    @property
    def DATABASE_POOL_SIZE(self) -> int:
        """Database connection pool size."""
        return _get_int_env('DATABASE_POOL_SIZE', 5, min_val=1, max_val=50)

    @property
    def DATABASE_POOL_TIMEOUT(self) -> int:
        """Database connection pool timeout in seconds."""
        return _get_int_env('DATABASE_POOL_TIMEOUT', 30, min_val=5, max_val=300)

    @property
    def SECRET_KEY(self) -> str:
        """Flask secret key for session management."""
        default_key = 'dev-secret-key-change-in-production'
        key = _get_env('SECRET_KEY', default_key)

        if key == default_key and self.FLASK_ENV == 'production':
            raise ConfigurationError("SECRET_KEY must be set for production environment")

        return key

    @property
    def FLASK_ENV(self) -> str:
        """Flask environment: development, production, or testing."""
        env = _get_env('FLASK_ENV', 'development').lower()
        valid_envs = ['development', 'production', 'testing']

        if env not in valid_envs:
            logger.warning(f"Invalid FLASK_ENV '{env}', defaulting to 'development'")
            return 'development'

        return env

    @property
    def FLASK_DEBUG(self) -> bool:
        """Flask debug mode setting."""
        debug = _get_bool_env('FLASK_DEBUG', True)

        # Force debug off in production
        if self.FLASK_ENV == 'production' and debug:
            logger.warning("Debug mode disabled for production environment")
            return False

        return debug

    @property
    def FLASK_HOST(self) -> str:
        """Flask application host."""
        return _get_env('FLASK_HOST', '0.0.0.0')

    @property
    def FLASK_PORT(self) -> int:
        """Flask application port."""
        return _get_int_env('FLASK_PORT', 5000, min_val=1024, max_val=65535)

    @property
    def FRONTEND_ORIGIN(self) -> str:
        """Frontend origin for CORS configuration."""
        default_origin = 'http://localhost:3000'
        return _get_env('FRONTEND_ORIGIN', default_origin)

    @property
    def CORS_ORIGINS(self) -> list:
        """List of allowed CORS origins."""
        origins_str = _get_env('CORS_ORIGINS', self.FRONTEND_ORIGIN)
        return [origin.strip() for origin in origins_str.split(',')]

    @property
    def AGENT_VERBOSE(self) -> bool:
        """Enable verbose mode for LangChain agent (shows ReAct loop)."""
        return _get_bool_env('AGENT_VERBOSE', True)

    @property
    def AGENT_TYPE(self) -> Literal["openai-tools", "tool-calling"]:
        """
        Agent type for create_sql_agent.
        'tool-calling' is the modern, recommended type for Gemini.
        """
        # Default to the recommended type for Gemini models
        agent_type = _get_env('AGENT_TYPE', 'tool-calling').lower()

        if agent_type == 'tool-calling':
            return 'tool-calling'
        elif agent_type == 'openai-tools':
            return 'openai-tools'
        else:
            # If the value from the .env file is invalid, log a warning and return the default.
            logger.warning(
                f"Invalid AGENT_TYPE '{agent_type}' found in environment. "
                f"Defaulting to 'tool-calling'. Valid options are: 'tool-calling', 'openai-tools'."
            )
            return 'tool-calling'

    @property
    def AGENT_MAX_ITERATIONS(self) -> int:
        """Maximum iterations for agent execution."""
        return _get_int_env('AGENT_MAX_ITERATIONS', 15, min_val=5, max_val=50)

    @property
    def AGENT_MAX_EXECUTION_TIME(self) -> int:
        """Maximum execution time for agent in seconds."""
        return _get_int_env('AGENT_MAX_EXECUTION_TIME', 60, min_val=10, max_val=300)

    def _validate_configuration(self) -> None:
        """Validate critical configuration settings."""
        validations = [
            self._validate_api_key,
            self._validate_database_uri,
            self._validate_flask_config,
            self._validate_agent_config
        ]

        errors = []
        for validation in validations:
            try:
                validation()
            except ConfigurationError as e:
                errors.append(str(e))

        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"- {err}" for err in errors)
            logger.error(error_msg)
            raise ConfigurationError(error_msg)

    def _validate_api_key(self) -> None:
        """Validate Google API key format."""
        api_key = self.GOOGLE_API_KEY
        if not api_key.startswith('AI'):
            logger.warning("Google API key doesn't start with 'AI' - verify it's correct")

        if len(api_key) < 20:
            raise ConfigurationError("Google API key appears to be too short")

    def _validate_database_uri(self) -> None:
        """Validate database URI format."""
        uri = self.DATABASE_URI
        if not uri.startswith(('sqlite:///', 'postgresql://', 'mysql://')):
            raise ConfigurationError(f"Unsupported database URI format: {uri}")

        # For SQLite, check if file path is reasonable
        if uri.startswith('sqlite:///'):
            db_path = uri.replace('sqlite:///', '')
            if not db_path:
                raise ConfigurationError("SQLite database path is empty")

    def _validate_flask_config(self) -> None:
        """Validate Flask configuration."""
        if self.FLASK_PORT < 1024 and os.geteuid() != 0:
            logger.warning(f"Port {self.FLASK_PORT} requires root privileges")

    def _validate_agent_config(self) -> None:
        """Validate agent configuration."""
        if self.LLM_TEMPERATURE < 0 or self.LLM_TEMPERATURE > 1:
            raise ConfigurationError(f"LLM_TEMPERATURE must be between 0 and 1")

    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current configuration (excluding sensitive data).

        Returns:
            Dictionary with configuration summary
        """
        return {
            'environment': self.FLASK_ENV,
            'debug_mode': self.FLASK_DEBUG,
            'gemini_model': self.GEMINI_MODEL_NAME,
            'database_type': self.DATABASE_URI.split('://')[0],
            'agent_type': self.AGENT_TYPE,
            'agent_verbose': self.AGENT_VERBOSE,
            'llm_temperature': self.LLM_TEMPERATURE,
            'cors_origins': self.CORS_ORIGINS,
            'host': self.FLASK_HOST,
            'port': self.FLASK_PORT
        }

    def __repr__(self) -> str:
        """String representation of configuration."""
        summary = self.get_config_summary()
        return f"Config(env={summary['environment']}, debug={summary['debug_mode']})"


# Create a singleton instance for application-wide use
_config_instance: Optional[Config] = None


def get_config(env_file: Optional[str] = None) -> Config:
    """
    Get singleton configuration instance.

    Args:
        env_file: Optional path to environment file

    Returns:
        Configuration instance
    """
    global _config_instance

    if _config_instance is None:
        _config_instance = Config(env_file)
        logger.info("Configuration singleton initialized")

    return _config_instance


def reload_config(env_file: Optional[str] = None) -> Config:
    """
    Force reload of configuration (useful for testing).

    Args:
        env_file: Optional path to environment file

    Returns:
        New configuration instance
    """
    global _config_instance
    _config_instance = None
    return get_config(env_file)


if __name__ == "__main__":
    """Test configuration loading when module is executed directly."""
    print("Testing configuration loading...")

    try:
        config = get_config()
        print(f"Configuration loaded: {config}")
        print(f"Configuration summary: {config.get_config_summary()}")

    except ConfigurationError as e:
        print(f"Configuration error: {e}")
        print("Please check your .env file and ensure required variables are set.")

    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
