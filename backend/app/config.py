from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    real_estate_api_key: str = ""
    openwatch_base_url: str = "https://openwatch.kr/api"
    database_path: str = str(
        Path(__file__).resolve().parent.parent / "data" / "wealth_tracker.db"
    )

    # Rate limiting
    openwatch_requests_per_second: float = 1.0
    real_estate_requests_per_second: float = 2.0

    model_config = {
        "env_file": [".env", "../.env"],
        "env_file_encoding": "utf-8",
    }


settings = Settings()
