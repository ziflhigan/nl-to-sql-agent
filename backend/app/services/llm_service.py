"""
LLM Service for NL-to-SQL Agent

This module provides a dedicated service for managing Google Gemini LLM
interactions, including initialization, configuration, health monitoring,
and API communication. It is completely decoupled from database operations.

Features:
- Google Gemini LLM initialization and configuration
- API key validation and authentication handling
- Model parameter management (temperature, retries, timeout)
- LLM health checks and connectivity testing
- Centralized error handling and retry logic
- Token usage monitoring and rate limiting awareness
- Model availability and capability testing

Usage:
    from app.services.llm_service import LLMService
    from app.config import get_config

    config = get_config()
    llm_service = LLMService(config)

    # Test LLM connectivity
    if llm_service.test_connection():
        response = llm_service.generate_response("What is 2+2?")
        print(f"LLM Response: {response}")
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from backend.app.config import Config
from backend.app.utils.logger import get_logger, log_exception
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

# Initialize logger for this module
logger = get_logger(__name__)


class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass


class LLMConnectionError(LLMError):
    """Exception raised when LLM connection/authentication fails."""
    pass


class LLMConfigurationError(LLMError):
    """Exception raised when LLM configuration is invalid."""
    pass


class LLMRateLimitError(LLMError):
    """Exception raised when API rate limits are exceeded."""
    pass


class LLMTimeoutError(LLMError):
    """Exception raised when LLM requests timeout."""
    pass


class LLMService:
    """
    LLM service that manages Google Gemini interactions and operations.

    This service provides a clean interface for LLM operations while
    handling authentication, rate limiting, error recovery, and health monitoring.
    """

    def __init__(self, custom_config: Config):
        """
        Initialize the LLM service.

        Args:
            custom_config: Application configuration instance
        """
        self.config = custom_config
        self.llm: Optional[ChatGoogleGenerativeAI] = None
        self._last_health_check: Optional[float] = None
        self._health_check_interval = 300  # 5 minutes
        self._rate_limit_reset: Optional[datetime] = None
        self._request_count = 0
        self._last_request_time: Optional[datetime] = None

        logger.info("Initializing LLMService")
        self._validate_configuration()
        self._initialize_llm()
        self._verify_connection()
        logger.info("LLMService initialized successfully")

    def _validate_configuration(self) -> None:
        """Validate LLM configuration parameters."""
        try:
            # Validate API key format
            api_key = self.config.GOOGLE_API_KEY
            if not api_key:
                raise LLMConfigurationError("Google API key is required")

            if not api_key.startswith('AI'):
                logger.warning("Google API key format may be incorrect (should start with 'AI')")

            if len(api_key) < 20:
                raise LLMConfigurationError("Google API key appears to be too short")

            # Validate model name
            model_name = self.config.GEMINI_MODEL_NAME
            valid_models = [
                'gemini-2.5-pro',
                'gemini-2.5-flash',
                'gemini-2.5-flash-lite-preview-06-17',

                'gemini-2.0-flash',
                'gemini-2.0-flash-lite',

                'gemini-1.5-pro-latest',
                'gemini-1.5-flash-latest',

                'gemini-1.5-pro',
                'gemini-1.5-flash',

                # Older generation model for backward compatibility
                'gemini-pro'
            ]

            if model_name not in valid_models:
                logger.warning(f"Model '{model_name}' may not be supported. "
                               f"Supported models: {', '.join(valid_models)}")

            # Validate temperature
            temp = self.config.LLM_TEMPERATURE
            if not 0.0 <= temp <= 1.0:
                raise LLMConfigurationError(f"Temperature must be between 0.0 and 1.0, got {temp}")

            # Validate other parameters
            if self.config.LLM_MAX_RETRIES < 0:
                raise LLMConfigurationError("Max retries cannot be negative")

            if self.config.LLM_TIMEOUT < 5:
                raise LLMConfigurationError("Timeout must be at least 5 seconds")

            logger.info("LLM configuration validation successful")

        except Exception as err:
            error_msg = f"LLM configuration validation failed: {err}"
            logger.error(error_msg)
            raise LLMConfigurationError(error_msg) from err

    def _initialize_llm(self) -> None:
        """Initialize the Google Gemini LLM instance."""
        try:
            logger.info(f"Initializing Gemini model: {self.config.GEMINI_MODEL_NAME}")

            # Create LLM instance with configuration
            self.llm = ChatGoogleGenerativeAI(
                model=self.config.GEMINI_MODEL_NAME,
                temperature=self.config.LLM_TEMPERATURE,
                max_retries=self.config.LLM_MAX_RETRIES,
                timeout=self.config.LLM_TIMEOUT,
                google_api_key=self.config.GOOGLE_API_KEY
            )

            logger.info("Gemini LLM instance created successfully")

        except Exception as err:
            error_msg = f"Failed to initialize Gemini LLM: {err}"
            logger.error(error_msg)
            raise LLMConnectionError(error_msg) from err

    def _verify_connection(self) -> None:
        """Verify LLM connection during initialization."""
        if not self.test_connection():
            raise LLMConnectionError("Failed to establish LLM connection during initialization")

    def test_connection(self) -> bool:
        """
        Test LLM connectivity with a simple request.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            if not self.llm:
                logger.error("LLM instance not initialized")
                return False

            logger.debug("Testing LLM connection")

            # Simple test message
            test_message = HumanMessage(content="Respond with just the word 'OK'")

            # Make test request with shorter timeout
            start_time = time.time()
            llm_response = self.llm.invoke([test_message])
            end_time = time.time()

            response_time = end_time - start_time
            logger.debug(f"LLM connection test successful (response time: {response_time:.2f}s)")

            # Update health check timestamp
            self._last_health_check = time.time()

            # Check if response is reasonable
            if hasattr(llm_response, 'content') and llm_response.content:
                logger.debug(f"Test response: {llm_response.content[:50]}")
                return True
            else:
                logger.warning("LLM test response was empty or invalid")
                return False

        except Exception as err:
            log_exception(logger, err, "LLM connection test")
            return False

    def generate_response(self, prompt: str, system_prompt: Optional[str] = None,
                          max_tokens: Optional[int] = None) -> str:
        """
        Generate a response from the LLM.

        Args:
            prompt: User prompt/question
            system_prompt: Optional system instruction
            max_tokens: Optional maximum tokens limit

        Returns:
            Generated response text

        Raises:
            LLMError: If response generation fails
        """
        if not self.llm:
            raise LLMConnectionError("LLM instance not initialized")

        if not prompt.strip():
            raise LLMError("Prompt cannot be empty")

        try:
            # Track request for rate limiting awareness
            self._update_request_tracking()

            # Prepare messages
            messages = []

            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            else:
                messages.append(HumanMessage(content=prompt))

            logger.debug(f"Generating LLM response for prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")

            start_time = time.time()

            # Generate response
            llm_response = self.llm.invoke(messages)

            end_time = time.time()
            response_time = end_time - start_time

            # Extract response content
            if hasattr(llm_response, 'content'):
                response_text = llm_response.content.strip()
            else:
                response_text = str(llm_response).strip()

            logger.info(f"LLM response generated successfully (time: {response_time:.2f}s, "
                        f"length: {len(response_text)} chars)")

            return response_text

        except Exception as err:
            # Handle specific error types
            error_msg = str(err).lower()

            if 'rate limit' in error_msg or 'quota' in error_msg:
                self._handle_rate_limit_error(err)
                raise LLMRateLimitError(f"API rate limit exceeded: {err}") from err

            elif 'timeout' in error_msg:
                raise LLMTimeoutError(f"LLM request timeout: {err}") from err

            elif 'api_key' in error_msg or 'authentication' in error_msg:
                raise LLMConnectionError(f"LLM authentication error: {err}") from err

            else:
                error_msg = f"LLM response generation failed: {err}"
                logger.error(error_msg)
                raise LLMError(error_msg) from err

    def _update_request_tracking(self) -> None:
        """Update request tracking for rate limiting awareness."""
        current_time = datetime.now()
        self._last_request_time = current_time
        self._request_count += 1

        # Reset counter every hour
        if (self._rate_limit_reset is None or
                current_time > self._rate_limit_reset + timedelta(hours=1)):
            self._request_count = 1
            self._rate_limit_reset = current_time

    def _handle_rate_limit_error(self, error: Exception) -> None:
        """Handle rate limit errors and update tracking."""
        logger.warning(f"Rate limit encountered: {error}")
        self._rate_limit_reset = datetime.now() + timedelta(hours=1)

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive LLM health status.

        Returns:
            Dictionary with health status information
        """
        status = {
            'connected': False,
            'last_check': self._last_health_check,
            'model_name': self.config.GEMINI_MODEL_NAME,
            'temperature': self.config.LLM_TEMPERATURE,
            'max_retries': self.config.LLM_MAX_RETRIES,
            'timeout': self.config.LLM_TIMEOUT,
            'llm_status': 'not_initialized' if not self.llm else 'initialized',
            'request_tracking': {
                'total_requests': self._request_count,
                'last_request': self._last_request_time.isoformat() if self._last_request_time else None,
                'rate_limit_reset': self._rate_limit_reset.isoformat() if self._rate_limit_reset else None
            }
        }

        try:
            # Perform connection test if it's been a while
            current_time = time.time()
            if (not self._last_health_check or
                    current_time - self._last_health_check > self._health_check_interval):
                status['connected'] = self.test_connection()
            else:
                status['connected'] = True  # Assume healthy if recently checked

        except Exception as err:
            log_exception(logger, err, "LLM health status check")
            status['error'] = str(err)

        return status

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.

        Returns:
            Dictionary with model information
        """
        return {
            'model_name': self.config.GEMINI_MODEL_NAME,
            'provider': 'Google',
            'model_family': 'Gemini',
            'configuration': {
                'temperature': self.config.LLM_TEMPERATURE,
                'max_retries': self.config.LLM_MAX_RETRIES,
                'timeout': self.config.LLM_TIMEOUT
            },
            'capabilities': [
                'text_generation',
                'conversation',
                'code_generation',
                'sql_generation',
                'reasoning'
            ],
            'limitations': [
                'no_direct_system_messages',
                'rate_limited',
                'context_window_limits'
            ]
        }

    def validate_prompt_for_sql(self, prompt: str) -> Dict[str, Any]:
        """
        Validate and analyze a prompt for SQL generation suitability.

        Args:
            prompt: User prompt to validate

        Returns:
            Dictionary with validation results
        """
        custom_validation = {
            'is_valid': True,
            'warnings': [],
            'suggestions': [],
            'complexity_score': 0
        }

        prompt_lower = prompt.lower().strip()

        # Check for empty or very short prompts
        if len(prompt.strip()) < 3:
            custom_validation['is_valid'] = False
            custom_validation['warnings'].append("Prompt is too short")
            return custom_validation

        # Check for SQL injection patterns (basic check)
        sql_injection_patterns = [
            'drop table', 'delete from', 'update set', 'insert into',
            'alter table', 'create table', 'truncate', '--', ';'
        ]

        for pattern in sql_injection_patterns:
            if pattern in prompt_lower:
                custom_validation['warnings'].append(f"Potential SQL injection pattern detected: {pattern}")

        # Check complexity indicators
        complexity_indicators = [
            'join', 'group by', 'order by', 'having', 'subquery',
            'aggregate', 'sum', 'count', 'average', 'max', 'min'
        ]

        for indicator in complexity_indicators:
            if indicator in prompt_lower:
                custom_validation['complexity_score'] += 1

        # Provide suggestions based on prompt content
        if 'show' in prompt_lower or 'list' in prompt_lower:
            custom_validation['suggestions'].append("Consider specifying which columns you need")

        if custom_validation['complexity_score'] > 3:
            custom_validation['suggestions'].append("Complex query detected - consider breaking into smaller parts")

        return custom_validation

    def get_usage_statistics(self) -> Dict[str, Any]:
        """
        Get LLM usage statistics.

        Returns:
            Dictionary with usage statistics
        """
        return {
            'total_requests': self._request_count,
            'last_request_time': self._last_request_time.isoformat() if self._last_request_time else None,
            'rate_limit_status': {
                'reset_time': self._rate_limit_reset.isoformat() if self._rate_limit_reset else None,
                'requests_this_period': self._request_count
            },
            'health_status': self.get_health_status()
        }

    def close(self) -> None:
        """Clean up LLM service resources."""
        logger.info("Closing LLM service")
        if self.llm:
            # No specific cleanup needed for ChatGoogleGenerativeAI
            self.llm = None
        logger.info("LLM service closed successfully")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.close()

    def __repr__(self) -> str:
        """String representation of LLM service."""
        model = self.config.GEMINI_MODEL_NAME
        connected = self.test_connection() if self.llm else False
        return f"LLMService(model={model}, connected={connected})"


