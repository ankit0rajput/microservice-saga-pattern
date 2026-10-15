from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException

from contracts.events import (
    EventEnvelope,
    EventType,
    InventoryReservedPayload,
    PaymentCompletedPayload,
    PaymentFailedPayload,
)
from services.payment_service.app.broker import RabbitMQBroker
from services.payment_service.app.models import PaymentRecord


class PaymentClass:
    def __init__(self, broker: RabbitMQBroker, service_name: str) -> None:
        self._broker = broker
        self._service_name = service_name
        self._payments: dict[str, PaymentRecord] = {}

    def list_payments(self) -> list[PaymentRecord]:
        return list(self._payments.values())

    def get_payment(self, order_id: str) -> PaymentRecord:
        payment = self._payments.get(order_id)
        if payment is None:
            raise HTTPException(status_code=404, detail="Payment not found")
        return payment

    async def handle_event(self, event: EventEnvelope) -> None:
        if event.event_type is not EventType.INVENTORY_RESERVED:
            return

        payload = InventoryReservedPayload.model_validate(event.payload)
        amount = payload.total_amount

        if payload.payment_token.lower().endswith("fail"):
            payment = PaymentRecord(
                order_id=payload.order_id,
                amount=amount,
                status="FAILED",
                reason="Payment gateway declined token",
            )
            self._payments[payload.order_id] = payment
            failed_payload = PaymentFailedPayload(
                order_id=payload.order_id,
                amount=amount,
                reason=payment.reason or "Payment failed",
            )
            await self._broker.publish(
                EventEnvelope(
                    event_type=EventType.PAYMENT_FAILED,
                    correlation_id=payload.order_id,
                    source=self._service_name,
                    payload=failed_payload.model_dump(),
                )
            )
            return

        payment = PaymentRecord(
            order_id=payload.order_id,
            amount=amount,
            status="COMPLETED",
            transaction_id=f"TX-{uuid4().hex[:10].upper()}",
        )
        self._payments[payload.order_id] = payment
        completed_payload = PaymentCompletedPayload(
            order_id=payload.order_id,
            amount=amount,
            transaction_id=payment.transaction_id or "",
        )
        await self._broker.publish(
            EventEnvelope(
                event_type=EventType.PAYMENT_COMPLETED,
                correlation_id=payload.order_id,
                source=self._service_name,
                payload=completed_payload.model_dump(),
            )
        )
