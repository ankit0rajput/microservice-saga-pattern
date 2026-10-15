from __future__ import annotations

from fastapi import HTTPException

from contracts.events import (
    EventEnvelope,
    EventType,
    InventoryRejectedPayload,
    InventoryReleaseRequestedPayload,
    InventoryReleasedPayload,
    InventoryReservedPayload,
    OrderCreatedPayload,
)
from services.inventory_service.app.broker import RabbitMQBroker
from services.inventory_service.app.models import InventoryProduct, ProductCreateRequest, ReservationRecord


class InventoryClass:
    def __init__(self, broker: RabbitMQBroker, service_name: str) -> None:
        self._broker = broker
        self._service_name = service_name
        self._products: dict[str, InventoryProduct] = {}
        self._reservations: dict[str, list[ReservationRecord]] = {}

    def seed_products(self) -> None:
        if self._products:
            return
        self.add_product(ProductCreateRequest(sku="SKU-CHAIR", name="Nordic Chair", available_quantity=8))
        self.add_product(ProductCreateRequest(sku="SKU-LAMP", name="Arc Lamp", available_quantity=5))
        self.add_product(ProductCreateRequest(sku="SKU-DESK", name="Standing Desk", available_quantity=3))

    def add_product(self, request: ProductCreateRequest) -> InventoryProduct:
        product = InventoryProduct(**request.model_dump())
        self._products[product.sku] = product
        return product

    def list_products(self) -> list[InventoryProduct]:
        return list(self._products.values())

    def get_product(self, sku: str) -> InventoryProduct:
        product = self._products.get(sku)
        if product is None:
            raise HTTPException(status_code=404, detail=f"Product {sku} not found")
        return product

    async def handle_event(self, event: EventEnvelope) -> None:
        if event.event_type is EventType.ORDER_CREATED:
            payload = OrderCreatedPayload.model_validate(event.payload)
            await self._reserve_inventory(payload)
            return

        if event.event_type is EventType.INVENTORY_RELEASE_REQUESTED:
            payload = InventoryReleaseRequestedPayload.model_validate(event.payload)
            await self._release_inventory(payload)

    async def _reserve_inventory(self, payload: OrderCreatedPayload) -> None:
        shortages: list[str] = []
        for item in payload.items:
            product = self._products.get(item.sku)
            if product is None:
                shortages.append(f"Unknown product {item.sku}")
                continue
            if product.available_quantity < item.quantity:
                shortages.append(f"Insufficient stock for {item.sku}")

        if shortages:
            rejected_payload = InventoryRejectedPayload(order_id=payload.order_id, reason="; ".join(shortages))
            await self._broker.publish(
                EventEnvelope(
                    event_type=EventType.INVENTORY_REJECTED,
                    correlation_id=payload.order_id,
                    source=self._service_name,
                    payload=rejected_payload.model_dump(),
                )
            )
            return

        reserved_lines: list[ReservationRecord] = []
        for item in payload.items:
            product = self._products[item.sku]
            product.available_quantity -= item.quantity
            product.reserved_quantity += item.quantity
            reserved_lines.append(ReservationRecord(sku=item.sku, quantity=item.quantity))
        self._reservations[payload.order_id] = reserved_lines

        reserved_payload = InventoryReservedPayload(
            order_id=payload.order_id,
            items=payload.items,
            total_amount=payload.total_amount,
            payment_token=payload.payment_token,
        )
        await self._broker.publish(
            EventEnvelope(
                event_type=EventType.INVENTORY_RESERVED,
                correlation_id=payload.order_id,
                source=self._service_name,
                payload=reserved_payload.model_dump(),
            )
        )

    async def _release_inventory(self, payload: InventoryReleaseRequestedPayload) -> None:
        reservations = self._reservations.pop(payload.order_id, [])
        for reservation in reservations:
            product = self._products[reservation.sku]
            product.available_quantity += reservation.quantity
            product.reserved_quantity -= reservation.quantity

        released_payload = InventoryReleasedPayload(order_id=payload.order_id, reason=payload.reason)
        await self._broker.publish(
            EventEnvelope(
                event_type=EventType.INVENTORY_RELEASED,
                correlation_id=payload.order_id,
                source=self._service_name,
                payload=released_payload.model_dump(),
            )
        )
