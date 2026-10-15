from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    ORDER_CREATED = "order.created"
    INVENTORY_RESERVED = "inventory.reserved"
    INVENTORY_REJECTED = "inventory.rejected"
    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_FAILED = "payment.failed"
    INVENTORY_RELEASE_REQUESTED = "inventory.release.requested"
    INVENTORY_RELEASED = "inventory.released"


class OrderItem(BaseModel):
    sku: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)


class OrderCreatedPayload(BaseModel):
    order_id: str
    customer_id: str
    items: list[OrderItem]
    total_amount: float
    payment_token: str


class InventoryReservedPayload(BaseModel):
    order_id: str
    items: list[OrderItem]
    total_amount: float
    payment_token: str


class InventoryRejectedPayload(BaseModel):
    order_id: str
    reason: str


class PaymentCompletedPayload(BaseModel):
    order_id: str
    amount: float
    transaction_id: str


class PaymentFailedPayload(BaseModel):
    order_id: str
    amount: float
    reason: str


class InventoryReleaseRequestedPayload(BaseModel):
    order_id: str
    reason: str


class InventoryReleasedPayload(BaseModel):
    order_id: str
    reason: str


class EventEnvelope(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: EventType
    correlation_id: str
    source: str
    payload: dict[str, Any]
