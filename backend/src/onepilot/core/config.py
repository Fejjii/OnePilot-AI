from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_ENV: str = "dev"
    APP_NAME: str = "OnePilot AI"
    APP_VERSION: str = "0.1.0"

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    DATABASE_URL: str = "sqlite:///./onepilot_dev.db"
    REDIS_URL: str = ""
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""

    LANGSMITH_API_KEY: str = ""
    LANGSMITH_TRACING: bool = False
    SERPER_API_KEY: str = ""

    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    DEV_AUTH_ENABLED: bool = True
    DEV_ORG_ID: str = "org_demo_onepilot"
    DEV_USER_ID: str = "usr_demo_admin"
    DEV_BYPASS_QUOTAS: bool = False

    @property
    def is_dev(self) -> bool:
        return self.APP_ENV == "dev"

    @property
    def is_test(self) -> bool:
        return self.APP_ENV == "test"

    @property
    def has_openai(self) -> bool:
        return bool(self.OPENAI_API_KEY)

    @property
    def has_qdrant(self) -> bool:
        return bool(self.QDRANT_URL)

    @property
    def has_redis(self) -> bool:
        return bool(self.REDIS_URL)

    @property
    def has_langsmith(self) -> bool:
        return bool(self.LANGSMITH_API_KEY) and self.LANGSMITH_TRACING

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
