# FastAPI E-Commerce Saga Microservices

This repository is now organized as independently deployable FastAPI microservices for an e-commerce `create order` flow using the Saga pattern with choreography.

## Services

- `order-service`: owns order creation and order state transitions.
- `inventory-service`: owns stock reservation and compensation.
- `payment-service`: owns payment success and failure handling.
- `rabbitmq`: event broker used by all services.

Each service has its own:

- FastAPI application entrypoint
- requirements file
- Dockerfile
- internal classes and models

## Service Classes

- `OrderClass` in `services/order_service/app/order_class.py`
- `InventoryClass` in `services/inventory_service/app/inventory_class.py`
- `PaymentClass` in `services/payment_service/app/payment_class.py`

## Choreography Flow

1. `order-service` accepts `POST /orders` and publishes `order.created`.
2. `inventory-service` consumes `order.created` and publishes either `inventory.reserved` or `inventory.rejected`.
3. `payment-service` consumes `inventory.reserved` and publishes either `payment.completed` or `payment.failed`.
4. `order-service` consumes `payment.failed` and publishes `inventory.release.requested`.
5. `inventory-service` consumes `inventory.release.requested` and publishes `inventory.released`.
6. `order-service` consumes `inventory.released` and marks the order as cancelled.

This keeps the saga decentralized. Later, this can be replaced or supplemented with an orchestration service.

## Layout

- `contracts/`: shared event schemas and routing keys for the monorepo.
- `services/order_service/`: dedicated order microservice.
- `services/inventory_service/`: dedicated inventory microservice.
- `services/payment_service/`: dedicated payment microservice.
- `compose.yaml`: local multi-container composition with RabbitMQ.

## Run Locally With Containers

```powershell
docker compose up --build
```

Endpoints:

- `http://localhost:8001/docs` for order-service
- `http://localhost:8002/docs` for inventory-service
- `http://localhost:8003/docs` for payment-service
- `http://localhost:15672` for RabbitMQ management

## Run Services Individually

Install each service independently:

```powershell
pip install -r services/order_service/requirements.txt
pip install -r services/inventory_service/requirements.txt
pip install -r services/payment_service/requirements.txt
```

Then start each app separately:

```powershell
uvicorn services.order_service.app.main:app --port 8001
uvicorn services.inventory_service.app.main:app --port 8002
uvicorn services.payment_service.app.main:app --port 8003
```

Each service expects a RabbitMQ broker at `AMQP_URL`. Override configuration with environment variables when deploying to the cloud.

## Authentication

Every API now requires a JWT bearer token on protected endpoints. The token is issued by the same service through `POST /auth/token` using the demo credentials below.

Demo credentials:

- username: `demo`
- password: `demo123`

Example flow:

1. Call `POST /auth/token` on any service.
2. Copy the returned `access_token`.
3. Send `Authorization: Bearer <access_token>` to the protected endpoints.

Protected endpoints are all business routes such as `/orders`, `/products`, and `/payments`. The `/health` endpoints stay open.

For production, replace the demo login with a real identity provider such as Azure AD, Cognito, Auth0, or Keycloak and keep the same bearer-token validation pattern in each service.

## Middleware

Each service includes HTTP middleware that:

- generates or forwards `X-Request-Id`
- adds `X-Service-Name` and `X-Process-Time-Ms` response headers
- logs request start and end events for tracing

This is useful for debugging distributed requests across the three services while keeping the services independently deployable.

## Example Order Request

The order service accepts price information as part of the request so it does not need a synchronous dependency on inventory for total calculation.

```json
{
  "customer_id": "customer-42",
  "items": [
    {"sku": "SKU-CHAIR", "quantity": 1, "unit_price": 120.0},
    {"sku": "SKU-LAMP", "quantity": 1, "unit_price": 80.0}
  ],
  "payment_token": "tok-success"
}
```

Use a payment token ending in `fail` to trigger compensation.

## Cloud Deployment Notes

- Build and deploy each service image independently.
- Point all services to the same RabbitMQ cluster or managed broker.
- Replace the in-memory dictionaries with service-owned databases before production deployment.
- Keep event contracts backward compatible because choreography depends on stable messages.