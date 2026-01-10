"""
Core Secrets Management System

Centralized, secure secrets management for AstraGuard AI.
Provides unified access to secrets from environment variables, files, and external vaults.

Features:
- Secure secret retrieval with validation
- Type conversion and validation
- Secret masking in logs
- Support for multiple secret sources
- Environment-specific configurations
"""

import os
import json
import logging
from typing import Any, Dict, Optional, Union, List
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import secrets
import hashlib
import base64

logger = logging.getLogger(__name__)


class SecretSource(Enum):
    """Supported secret sources."""
    ENVIRONMENT = "environment"
    FILE = "file"
    VAULT = "vault"  # For future Azure Key Vault, AWS Secrets Manager, etc.


class SecretType(Enum):
    """Secret data types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"
    BYTES = "bytes"


@dataclass
class SecretConfig:
    """Configuration for a secret."""
    key: str
    default: Any = None
    required: bool = False
    secret_type: SecretType = SecretType.STRING
    source: SecretSource = SecretSource.ENVIRONMENT
    file_path: Optional[str] = None
    vault_path: Optional[str] = None
    validate_func: Optional[callable] = None
    mask_in_logs: bool = True


class SecretsManager:
    """
    Centralized secrets management system.

    Provides secure access to secrets with validation, type conversion,
    and protection against accidental logging.
    """

    def __init__(self, environment: str = None):
        """
        Initialize secrets manager.

        Args:
            environment: Environment name (development, staging, production)
        """
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        self._cache: Dict[str, Any] = {}
        self._masked_cache: Dict[str, str] = {}

        # Initialize secret configurations
        self._secret_configs = self._initialize_secret_configs()

    def _initialize_secret_configs(self) -> Dict[str, SecretConfig]:
        """Initialize all secret configurations."""
        configs = {}

        # API and Authentication
        configs["api_key"] = SecretConfig(
            key="API_KEY",
            required=False,
            mask_in_logs=True
        )

        configs["api_secret"] = SecretConfig(
            key="API_SECRET",
            required=False,
            mask_in_logs=True
        )

        configs["jwt_secret"] = SecretConfig(
            key="JWT_SECRET",
            default=self._generate_secure_secret(),
            required=True,
            mask_in_logs=True
        )

        # Database
        configs["database_url"] = SecretConfig(
            key="DATABASE_URL",
            default="sqlite:///data/astraguard.db",
            required=False
        )

        configs["database_pool_size"] = SecretConfig(
            key="DATABASE_POOL_SIZE",
            default=5,
            secret_type=SecretType.INTEGER,
            required=False
        )

        # Redis
        configs["redis_url"] = SecretConfig(
            key="REDIS_URL",
            default="redis://localhost:6379",
            required=False
        )

        configs["redis_host"] = SecretConfig(
            key="REDIS_HOST",
            default="localhost",
            required=False
        )

        configs["redis_port"] = SecretConfig(
            key="REDIS_PORT",
            default=6379,
            secret_type=SecretType.INTEGER,
            required=False
        )

        # Metrics and Monitoring
        configs["metrics_user"] = SecretConfig(
            key="METRICS_USER",
            required=False,
            mask_in_logs=True
        )

        configs["metrics_password"] = SecretConfig(
            key="METRICS_PASSWORD",
            required=False,
            mask_in_logs=True
        )

        configs["grafana_password"] = SecretConfig(
            key="GRAFANA_PASSWORD",
            default="admin",
            required=False,
            mask_in_logs=True
        )

        # Application Configuration
        configs["log_level"] = SecretConfig(
            key="LOG_LEVEL",
            default="INFO",
            required=False
        )

        configs["debug"] = SecretConfig(
            key="DEBUG",
            default=False,
            secret_type=SecretType.BOOLEAN,
            required=False
        )

        configs["environment"] = SecretConfig(
            key="ENVIRONMENT",
            default="development",
            required=False
        )

        # API Configuration
        configs["api_host"] = SecretConfig(
            key="API_HOST",
            default="0.0.0.0",
            required=False
        )

        configs["api_port"] = SecretConfig(
            key="API_PORT",
            default=8000,
            secret_type=SecretType.INTEGER,
            required=False
        )

        # CORS
        configs["allowed_origins"] = SecretConfig(
            key="ALLOWED_ORIGINS",
            default="http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000",
            required=False
        )

        # Rate Limiting
        configs["rate_limit_telemetry"] = SecretConfig(
            key="RATE_LIMIT_TELEMETRY",
            default="1000/hour",
            required=False
        )

        configs["rate_limit_api"] = SecretConfig(
            key="RATE_LIMIT_API",
            default="500/hour",
            required=False
        )

        # Resource Monitoring
        configs["resource_cpu_warning"] = SecretConfig(
            key="RESOURCE_CPU_WARNING",
            default=70.0,
            secret_type=SecretType.FLOAT,
            required=False
        )

        configs["resource_cpu_critical"] = SecretConfig(
            key="RESOURCE_CPU_CRITICAL",
            default=90.0,
            secret_type=SecretType.FLOAT,
            required=False
        )

        configs["resource_memory_warning"] = SecretConfig(
            key="RESOURCE_MEMORY_WARNING",
            default=75.0,
            secret_type=SecretType.FLOAT,
            required=False
        )

        configs["resource_memory_critical"] = SecretConfig(
            key="RESOURCE_MEMORY_CRITICAL",
            default=90.0,
            secret_type=SecretType.FLOAT,
            required=False
        )

        configs["resource_monitoring_enabled"] = SecretConfig(
            key="RESOURCE_MONITORING_ENABLED",
            default=True,
            secret_type=SecretType.BOOLEAN,
            required=False
        )

        # Timeouts
        configs["timeout_model_load"] = SecretConfig(
            key="OPERATION_TIMEOUT_MODEL_LOAD",
            default=5.0,
            secret_type=SecretType.FLOAT,
            required=False
        )

        configs["timeout_inference"] = SecretConfig(
            key="OPERATION_TIMEOUT_INFERENCE",
            default=2.0,
            secret_type=SecretType.FLOAT,
            required=False
        )

        configs["timeout_redis"] = SecretConfig(
            key="OPERATION_TIMEOUT_REDIS",
            default=5.0,
            secret_type=SecretType.FLOAT,
            required=False
        )

        configs["timeout_file_io"] = SecretConfig(
            key="OPERATION_TIMEOUT_FILE_IO",
            default=10.0,
            secret_type=SecretType.FLOAT,
            required=False
        )

        # Azure Configuration (for production)
        configs["azure_resource_group"] = SecretConfig(
            key="AZURE_RESOURCE_GROUP",
            required=False
        )

        configs["azure_container_registry"] = SecretConfig(
            key="AZURE_CONTAINER_REGISTRY",
            required=False
        )

        configs["azure_storage_account"] = SecretConfig(
            key="AZURE_STORAGE_ACCOUNT",
            required=False
        )

        # Simulation mode
        configs["simulation_mode"] = SecretConfig(
            key="ASTRAGUARD_SIMULATION_MODE",
            default=False,
            secret_type=SecretType.BOOLEAN,
            required=False
        )

        # Backend URL for frontend
        configs["backend_url"] = SecretConfig(
            key="ASTRAGUARD_BACKEND_URL",
            default="http://localhost:8000",
            required=False
        )

        # Chaos engineering
        configs["chaos_enabled"] = SecretConfig(
            key="ENABLE_CHAOS",
            default=False,
            secret_type=SecretType.BOOLEAN,
            required=False
        )

        configs["chaos_admin_key"] = SecretConfig(
            key="CHAOS_ADMIN_KEY",
            required=False,
            mask_in_logs=True
        )

        # Tracing and observability
        configs["jaeger_host"] = SecretConfig(
            key="JAEGER_HOST",
            default="localhost",
            required=False
        )

        configs["jaeger_port"] = SecretConfig(
            key="JAEGER_PORT",
            default=6831,
            secret_type=SecretType.INTEGER,
            required=False
        )

        configs["app_version"] = SecretConfig(
            key="APP_VERSION",
            default="1.0.0",
            required=False
        )

        configs["enable_json_logging"] = SecretConfig(
            key="ENABLE_JSON_LOGGING",
            default=False,
            secret_type=SecretType.BOOLEAN,
            required=False
        )

        # API Keys for authentication
        configs["api_keys"] = SecretConfig(
            key="API_KEYS",
            required=False,
            mask_in_logs=True
        )

        return configs

    def _generate_secure_secret(self) -> str:
        """Generate a secure random secret."""
        return base64.b64encode(secrets.token_bytes(32)).decode('utf-8')

    def get(self, name: str, default: Any = None) -> Any:
        """
        Get a secret value with validation and type conversion.

        Args:
            name: Secret name
            default: Default value if secret not found

        Returns:
            Secret value with proper type conversion

        Raises:
            ValueError: If required secret is missing
        """
        if name in self._cache:
            return self._cache[name]

        config = self._secret_configs.get(name)
        if not config:
            # Unknown secret, try environment variable
            value = os.getenv(name.upper(), default)
            self._cache[name] = value
            return value

        # Get value based on source
        if config.source == SecretSource.ENVIRONMENT:
            value = self._get_from_environment(config, default if default is not None else config.default)
        elif config.source == SecretSource.FILE:
            value = self._get_from_file(config, default if default is not None else config.default)
        elif config.source == SecretSource.VAULT:
            value = self._get_from_vault(config, default if default is not None else config.default)
        else:
            value = default if default is not None else config.default

        # Validate required secrets
        if config.required and value is None:
            raise ValueError(f"Required secret '{name}' is not set")

        # Type conversion
        value = self._convert_type(value, config.secret_type)

        # Custom validation
        if config.validate_func and value is not None:
            config.validate_func(value)

        # Cache the value
        self._cache[name] = value

        return value

    def _get_from_environment(self, config: SecretConfig, default: Any) -> Any:
        """Get secret from environment variable."""
        return os.getenv(config.key, default)

    def _get_from_file(self, config: SecretConfig, default: Any) -> Any:
        """Get secret from file."""
        if not config.file_path:
            return default

        try:
            with open(config.file_path, 'r') as f:
                return f.read().strip()
        except (FileNotFoundError, IOError):
            logger.warning(f"Could not read secret file: {config.file_path}")
            return default

    def _get_from_vault(self, config: SecretConfig, default: Any) -> Any:
        """Get secret from external vault (placeholder for future implementation)."""
        # TODO: Implement Azure Key Vault, AWS Secrets Manager, etc.
        logger.warning(f"Vault secrets not yet implemented for: {config.key}")
        return default

    def _convert_type(self, value: Any, secret_type: SecretType) -> Any:
        """Convert value to the specified type."""
        if value is None:
            return None

        try:
            if secret_type == SecretType.STRING:
                return str(value)
            elif secret_type == SecretType.INTEGER:
                return int(value)
            elif secret_type == SecretType.FLOAT:
                return float(value)
            elif secret_type == SecretType.BOOLEAN:
                if isinstance(value, str):
                    return value.lower() in ('true', '1', 'yes', 'on')
                return bool(value)
            elif secret_type == SecretType.JSON:
                if isinstance(value, str):
                    return json.loads(value)
                return value
            elif secret_type == SecretType.BYTES:
                if isinstance(value, str):
                    return value.encode('utf-8')
                return value
            else:
                return value
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            logger.warning(f"Type conversion failed for value '{value}': {e}")
            return value

    def get_masked(self, name: str) -> str:
        """
        Get a masked version of the secret for logging.

        Args:
            name: Secret name

        Returns:
            Masked secret string
        """
        if name in self._masked_cache:
            return self._masked_cache[name]

        config = self._secret_configs.get(name)
        if config and config.mask_in_logs:
            value = self.get(name)
            if value is not None:
                # Create a masked version
                if isinstance(value, str) and len(value) > 4:
                    masked = value[:2] + "*" * (len(value) - 4) + value[-2:]
                else:
                    masked = "***"
                self._masked_cache[name] = masked
                return masked

        return self.get(name) or ""

    def validate_all_required(self) -> List[str]:
        """
        Validate that all required secrets are available.

        Returns:
            List of missing required secrets
        """
        missing = []
        for name, config in self._secret_configs.items():
            if config.required:
                try:
                    value = self.get(name)
                    if value is None:
                        missing.append(name)
                except ValueError:
                    missing.append(name)
        return missing

    def list_secrets(self, include_values: bool = False) -> Dict[str, Any]:
        """
        List all configured secrets.

        Args:
            include_values: Whether to include actual secret values

        Returns:
            Dictionary of secret information
        """
        result = {}
        for name, config in self._secret_configs.items():
            info = {
                "key": config.key,
                "required": config.required,
                "type": config.secret_type.value,
                "source": config.source.value,
                "masked": config.mask_in_logs
            }
            if include_values:
                info["value"] = self.get_masked(name) if config.mask_in_logs else self.get(name)
            result[name] = info
        return result

    def reload_cache(self):
        """Clear the secret cache to force reloading from sources."""
        self._cache.clear()
        self._masked_cache.clear()


# Global secrets manager instance
_secrets_manager = None

def get_secrets_manager() -> SecretsManager:
    """Get the global secrets manager instance."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager

def get_secret(name: str, default: Any = None) -> Any:
    """
    Convenience function to get a secret.

    Args:
        name: Secret name
        default: Default value

    Returns:
        Secret value
    """
    return get_secrets_manager().get(name, default)

def get_secret_masked(name: str) -> str:
    """
    Convenience function to get a masked secret.

    Args:
        name: Secret name

    Returns:
        Masked secret string
    """
    return get_secrets_manager().get_masked(name)