from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    app_name: str = "Sistema de Procesamiento de Órdenes"
    debug: bool = True
    database_url: str = "sqlite:///./orders.db"
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    class Config:
        env_file = ".env"

settings = Settings()