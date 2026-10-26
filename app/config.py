from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.constants import CODE_COLUMN_LENGTH, DEFAULT_CODE_LENGTH


class Settings(BaseSettings):
    database_url: str = "sqlite:///./shortener.db"
    base_url: str = "http://localhost:8000"
    # Bounded so a bad CODE_LENGTH can never overflow the `links.code` column.
    code_length: int = Field(default=DEFAULT_CODE_LENGTH, ge=4, le=CODE_COLUMN_LENGTH)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