def create_llm_service(custom_config: Optional[Config] = None) -> LLMService:
    """
    Factory function to create an LLM service instance.

    Args:
        custom_config: Optional configuration instance

    Returns:
        Configured LLMService instance
    """
    if custom_config is None:
        from backend.app.config import get_config
        custom_config = get_config()

    return LLMService(custom_config)


if __name__ == "__main__":
    """Test LLM service when module is executed directly."""
    print("Testing LLMService...")

    try:
        from backend.app.config import get_config

        # Load configuration
        config = get_config()

        # Create LLM service
        with create_llm_service(config) as llm_service:
            print(f"LLM service: {llm_service}")

            # Test connection
            if llm_service.test_connection():
                print("✓ LLM connection successful")

                # Get model info
                model_info = llm_service.get_model_info()
                print(f"✓ Model: {model_info['model_name']} ({model_info['provider']})")
                print(f"✓ Temperature: {model_info['configuration']['temperature']}")

                # Test simple generation
                try:
                    response = llm_service.generate_response(
                        "What is 2+2? Answer with just the number."
                    )
                    print(f"✓ Test generation successful: {response}")
                except Exception as e:
                    print(f"✗ Test generation failed: {e}")

                # Test SQL prompt validation
                validation = llm_service.validate_prompt_for_sql(
                    "Show me all customers from the USA"
                )
                print(f"✓ Prompt validation: {validation['is_valid']}")

                # Get usage statistics
                stats = llm_service.get_usage_statistics()
                print(f"✓ Total requests: {stats['total_requests']}")

            else:
                print("✗ LLM connection failed")

    except Exception as e:
        print(f"✗ LLMService test failed: {e}")
        import traceback

        traceback.print_exc()
