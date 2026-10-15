from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

import aio_pika

from contracts.events import EventEnvelope, EventType


EventHandler = Callable[[EventEnvelope], Awaitable[None]]


class RabbitMQBroker:
    def __init__(self, amqp_url: str, exchange_name: str, queue_name: str) -> None:
        self._amqp_url = amqp_url
        self._exchange_name = exchange_name
        self._queue_name = queue_name
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.abc.AbstractRobustChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None
        self._queue: aio_pika.abc.AbstractQueue | None = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self._amqp_url)
        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(
            self._exchange_name,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )
        self._queue = await self._channel.declare_queue(self._queue_name, durable=True)

    async def bind(self, routing_keys: list[str]) -> None:
        if self._queue is None or self._exchange is None:
            raise RuntimeError("Broker is not connected")
        for routing_key in routing_keys:
            await self._queue.bind(self._exchange, routing_key)

    async def publish(self, envelope: EventEnvelope) -> None:
        if self._exchange is None:
            raise RuntimeError("Broker is not connected")

        message = aio_pika.Message(
            body=envelope.model_dump_json().encode("utf-8"),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await self._exchange.publish(message, routing_key=envelope.event_type.value)

    async def consume(self, handler: EventHandler) -> None:
        if self._queue is None:
            raise RuntimeError("Broker is not connected")

        async def wrapped(message: aio_pika.abc.AbstractIncomingMessage) -> None:
            async with message.process():
                data = json.loads(message.body.decode("utf-8"))
                await handler(EventEnvelope.model_validate(data))

        await self._queue.consume(wrapped)

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
