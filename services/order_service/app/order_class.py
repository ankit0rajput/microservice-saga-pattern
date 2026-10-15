from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException

from contracts.events import (
    EventEnvelope,
    EventType,
    InventoryReleaseRequestedPayload,
    OrderCreatedPayload,
)
from services.order_service.app.broker import RabbitMQBroker
from services.order_service.app.models import CreateOrderRequest, OrderRecord, OrderStatus


class OrderClass:
    def __init__(self, broker: RabbitMQBroker, service_name: str) -> None:
        self._broker = broker
        self._service_name = service_name
        self._orders: dict[str, OrderRecord] = {}

    async def create_order(self, request: CreateOrderRequest) -> OrderRecord:
        order_id = str(uuid4())
        total_amount = round(sum(item.unit_price * item.quantity for item in request.items), 2)
        order = OrderRecord(
            order_id=order_id,
            customer_id=request.customer_id,
            items=request.items,
            total_amount=total_amount,
            payment_token=request.payment_token,
            status=OrderStatus.PENDING,
            saga_steps=["Order created"],
        )
        self._orders[order_id] = order

        payload = OrderCreatedPayload(
            order_id=order_id,
            customer_id=request.customer_id,
            items=request.items,
            total_amount=total_amount,
            payment_token=request.payment_token,
        )
        await self._broker.publish(
            EventEnvelope(
                event_type=EventType.ORDER_CREATED,
                correlation_id=order_id,
                source=self._service_name,
                payload=payload.model_dump(),
            )
        )
        return order

    def list_orders(self) -> list[OrderRecord]:
        return list(self._orders.values())

    def get_order(self, order_id: str) -> OrderRecord:
        order = self._orders.get(order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return order

    async def handle_event(self, event: EventEnvelope) -> None:
        order = self._orders.get(event.correlation_id)
        if order is None:
            return

        if event.event_type is EventType.INVENTORY_RESERVED:
            order.status = OrderStatus.INVENTORY_RESERVED
            order.saga_steps.append("Inventory reserved")
            return

        if event.event_type is EventType.INVENTORY_REJECTED:
            order.status = OrderStatus.INVENTORY_REJECTED
            order.saga_steps.append(f"Inventory rejected: {event.payload['reason']}")
            return

        if event.event_type is EventType.PAYMENT_COMPLETED:
            order.status = OrderStatus.PAYMENT_COMPLETED
            order.saga_steps.append(f"Payment completed: {event.payload['transaction_id']}")
            return

        if event.event_type is EventType.PAYMENT_FAILED:
            order.status = OrderStatus.PAYMENT_FAILED
            order.saga_steps.append(f"Payment failed: {event.payload['reason']}")
            release_payload = InventoryReleaseRequestedPayload(
                order_id=order.order_id,
                reason=event.payload["reason"],
            )
            await self._broker.publish(
                EventEnvelope(
                    event_type=EventType.INVENTORY_RELEASE_REQUESTED,
                    correlation_id=order.order_id,
                    source=self._service_name,
                    payload=release_payload.model_dump(),
                )
            )
            return

        if event.event_type is EventType.INVENTORY_RELEASED:
            order.status = OrderStatus.CANCELLED
            order.saga_steps.append("Inventory released and order cancelled")
