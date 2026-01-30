from pathlib import Path
from urllib.parse import quote

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).parent


class DbConfig(BaseSettings):
    """Конфигурация подключения к БД"""
    
    prod_db: bool = Field(default=False)
    host: str = Field(default="localhost")
    port: str = Field(default="5432")
    name: str = Field(default="myapp")
    user: str = Field(default="postgres")
    password: str = Field(default="password")
    sqlite_path: str = Field(default="database.db")
    model_config = SettingsConfigDict(
        env_prefix="db_",  
    )
    @property
    def database_url(self) -> str:
        """
        Формирует строку подключения к БД
        
        Returns:
            URL для подключения к PostgreSQL или SQLite в зависимости от режима.
        """
        if self.prod_db:
            password = quote(self.password)
            return (
                f"postgresql+asyncpg://{self.user}:{password}@"
                f"{self.host}:{self.port}/{self.name}"
            )
        return f"sqlite+aiosqlite:///{BASE_DIR / self.sqlite_path}"


class BotConfig(BaseSettings):
    """Конфигурация тг бота"""
    model_config = SettingsConfigDict(
        env_prefix="tg_", 
    )
    
    token: str = Field(default="")


class Config(BaseSettings):
    """Основной класс конфигурации"""
    
    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__", 
    )
    
    db: DbConfig = Field(default_factory=DbConfig)
    tg: BotConfig = Field(default_factory=BotConfig)


config = Config()