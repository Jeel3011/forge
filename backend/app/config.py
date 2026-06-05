from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    github_token: str = ""
    database_url: str = "postgresql://forge:forge@localhost:5432/forge"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "dev-secret-key"
    debug: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
