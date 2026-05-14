from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    environment: str = Field(default="development")
    debug: bool = Field(default=False)

    secret_key: str = Field(default="dev-secret-key-not-for-production")
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    database_url: str = Field(
        default="postgresql+asyncpg://sk6:devpassword@pgbouncer:6432/sk6"
    )
    redis_url: str = Field(default="redis://:devpassword@redis:6379/0")

    rustfs_endpoint: str = "http://rustfs:9000"
    rustfs_access_key: str = "devaccess"
    rustfs_secret_key: str = "devsecret123"
    rustfs_bucket: str = "sk6-static"

    otp_length: int = 6
    otp_expiry_minutes: int = 5

    @property
    def is_dev(self) -> bool:
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
