"""ActorRegistry - Global registry for all running actors.

This module provides the ActorRegistry class for managing running actors.
"""

from __future__ import annotations

import asyncio
import logging

from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    TypeVar,
)

if TYPE_CHECKING:
    from async_pykka._actor import Actor
    from async_pykka._ref import ActorRef

__all__ = ['ActorRegistry']


logger = logging.getLogger('pykka')


A = TypeVar('A', bound='Actor')


class ActorRegistry:
    """Registry which provides easy access to all running actors.

    Contains global state. Supports multiple event loops - each actor is
    bound to the event loop it was created in.

    Note: In environments like Celery workers with gevent, actors from
    different event loops may coexist. Use :meth:`get_by_loop` to filter
    actors by their bound loop.
    """

    _actor_refs: ClassVar[list[ActorRef[Any]]] = []

    @classmethod
    def _get_running_loop(cls) -> asyncio.AbstractEventLoop:
        """Get the current running event loop.

        Raises:
            RuntimeError: If called from outside an event loop.
        """
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            raise RuntimeError('ActorRegistry methods must be called within a running event loop.') from None

    @classmethod
    def get_by_loop(
        cls,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> list[ActorRef[Any]]:
        """Get all actors bound to the specified event loop.

        :param loop: the event loop to filter by, or None for current loop
        :type loop: asyncio.AbstractEventLoop or None

        :returns: list of :class:`async_pykka.ActorRef` bound to the loop
        """
        if loop is None:
            loop = cls._get_running_loop()
        return [ref for ref in cls._actor_refs if ref._loop is loop]

    @classmethod
    def broadcast(
        cls,
        message: Any,
        target_class: str | type[Actor] | None = None,
    ) -> None:
        """Broadcast ``message`` to all actors of the specified ``target_class``.

        Only broadcasts to actors bound to the current event loop.

        If no ``target_class`` is specified, the message is broadcasted to all
        actors in the current loop.

        Note: This method inherits loop validation from ActorRef.tell().

        :param message: the message to send
        :type message: any

        :param target_class: optional actor class to broadcast the message to
        :type target_class: class or class name
        """
        current_loop = cls._get_running_loop()

        if isinstance(target_class, str):
            targets = cls.get_by_class_name(target_class)
        elif target_class is not None:
            targets = cls.get_by_class(target_class)
        else:
            targets = cls.get_all()

        # Filter to only actors in current loop
        for ref in targets:
            if ref._loop is current_loop:
                ref.tell(message)
            else:
                logger.debug(f'Skipping broadcast to {ref} - bound to different event loop')

    @classmethod
    def get_all(cls) -> list[ActorRef[Any]]:
        """Get all running actors (across all event loops).

        :returns: list of :class:`async_pykka.ActorRef`
        """
        return cls._actor_refs[:]

    @classmethod
    def get_by_class(
        cls,
        actor_class: type[A],
    ) -> list[ActorRef[A]]:
        """Get all running actors of the given class or a subclass.

        :param actor_class: actor class, or any superclass of the actor
        :type actor_class: class

        :returns: list of :class:`async_pykka.ActorRef`
        """
        return [ref for ref in cls._actor_refs if issubclass(ref.actor_class, actor_class)]

    @classmethod
    def get_by_class_name(
        cls,
        actor_class_name: str,
    ) -> list[ActorRef[Any]]:
        """Get all running actors of the given class name.

        :param actor_class_name: actor class name
        :type actor_class_name: string

        :returns: list of :class:`async_pykka.ActorRef`
        """
        return [ref for ref in cls._actor_refs if ref.actor_class.__name__ == actor_class_name]

    @classmethod
    def get_by_urn(
        cls,
        actor_urn: str,
    ) -> ActorRef[Any] | None:
        """Get an actor by its universally unique URN.

        :param actor_urn: actor URN
        :type actor_urn: string

        :returns: :class:`async_pykka.ActorRef` or :class:`None` if not found
        """
        refs = [ref for ref in cls._actor_refs if ref.actor_urn == actor_urn]
        if not refs:
            return None
        return refs[0]

    @classmethod
    def register(
        cls,
        actor_ref: ActorRef[Any],
    ) -> None:
        """Register an :class:`ActorRef` in the registry.

        This is done automatically when an actor is started, e.g. by calling
        :meth:`Actor.start()`.

        :param actor_ref: reference to the actor to register
        :type actor_ref: :class:`async_pykka.ActorRef`
        """
        cls._actor_refs.append(actor_ref)
        logger.debug(f'Registered {actor_ref}')

    @classmethod
    async def stop_all(
        cls,
        timeout: float | None = None,
        *,
        current_loop_only: bool = True,
    ) -> list[bool]:
        """Stop all running actors.

        Must be called from within a running event loop.

        By default, only stops actors bound to the current event loop.
        This is safe for environments with multiple loops (e.g., Celery + gevent).

        The actors are guaranteed to be stopped in the reverse of the
        order they were started in. This is helpful if you have simple
        dependencies in between your actors, where it is sufficient to
        shut down actors in a LIFO manner: last started, first stopped.

        If you have more complex dependencies in between your actors, you
        should take care to shut them down in the required order yourself, e.g.
        by stopping dependees from a dependency's :meth:`on_stop()` method.

        :param timeout: seconds to wait for each actor to stop
        :type timeout: float or None

        :param current_loop_only: if True (default), only stop actors bound to
            the current event loop. If False, attempt to stop all actors
            (may fail for actors in other loops).
        :type current_loop_only: bool

        :raise: :exc:`RuntimeError` if called from outside an event loop
        :returns: A list of return values from :meth:`ActorRef.stop`.
        """
        current_loop = cls._get_running_loop()

        if current_loop_only:
            # Only stop actors in current loop
            refs_to_stop = [ref for ref in cls._actor_refs if ref._loop is current_loop]
            other_loop_count = len(cls._actor_refs) - len(refs_to_stop)
            if other_loop_count > 0:
                logger.warning(
                    f'stop_all: Skipping {other_loop_count} actor(s) bound to '
                    f'different event loop(s). Use current_loop_only=False to '
                    f'attempt stopping all actors.'
                )
        else:
            refs_to_stop = cls._actor_refs[:]

        results = []
        for ref in reversed(refs_to_stop):
            if ref._loop is current_loop:
                result = await ref.stop().get(timeout=timeout)
                results.append(result)
            else:
                # Actor is in different loop - cannot safely stop from here
                logger.warning(
                    f'Cannot stop {ref} from current loop - actor is bound to '
                    f'a different event loop. Stop it from its own loop.'
                )
                results.append(False)

        return results

    @classmethod
    def unregister(
        cls,
        actor_ref: ActorRef[A],
    ) -> None:
        """Remove an :class:`ActorRef` from the registry.

        This is done automatically when an actor is stopped, e.g. by calling
        :meth:`Actor.stop()`.

        :param actor_ref: reference to the actor to unregister
        :type actor_ref: :class:`async_pykka.ActorRef`
        """
        removed = False
        if actor_ref in cls._actor_refs:
            cls._actor_refs.remove(actor_ref)
            removed = True
        if removed:
            logger.debug(f'Unregistered {actor_ref}')
        else:
            logger.debug(f'Unregistered {actor_ref} (not found in registry)')
