import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Settings:
    database_url: str
    jwt_secret: str
    demo_password: str
    demo_username: str = "alumno"
    model_backend: str = "local"
    event_transport: str = "local"
    rabbit_url: str = ""
    aws_region: str = "us-east-1"
    endpoint_name: str = "ep3-preflop"
    rate_limit: int = 120
    environment: str = "development"

    @classmethod
    def from_env(cls):
        load_dotenv()
        values = cls(
            database_url=os.getenv("DATABASE_URL", "sqlite:///runtime/preflop.db"),
            jwt_secret=os.getenv("JWT_SECRET", ""), demo_password=os.getenv("DEMO_PASSWORD", ""),
            demo_username=os.getenv("DEMO_USERNAME", "alumno"),
            model_backend=os.getenv("MODEL_BACKEND", "local"),
            event_transport=os.getenv("EVENT_TRANSPORT", "local"), rabbit_url=os.getenv("RABBIT_URL", ""),
            aws_region=os.getenv("AWS_DEFAULT_REGION", "us-east-1"), endpoint_name=os.getenv("SAGEMAKER_ENDPOINT", "ep3-preflop"),
            rate_limit=int(os.getenv("RATE_LIMIT_PER_MINUTE", "120")), environment=os.getenv("APP_ENV", "development"))
        values.validate()
        return values

    def validate(self):
        if len(self.jwt_secret) < 32 or len(self.demo_password) < 12:
            raise ValueError("Genera .env con scripts/setup_local.py: secretos ausentes o demasiado cortos.")
        if self.model_backend not in {"local", "sagemaker"} or self.event_transport not in {"local", "rabbitmq"}:
            raise ValueError("Backend o transporte de eventos no soportado.")
        if self.environment == "production" and (self.model_backend != "sagemaker" or self.event_transport != "rabbitmq" or not self.database_url.startswith("postgresql")):
            raise ValueError("Produccion requiere SageMaker, RabbitMQ y PostgreSQL; no se permiten sustituciones locales.")
        if self.event_transport == "rabbitmq" and not self.rabbit_url:
            raise ValueError("Falta RABBIT_URL")

