"""Abstract message transport for agent-to-agent communication.

``MessageBus`` is the contract the base ``Agent`` class (and, later, the
Supervisor) uses to publish, send, and request/response over
``AgentMessage`` envelopes. Task #7/#9 replace ``InProcessMessageBus`` with a
RabbitMQ-backed implementation (topic exchange for broadcasts, direct
exchange for supervisor->agent commands — see ``protocol.EXCHANGE_EVENTS``
and ``protocol.EXCHANGE_COMMANDS``); nothing built against this interface
needs to change when that lands.

``InProcessMessageBus`` is a real, working asyncio-based implementation
(not a stub) — it's what makes the framework testable without infrastructure,
and is also a legitimate "single-process/local dev" mode.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from .protocol import AgentMessage, AgentRole

MessageHandler = Callable[[AgentMessage], Awaitable[AgentMessage | None]]


class MessageBus(ABC):
    """Abstract pub/sub + request/response transport for ``AgentMessage``."""

    @abstractmethod
    def subscribe(self, role: AgentRole, handler: MessageHandler) -> None:
        """Register the handler that receives messages addressed to ``role``."""

    @abstractmethod
    async def send(self, message: AgentMessage) -> None:
        """Deliver ``message`` to its ``recipient`` (or broadcast if None)."""

    @abstractmethod
    async def request(self, message: AgentMessage, *, timeout: float = 10.0) -> AgentMessage:
        """Send ``message`` and await the reply correlated by ``correlation_id``."""


class InProcessMessageBus(MessageBus):
    """Asyncio in-process bus: real transport, zero external dependencies.

    Correlation model: ``request()`` registers a future keyed by the
    outgoing message's ``correlation_id``; the first message ``send()``'d
    with that same ``correlation_id`` resolves it (this is exactly what
    ``AgentMessage.reply()`` produces). This covers the common
    request/response and question/answer flows used by the base ``Agent``
    class.

    Not covered here: many-repliers-to-one-broadcast quorum collection
    (e.g. "ask all four analysts and wait for all four"). That's debate/
    fan-in logic that belongs to the Supervisor (task #5), which subscribes
    directly rather than using ``request()``.
    """

    def __init__(self) -> None:
        self._handlers: dict[AgentRole, MessageHandler] = {}
        self._pending: dict[str, asyncio.Future[AgentMessage]] = {}

    def subscribe(self, role: AgentRole, handler: MessageHandler) -> None:
        self._handlers[role] = handler

    async def send(self, message: AgentMessage) -> None:
        # Only treat this as resolving an outstanding request() if `message`
        # is itself a reply (i.e. produced via AgentMessage.reply(), which
        # always sets causation_id). Without this check, request()'s own
        # initial send of the *original* message would immediately resolve
        # its own future instead of being routed to the recipient's handler,
        # since it already carries the correlation_id being waited on.
        future = self._pending.get(message.correlation_id)
        if message.causation_id is not None and future is not None and not future.done():
            future.set_result(message)
            return

        targets = [message.recipient] if message.recipient is not None else list(self._handlers)
        for role in targets:
            handler = self._handlers.get(role)
            if handler is None:
                continue
            reply = await handler(message)
            if reply is not None:
                await self.send(reply)

    async def request(self, message: AgentMessage, *, timeout: float = 10.0) -> AgentMessage:
        loop = asyncio.get_running_loop()
        future: asyncio.Future[AgentMessage] = loop.create_future()
        self._pending[message.correlation_id] = future
        try:
            await self.send(message)
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            self._pending.pop(message.correlation_id, None)


__all__ = ["MessageBus", "InProcessMessageBus", "MessageHandler"]
