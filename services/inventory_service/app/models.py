from __future__ import annotations

from pydantic import BaseModel, Field


class ProductCreateRequest(BaseModel):
    sku: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    available_quantity: int = Field(..., ge=0)


class InventoryProduct(BaseModel):
    sku: str
    name: str
    available_quantity: int
    reserved_quantity: int = 0


class ReservationRecord(BaseModel):
    sku: str
    quantity: int
