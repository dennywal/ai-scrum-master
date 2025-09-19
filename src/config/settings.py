"""Configuration settings for AI Scrum Master."""

from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings

# Load environment variables
load_dotenv()


class LLMSettings(BaseSettings):
    """LLM configuration settings."""

    openai_api_key: SecretStr = Field(..., env="OPENAI_API_KEY")
    model_name: str = Field("gpt-5", env="LLM_MODEL_NAME")
    temperature: float = Field(0.5, env="LLM_TEMPERATURE", ge=0.0, le=2.0)
    max_tokens: int = Field(4000, env="LLM_MAX_TOKENS", ge=1, le=256000)  # GPT-5 supports up to 256k

    class Config:
        env_prefix = "LLM_"
        case_sensitive = False


class GitHubSettings(BaseSettings):
    """GitHub configuration settings."""

    github_token: SecretStr = Field(..., env="GITHUB_TOKEN")
    api_timeout: int = Field(30, env="GITHUB_API_TIMEOUT", ge=1)
    default_labels: list[str] = Field(
        ["ai-generated", "scrum"],
        env="DEFAULT_LABELS"
    )

    @field_validator('default_labels', mode='before')
    @classmethod
    def parse_labels(cls, v):
        """Parse comma-separated labels from environment."""
        if isinstance(v, str):
            return [label.strip() for label in v.split(',')]
        return v

    class Config:
        env_prefix = "GITHUB_"
        case_sensitive = False


class RetrySettings(BaseSettings):
    """Retry configuration settings."""

    max_attempts: int = Field(3, env="MAX_RETRY_ATTEMPTS", ge=1, le=10)
    delay_seconds: float = Field(1.0, env="RETRY_DELAY_SECONDS", ge=0.1)
    backoff_factor: float = Field(2.0, env="RETRY_BACKOFF_FACTOR", ge=1.0)

    class Config:
        env_prefix = "RETRY_"
        case_sensitive = False


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""

    level: str = Field("INFO", env="LOG_LEVEL")
    format: str = Field("json", env="LOG_FORMAT")  # json or console
    file: Path | None = Field(None, env="LOG_FILE")

    @field_validator('level')
    @classmethod
    def validate_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}")
        return v.upper()

    @field_validator('format')
    @classmethod
    def validate_format(cls, v):
        """Validate log format."""
        valid_formats = ["json", "console"]
        if v.lower() not in valid_formats:
            raise ValueError(f"Invalid log format: {v}")
        return v.lower()

    @field_validator('file', mode='before')
    @classmethod
    def parse_file_path(cls, v):
        """Parse file path."""
        if v:
            return Path(v)
        return None

    class Config:
        env_prefix = "LOG_"
        case_sensitive = False


class FeatureFlags(BaseSettings):
    """Feature flag settings."""

    enable_fallback_mode: bool = Field(True, env="ENABLE_FALLBACK_MODE")
    enable_batch_processing: bool = Field(True, env="ENABLE_BATCH_PROCESSING")
    enable_dependency_resolution: bool = Field(True, env="ENABLE_DEPENDENCY_RESOLUTION")
    enable_auto_priority: bool = Field(True, env="ENABLE_AUTO_PRIORITY")
    enable_caching: bool = Field(False, env="ENABLE_CACHING")

    class Config:
        env_prefix = "FEATURE_"
        case_sensitive = False


class RateLimiting(BaseSettings):
    """Rate limiting settings."""

    github_requests_per_hour: int = Field(5000, env="GITHUB_REQUESTS_PER_HOUR", ge=1)
    openai_requests_per_minute: int = Field(60, env="OPENAI_REQUESTS_PER_MINUTE", ge=1)

    class Config:
        case_sensitive = False


class PathSettings(BaseSettings):
    """Path configuration settings."""

    output_dir: Path = Field(Path("./output"), env="OUTPUT_DIR")
    cache_dir: Path = Field(Path("./cache"), env="CACHE_DIR")
    temp_dir: Path = Field(Path("/tmp/ai_scrum_master"), env="TEMP_DIR")

    @field_validator('output_dir', 'cache_dir', 'temp_dir', mode='before')
    @classmethod
    def parse_path(cls, v):
        """Parse path from string."""
        if isinstance(v, str):
            return Path(v)
        return v

    def ensure_directories(self):
        """Ensure all directories exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    class Config:
        case_sensitive = False


class Settings(BaseSettings):
    """Main settings class combining all configurations."""

    # Sub-settings
    llm: LLMSettings = Field(default_factory=LLMSettings)
    github: GitHubSettings = Field(default_factory=GitHubSettings)
    retry: RetrySettings = Field(default_factory=RetrySettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    rate_limiting: RateLimiting = Field(default_factory=RateLimiting)
    paths: PathSettings = Field(default_factory=PathSettings)

    # Application settings
    app_name: str = Field("AI Scrum Master", env="APP_NAME")
    app_version: str = Field("0.1.0", env="APP_VERSION")
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")

    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v):
        """Validate environment."""
        valid_envs = ["development", "staging", "production", "test"]
        if v.lower() not in valid_envs:
            raise ValueError(f"Invalid environment: {v}")
        return v.lower()

    class Config:
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"

    def __init__(self, **kwargs):
        """Initialize settings and ensure directories."""
        super().__init__(**kwargs)
        self.paths.ensure_directories()

    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"

    def get_log_config(self) -> dict:
        """Get logging configuration dict."""
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "console": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                },
                "json": {
                    "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                    "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": self.logging.format,
                    "level": self.logging.level
                }
            },
            "root": {
                "level": self.logging.level,
                "handlers": ["console"]
            }
        }

        # Add file handler if specified
        if self.logging.file:
            config["handlers"]["file"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": self.logging.format,
                "filename": str(self.logging.file),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "level": self.logging.level
            }
            config["root"]["handlers"].append("file")

        return config


# Global settings instance
settings = Settings()


# Configuration manager for backward compatibility
class ConfigManager:
    """Configuration manager for backward compatibility."""

    @classmethod
    def load_config(cls) -> Settings:
        """Load configuration settings."""
        return settings

    @classmethod
    def get_settings(cls) -> Settings:
        """Get settings instance."""
        return settings
