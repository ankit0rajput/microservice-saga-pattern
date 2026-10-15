from __future__ import annotations

from pydantic import BaseModel


class PaymentRecord(BaseModel):
    order_id: str
    amount: float
    status: str
    transaction_id: str | None = None
    reason: str | None = None
