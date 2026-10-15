from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException

from contracts.auth import TokenRequest, TokenResponse, build_auth_dependency, create_access_token
from contracts.events import EventEnvelope
from contracts.middleware import add_request_middleware
from services.order_service.app.broker import RabbitMQBroker
from services.order_service.app.config import OrderServiceSettings
from services.order_service.app.models import CreateOrderRequest
from services.order_service.app.order_class import OrderClass


settings = OrderServiceSettings()
broker = RabbitMQBroker(settings.amqp_url, settings.exchange_name, queue_name="order-service.queue")
order_class = OrderClass(broker, settings.service_name)
require_user = build_auth_dependency(settings.auth_secret_key, settings.auth_issuer)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await broker.connect()
    await broker.bind(["inventory.*", "payment.*"])

    async def handle_event(event: EventEnvelope) -> None:
        await order_class.handle_event(event)

    await broker.consume(handle_event)
    yield
    await broker.close()


app = FastAPI(
    title="Order Service",
    version="1.0.0",
    summary="Dedicated order microservice for choreography-based saga",
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


@app.post("/orders", dependencies=[Depends(require_user)])
async def create_order(request: CreateOrderRequest):
    return await order_class.create_order(request)


@app.get("/orders", dependencies=[Depends(require_user)])
async def list_orders():
    return order_class.list_orders()


@app.get("/orders/{order_id}", dependencies=[Depends(require_user)])
async def get_order(order_id: str):
    return order_class.get_order(order_id)
