from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException

from contracts.auth import TokenRequest, TokenResponse, build_auth_dependency, create_access_token
from contracts.events import EventEnvelope
from contracts.middleware import add_request_middleware
from services.payment_service.app.broker import RabbitMQBroker
from services.payment_service.app.config import PaymentServiceSettings
from services.payment_service.app.payment_class import PaymentClass


settings = PaymentServiceSettings()
broker = RabbitMQBroker(settings.amqp_url, settings.exchange_name, queue_name="payment-service.queue")
payment_class = PaymentClass(broker, settings.service_name)
require_user = build_auth_dependency(settings.auth_secret_key, settings.auth_issuer)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await broker.connect()
    await broker.bind(["inventory.reserved"])

    async def handle_event(event: EventEnvelope) -> None:
        await payment_class.handle_event(event)

    await broker.consume(handle_event)
    yield
    await broker.close()


app = FastAPI(
    title="Payment Service",
    version="1.0.0",
    summary="Dedicated payment microservice for choreography-based saga",
    lifespan=lifespan,
)
add_request_middleware(app, settings.service_name)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name, "pattern": "choreography"}


@app.post("/auth/token", response_model=TokenResponse)
async def issue_token(request: TokenRequest) -> TokenResponse:
    if request.username != settings.auth_demo_username or request.password != settings.auth_demo_password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(
        subject=request.username,
        secret_key=settings.auth_secret_key,
        issuer=settings.auth_issuer,
        expires_minutes=settings.auth_token_minutes,
    )
    return TokenResponse(access_token=token)


@app.get("/payments", dependencies=[Depends(require_user)])
async def list_payments():
    return payment_class.list_payments()


@app.get("/payments/{order_id}", dependencies=[Depends(require_user)])
async def get_payment(order_id: str):
    return payment_class.get_payment(order_id)