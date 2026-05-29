from typing import Optional

from pydantic import ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Drone delivery management APIs"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True

    # Database setup
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    def assemble_db_connection(cls, v: Optional[str], values: ValidationInfo) -> str:
        if isinstance(v, str):
            return v
        database_url = "postgresql+psycopg://{}:{}@{}/{}".format(
            values.data.get("POSTGRES_USER"),
            values.data.get("POSTGRES_PASSWORD"),
            values.data.get("POSTGRES_SERVER"),
            values.data.get("POSTGRES_DB"),
        )
        return database_url

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=True)


settings = Settings()
