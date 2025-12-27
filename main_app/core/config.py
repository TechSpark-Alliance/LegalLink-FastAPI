from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LegalLink FastAPI"
    admin_email: str = ""
    items_per_page: int = 50
    secret_key: str = "your-secret-key-here"
    debug: bool = True

    # Server metadata
    app_env: str = "development"
    allowed_hosts: str = "localhost,127.0.0.1"
    port: int = 8000

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "legallink"

    brevo_api_key: str = ""
    sender_email: str = "noreply@legallink.com"
    sender_name: str = "LegalLink"

    stripe_secret_key: str = "" # STRIPE_SECRET_KEY
    stripe_webhook_secret: str = "" # STRIPE_WEBHOOK_SECRET
    stripe_price_id: str = "" # STRIPE_PRICE_ID
    stripe_success_url: str = "http://localhost:5173/lawyer/profile"
    stripe_cancel_url: str = "http://localhost:5173/lawyer/profile"
    stripe_portal_return_url: str = "http://localhost:5173/lawyer/profile"
    stripe_trial_days: int = 30

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


settings = Settings()
