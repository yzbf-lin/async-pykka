"""ActorRef - Reference to a running actor.

This module provides the ActorRef class for safely communicating with actors.
"""

from __future__ import annotations

import asyncio
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Optional,
    TypeVar,
)

from async_pykka._exceptions import ActorDeadError
from async_pykka._envelope import Envelope
from async_pykka.messages import _ActorStop

if TYPE_CHECKING:
    from async_pykka._actor import Actor, AsyncioFuture
    from async_pykka._event import AsyncioEvent
    from async_pykka._future import Future
    from async_pykka._inbox import ActorInbox
    from async_pykka._proxy import ActorProxy

__all__ = ["ActorRef"]


A = TypeVar("A", bound="Actor")


class ActorRef(Generic[A]):
    """Reference to a running actor which may safely be passed around.

    :class:`ActorRef` instances are returned by :meth:`Actor.start` and the
    lookup methods in :class:`ActorRegistry <async_pykka.ActorRegistry>`. You should
    never need to create :class:`ActorRef` instances yourself.

    All operations must be performed within the same event loop that the actor
    was created in. Cross-thread or cross-loop calls will raise RuntimeError.

    :param actor: the actor to wrap
    :type actor: :class:`Actor`
    """

    #: The class of the referenced actor.
    actor_class: type[A]

    #: See :attr:`Actor.actor_urn`.
    actor_urn: str

    #: See :attr:`Actor.actor_inbox`.
    actor_inbox: ActorInbox

    #: See :attr:`Actor.actor_stopped`.
    actor_stopped: AsyncioEvent

    #: The event loop this actor ref is bound to.
    _loop: asyncio.AbstractEventLoop

    def __init__(
        self,
        actor: A,
    ) -> None:
        self._actor = actor
        self._loop = actor._loop  # Inherit the actor's loop
        self.actor_class = actor.__class__
        self.actor_urn = actor.actor_urn
        self.actor_inbox = actor.actor_inbox
        self.actor_stopped = actor.actor_stopped

    def __repr__(self) -> str:
        return f"<ActorRef for {self}>"

    def __str__(self) -> str:
        return f"{self.actor_class.__name__} ({self.actor_urn})"

    def _check_loop(self) -> None:
        """Validate that we're being called from the correct event loop.

        Raises:
            RuntimeError: If called from outside an event loop or from a
                different event loop than the one the actor is bound to.
        """
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            raise RuntimeError(
                f"Cannot call {self} outside of a running event loop."
            ) from None

        if current_loop is not self._loop:
            raise RuntimeError(
                f"Cannot call {self} from a different event loop. "
                f"Actor is bound to {self._loop!r}, but current loop is {current_loop!r}."
            )

    def is_alive(self) -> bool:
        """Check if actor is alive.

        This is based on the actor's stopped flag. The actor is not guaranteed
        to be alive and responding even though :meth:`is_alive` returns
        :class:`True`.

        :return:
            Returns :class:`True` if actor is alive, :class:`False` otherwise.
        """
        return not self.actor_stopped.is_set()

    def tell(
        self,
        message: Any,
    ) -> None:
        """Send message to actor without waiting for any response.

        Will generally not block, but if the underlying queue is full it will
        block until a free slot is available.

        Must be called from within the same event loop as the actor.

        :param message: message to send
        :type message: any

        :raise: :exc:`RuntimeError` if called from wrong event loop
        :raise: :exc:`async_pykka.ActorDeadError` if actor is not available
        :return: nothing
        """
        self._check_loop()

        if not self.is_alive():
            msg = f"{self} not found"
            raise ActorDeadError(msg)
        self.actor_inbox.put(Envelope(message))

    def ask(
        self,
        message: Any,
    ) -> Future[Any]:
        """Send message to actor and return a Future for the reply.

        The message can be of any type. Returns a :class:`Future` that can
        be awaited to get the result.

        Must be called from within the same event loop as the actor.

        Usage::

            # Direct await
            result = await actor_ref.ask(msg)

            # With timeout
            future = actor_ref.ask(msg)
            result = await future.get(timeout=5.0)

        :param message: message to send
        :type message: any

        :raise: :exc:`RuntimeError` if called from wrong event loop
        :return: :class:`async_pykka.Future` containing the response
        """
        self._check_loop()

        future: AsyncioFuture = self.actor_class._create_future()  # noqa: SLF001

        try:
            if not self.is_alive():
                msg = f"{self} not found"
                raise ActorDeadError(msg)  # noqa: TRY301
        except ActorDeadError:
            future.set_exception()
        else:
            self.actor_inbox.put(Envelope(message, reply_to=future))

        return future

    def stop(
        self,
    ) -> Future[bool]:
        """Send a message to the actor, asking it to stop.

        The returned future contains :class:`True` if actor is stopped
        or was being stopped at the time of the call. :class:`False`
        if actor was already dead.

        Messages sent to the actor before the actor is asked to stop will
        be processed normally before it stops.

        Messages sent to the actor after the actor is asked to stop will
        be replied to with :exc:`async_pykka.ActorDeadError` after it stops.

        The actor may not be restarted.

        Must be called from within the same event loop as the actor.

        Usage::

            success = await actor_ref.stop()

        :raise: :exc:`RuntimeError` if called from wrong event loop
        :return: :class:`async_pykka.Future` containing a boolean
        """
        self._check_loop()

        ask_future = self.ask(_ActorStop())

        async def _stop_result_converter(timeout: Optional[float]) -> bool:
            try:
                await ask_future.get(timeout=timeout)
            except ActorDeadError:
                return False
            else:
                return True

        converted_future = ask_future.__class__()
        converted_future.set_get_hook(_stop_result_converter)

        return converted_future

    def proxy(self: ActorRef[A]) -> ActorProxy[A]:
        """Wrap the :class:`ActorRef` in an :class:`ActorProxy`.

        Using this method like this::

            proxy = AnActor.start().proxy()

        is analogous to::

            proxy = ActorProxy(actor_ref=AnActor.start())

        :raise: :exc:`async_pykka.ActorDeadError` if actor is not available
        :return: :class:`async_pykka.ActorProxy`
        """
        from async_pykka._proxy import ActorProxy
        return ActorProxy(actor_ref=self)
