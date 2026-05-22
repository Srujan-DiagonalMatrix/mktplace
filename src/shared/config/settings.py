"""Application settings for the AI Car Buying Assistant MVP."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.shared.config.constants import (
    DEFAULT_INVENTORY_CSV_PATH,
    DEFAULT_PLACEHOLDER_IMAGE_PATH,
)




class PainPointScoringWeights(BaseSettings):
    """Weighting and calibration options for pain-point prioritization."""

    model_config = SettingsConfigDict(extra="ignore")

    frequency_weight: float = Field(default=0.35, alias="PAIN_POINT_FREQUENCY_WEIGHT")
    severity_weight: float = Field(default=0.4, alias="PAIN_POINT_SEVERITY_WEIGHT")
    impact_weight: float = Field(default=0.25, alias="PAIN_POINT_IMPACT_WEIGHT")
    confidence_floor: float = Field(default=0.5, alias="PAIN_POINT_CONFIDENCE_FLOOR")

    @model_validator(mode="after")
    def validate_values(self) -> "PainPointScoringWeights":
        total = self.frequency_weight + self.severity_weight + self.impact_weight
        if total <= 0:
            raise ValueError("Pain-point scoring weights must sum to a positive value")
        for val in (self.frequency_weight, self.severity_weight, self.impact_weight):
            if val < 0:
                raise ValueError("Pain-point scoring weights cannot be negative")
        if not 0 <= self.confidence_floor <= 1:
            raise ValueError("Pain-point confidence floor must be between 0 and 1")
        return self

    def normalized(self) -> dict[str, float]:
        total = self.frequency_weight + self.severity_weight + self.impact_weight
        return {
            "frequency": self.frequency_weight / total,
            "severity": self.severity_weight / total,
            "impact": self.impact_weight / total,
        }


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/mktplace",
        alias="DATABASE_URL",
    )
    inventory_csv_path: Path = Field(
        default=DEFAULT_INVENTORY_CSV_PATH,
        alias="INVENTORY_CSV_PATH",
    )
    placeholder_image_path: Path = Field(
        default=DEFAULT_PLACEHOLDER_IMAGE_PATH,
        alias="PLACEHOLDER_IMAGE_PATH",
    )
    chroma_enabled: bool = Field(default=False, alias="CHROMA_ENABLED")
    chroma_db_path: Path = Field(default=Path("vector_db"), alias="CHROMA_DB_PATH")
    fastapi_host: str = Field(default="127.0.0.1", alias="FASTAPI_HOST")
    fastapi_port: int = Field(default=8000, alias="FASTAPI_PORT")
    streamlit_host: str = Field(default="127.0.0.1", alias="STREAMLIT_HOST")
    streamlit_port: int = Field(default=8501, alias="STREAMLIT_PORT")
    admin_token: str = Field(default="", alias="ADMIN_TOKEN")
    pain_point_scoring: PainPointScoringWeights = PainPointScoringWeights()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()