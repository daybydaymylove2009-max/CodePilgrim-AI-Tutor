from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "CodePilgrim"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite+aiosqlite:///./codepilgrim.db"
    DATABASE_URL_SYNC: str = "sqlite:///./codepilgrim.db"

    REDIS_URL: str = "redis://localhost:6379/0"

    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"

    SANDBOX_DOCKER_IMAGE: str = "codepilgrim-sandbox:latest"
    SANDBOX_TIMEOUT_SECONDS: int = 10
    SANDBOX_MAX_MEMORY_MB: int = 128

    BKT_P_L0: float = 0.2
    BKT_P_G: float = 0.25
    BKT_P_S: float = 0.15
    BKT_P_T: float = 0.1
    BKT_MASTERY_THRESHOLD: float = 0.85

    SPACED_REPETITION_INITIAL_INTERVAL_DAYS: int = 1
    SPACED_REPETITION_RECALL_THRESHOLD: float = 0.85

    COGNITIVE_LOAD_CHECK_INTERVAL_SECONDS: int = 300
    COGNITIVE_LOAD_FATIGUE_SESSION_MINUTES: int = 45

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
