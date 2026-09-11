from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MARKET_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://market:market@postgres:5432/market"
    redis_url: str = "redis://redis:6379/0"
    stripe_secret_key: str = "sk_test_replace_me"
    stripe_webhook_secret: str = "whsec_replace_me"
    platform_fee_bps: int = 500
    webhook_max_attempts: int = 8

