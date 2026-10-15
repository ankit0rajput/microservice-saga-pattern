from pydantic_settings import BaseSettings, SettingsConfigDict


class PaymentServiceSettings(BaseSettings):
    service_name: str = "payment-service"
    service_port: int = 8003
    amqp_url: str = "amqp://guest:guest@localhost:5672/"
    exchange_name: str = "ecommerce.events"
    auth_secret_key: str = "dev-auth-secret"
    auth_issuer: str = "pdftoexcel-ecommerce"
    auth_demo_username: str = "demo"
    auth_demo_password: str = "demo123"
    auth_token_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
