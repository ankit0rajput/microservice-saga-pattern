from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from contracts.events import OrderItem


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    INVENTORY_RESERVED = "INVENTORY_RESERVED"
    INVENTORY_REJECTED = "INVENTORY_REJECTED"
    PAYMENT_COMPLETED = "PAYMENT_COMPLETED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    CANCELLED = "CANCELLED"


class CreateOrderRequest(BaseModel):
    customer_id: str = Field(..., min_length=1)
    items: list[OrderItem] = Field(..., min_length=1)
    payment_token: str = Field(..., min_length=1)


class OrderRecord(BaseModel):
    order_id: str
    customer_id: str
    items: list[OrderItem]
    total_amount: float
    payment_token: str
    status: OrderStatus
    saga_steps: list[str]
