from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values
from pydantic import Field, SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigurationError(RuntimeError):
    """Safe startup failure; never includes input values or underlying exceptions."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", hide_input_in_errors=True, env_file=None)

    environment: Literal["development", "test"] = Field(default="development", validation_alias="COMMERCE_ENVIRONMENT")
    log_level: Literal["INFO", "WARNING", "ERROR"] = Field(default="INFO", validation_alias="COMMERCE_LOG_LEVEL")
    db_host: str = Field(min_length=1, max_length=253, validation_alias="S01_TEST_DB_HOST", repr=False)
    db_port: int = Field(default=3306, ge=1, le=65535, validation_alias="S01_TEST_DB_PORT", repr=False)
    db_name: str = Field(pattern=r"^[A-Za-z0-9_]{1,64}$", validation_alias="S01_TEST_DB_NAME", repr=False)
    db_user: SecretStr = Field(validation_alias="S01_TEST_DB_USER", repr=False)
    db_password: SecretStr = Field(validation_alias="S01_TEST_DB_PASSWORD", repr=False)
    db_connect_timeout: int = Field(default=5, ge=1, le=10, validation_alias="S01_TEST_DB_CONNECT_TIMEOUT_SECONDS")
    db_ssl_ca: str = Field(default="", validation_alias="S01_TEST_DB_SSL_CA", repr=False)

    @field_validator("db_user", "db_password")
    @classmethod
    def require_secret(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value():
            raise ValueError("nonempty credential required")
        return value

    @field_validator("db_host")
    @classmethod
    def validate_host(cls, value: str) -> str:
        if any(c in value for c in "\r\n\t /@"):
            raise ValueError("host must not be a URL")
        return value

    @model_validator(mode="after")
    def require_remote_tls(self) -> Settings:
        if self.db_host not in {"127.0.0.1", "localhost", "::1"} and not self.db_ssl_ca:
            raise ValueError("remote database requires trusted CA")
        if self.db_ssl_ca and not Path(self.db_ssl_ca).is_file():
            raise ValueError("trusted CA file missing")
        return self

    def connection_kwargs(self) -> dict:
        # Used only by the connector. Never log this result.
        values = dict(host=self.db_host, port=self.db_port, database=self.db_name,
                      user=self.db_user.get_secret_value(), password=self.db_password.get_secret_value(),
                      charset="utf8mb4", connect_timeout=self.db_connect_timeout,
                      read_timeout=self.db_connect_timeout, write_timeout=self.db_connect_timeout)
        if self.db_ssl_ca:
            values.update(ssl_ca=self.db_ssl_ca, ssl_verify_cert=True, ssl_verify_identity=True)
        return values


def load_settings(env_file: str | Path | None = ".env") -> Settings:
    aliases = {field.validation_alias for field in Settings.model_fields.values()}
    try:
        # Treat passwords literally, including '$', and never execute the file as shell code.
        logging.getLogger("dotenv.main").disabled = True
        values = dotenv_values(env_file, interpolate=False) if env_file is not None else {}
        supplied = {key: value for key, value in values.items() if key in aliases}
        supplied.update({key: os.environ[key] for key in aliases if key in os.environ})
        return Settings(**supplied)
    except ValidationError as exc:
        fields = sorted({str(error["loc"][0]) if error["loc"] else "connection_policy" for error in exc.errors()})
        raise ConfigurationError("Invalid configuration fields: " + ", ".join(fields)) from None
    except (OSError, ValueError):
        raise ConfigurationError("Configuration file could not be safely loaded") from None
