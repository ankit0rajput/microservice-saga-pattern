from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException

from contracts.auth import TokenRequest, TokenResponse, build_auth_dependency, create_access_token
from contracts.events import EventEnvelope
from contracts.middleware import add_request_middleware
from services.inventory_service.app.broker import RabbitMQBroker
from services.inventory_service.app.config import InventoryServiceSettings
from services.inventory_service.app.inventory_class import InventoryClass
from services.inventory_service.app.models import ProductCreateRequest


settings = InventoryServiceSettings()
broker = RabbitMQBroker(settings.amqp_url, settings.exchange_name, queue_name="inventory-service.queue")
inventory_class = InventoryClass(broker, settings.service_name)
inventory_class.seed_products()
require_user = build_auth_dependency(settings.auth_secret_key, settings.auth_issuer)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await broker.connect()
    await broker.bind(["order.created", "inventory.release.requested"])

    async def handle_event(event: EventEnvelope) -> None:
        await inventory_class.handle_event(event)

    await broker.consume(handle_event)
    yield
    await broker.close()


app = FastAPI(
    title="Inventory Service",
    version="1.0.0",
    summary="Dedicated inventory microservice for choreography-based saga",
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


@app.get("/products", dependencies=[Depends(require_user)])
async def list_products():
    return inventory_class.list_products()


@app.get("/products/{sku}", dependencies=[Depends(require_user)])
async def get_product(sku: str):
    return inventory_class.get_product(sku)


@app.post("/products", dependencies=[Depends(require_user)])
async def add_product(request: ProductCreateRequest):
    return inventory_class.add_product(request)
