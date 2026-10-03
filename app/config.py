from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


JWT_ALGORITHM = "HS256"
JWT_ISSUER = "clinicas-api"
JWT_HUMAN_AUDIENCE = "clinicas-clientes-humanos"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class Settings(BaseSettings):

    app_name: str = "API de Agendamento de Consultas"
    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = Field(min_length=1)
    database_echo: bool = False
    jwt_secret_key: SecretStr
    admin_mfa_code: str = Field(pattern=r"^\d{6}$")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("jwt_secret_key")
    @classmethod
    def validar_chave_jwt(cls, valor: SecretStr) -> SecretStr:
        if len(valor.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET_KEY deve possuir ao menos 32 caracteres")
        return valor


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_jwt_secret_key() -> str:
    return get_settings().jwt_secret_key.get_secret_value()


def get_admin_mfa_code() -> str:
    return get_settings().admin_mfa_code
