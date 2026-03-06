"""Actor inbox protocol and implementation.

This module defines the interface for actor message queues and provides
an asyncio-based implementation.
"""

from __future__ import annotations

import asyncio

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from async_pykka._envelope import Envelope

__all__ = ['ActorInbox', 'AsyncioActorInbox']


class ActorInbox(Protocol):
    """Actor inbox interface.

    Defines the protocol for actor message queues. Implementations must
    provide thread-safe (or async-safe) message passing.

    Raises:
        asyncio.QueueEmpty: get_nowait() raises when queue is empty
    """

    def put(self, envelope: Envelope[Any], /) -> None:
        """Put a message into the inbox (non-blocking).

        Args:
            envelope: The message envelope to put
        """
        ...

    async def get(self) -> Envelope[Any]:
        """Get a message from the inbox (async blocking).

        Returns:
            The next message envelope
        """
        ...

    def get_nowait(self) -> Envelope[Any]:
        """Get a message from the inbox (non-blocking).

        Returns:
            The next message envelope

        Raises:
            asyncio.QueueEmpty: If the queue is empty
        """
        ...

    def empty(self) -> bool:
        """Check if the inbox is empty.

        Returns:
            True if empty, False otherwise
        """
        ...


class AsyncioActorInbox:
    """Asyncio-based actor inbox implementation.

    Uses asyncio.Queue for message passing within a single event loop.
    """

    def __init__(self) -> None:
        """Initialize the inbox with an asyncio.Queue."""
        self._queue: asyncio.Queue[Envelope[Any]] = asyncio.Queue()

    def put(self, envelope: Envelope[Any]) -> None:
        """Put a message into the inbox (non-blocking).

        Uses put_nowait since we're always within the same event loop.

        Args:
            envelope: The message envelope to put
        """
        self._queue.put_nowait(envelope)

    async def get(self) -> Envelope[Any]:
        """Get a message from the inbox (async blocking).

        Returns:
            The next message envelope
        """
        return await self._queue.get()

    def get_nowait(self) -> Envelope[Any]:
        """Get a message from the inbox (non-blocking).

        Returns:
            The next message envelope

        Raises:
            asyncio.QueueEmpty: If the queue is empty
        """
        return self._queue.get_nowait()

    def empty(self) -> bool:
        """Check if the inbox is empty.

        Returns:
            True if empty, False otherwise
        """
        return self._queue.empty()
