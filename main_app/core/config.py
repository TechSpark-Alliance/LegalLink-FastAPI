from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "LegalLink FastAPI"
    admin_email: str = ""
    items_per_page: int = 50
    database_url: str = "postgresql://user:password@localhost/dbname"
    secret_key: str = "your-secret-key-here"
    debug: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def DATABASE_URL(self) -> str:
        return self.database_url


settings = Settings()