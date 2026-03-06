"""Actor base class and asyncio implementation.

This module provides the base Actor class and AsyncioActor implementation
for the async_pykka actor framework.
"""

from __future__ import annotations

import abc
import asyncio
import inspect
import logging
import sys
import uuid

from typing import TYPE_CHECKING, Any, Self, TypeVar

from async_pykka import messages
from async_pykka._exceptions import ActorDeadError, Timeout
from async_pykka._future import Future  # Runtime import for inheritance
from async_pykka._inbox import ActorInbox, AsyncioActorInbox
from async_pykka._introspection import get_attr_directly

if TYPE_CHECKING:
    from types import TracebackType

    from async_pykka._envelope import Envelope
    from async_pykka._event import AsyncioEvent as AsyncioEventType
    from async_pykka._ref import ActorRef
    from async_pykka._types import OptExcInfo

__all__ = ['Actor', 'AsyncioActor', 'AsyncioFuture']


logger = logging.getLogger('pykka')


A = TypeVar('A', bound='Actor')
T = TypeVar('T')


class Actor(abc.ABC):
    """An actor is an execution unit that executes concurrently with other actors.

    To create an actor:

    1. subclass one of the :class:`Actor` implementations:

       - :class:`~async_pykka.AsyncioActor`

    2. implement your methods, including :meth:`__init__`, as usual,
    3. call :meth:`Actor.start` on your actor class, passing the method any
       arguments for your constructor.

    To stop an actor, call :meth:`Actor.stop()` or :meth:`ActorRef.stop()`.

    For example::

        import asyncio
        import async_pykka

        class MyActor(async_pykka.AsyncioActor):
            def __init__(self, my_arg=None):
                super().__init__()
                ... # My optional init code with access to start() arguments

            async def on_start(self):
                ... # My optional setup code in same context as on_receive()

            async def on_stop(self):
                ... # My optional cleanup code in same context as on_receive()

            async def on_failure(self, exception_type, exception_value, traceback):
                ... # My optional cleanup code in same context as on_receive()

            async def on_receive(self, message):
                ... # My optional message handling code for a plain actor

            async def a_method(self, ...):
                ... # My regular method to be used through an ActorProxy

        async def main():
            my_actor_ref = MyActor.start(my_arg=...)
            await my_actor_ref.stop()

        asyncio.run(main())
    """

    @classmethod
    def start(
        cls,
        *args: Any,
        **kwargs: Any,
    ) -> ActorRef[Self]:
        """Start an actor.

        Starting an actor also registers it in the
        :class:`ActorRegistry <async_pykka.ActorRegistry>`.

        Any arguments passed to :meth:`start` will be passed on to the class
        constructor.

        Behind the scenes, the following is happening when you call
        :meth:`start`:

        1. The actor is created:

           1. :attr:`actor_urn` is initialized with the assigned URN.

           2. :attr:`actor_inbox` is initialized with a new actor inbox.

           3. :attr:`actor_ref` is initialized with a :class:`async_pykka.ActorRef`
              object for safely communicating with the actor.

           4. At this point, your :meth:`__init__()` code can run.

        2. The actor is registered in :class:`async_pykka.ActorRegistry`.

        3. The actor receive loop is started as a task on the event loop.


        :returns: a :class:`ActorRef` which can be used to access the actor in
            a safe manner
        """
        # Import here to avoid circular imports
        from async_pykka._registry import ActorRegistry

        obj = cls(*args, **kwargs)
        assert obj.actor_ref is not None, (
            'Actor.__init__() have not been called. Did you forget to call super() in your override?'
        )
        ActorRegistry.register(obj.actor_ref)
        logger.debug(f'Starting {obj}')
        obj._start_actor_loop()
        return obj.actor_ref

    @staticmethod
    @abc.abstractmethod
    def _create_actor_inbox() -> ActorInbox:
        """Create an inbox for the actor.

        Internal method for implementors of new actor types.
        """
        msg = 'Use a subclass of Actor'
        raise NotImplementedError(msg)

    @staticmethod
    @abc.abstractmethod
    def _create_future() -> Future[Any]:
        """Create a future for the actor.

        Internal method for implementors of new actor types.
        """
        msg = 'Use a subclass of Actor'
        raise NotImplementedError(msg)

    @abc.abstractmethod
    def _start_actor_loop(self) -> None:
        """Create and start the actor's event loop.

        Internal method for implementors of new actor types.
        """
        msg = 'Use a subclass of Actor'
        raise NotImplementedError(msg)

    #: The actor URN string is a universally unique identifier for the actor.
    #: It may be used for looking up a specific actor using
    #: :meth:`ActorRegistry.get_by_urn`.
    actor_urn: str

    #: The actor's inbox. Use :meth:`ActorRef.tell`, :meth:`ActorRef.ask`, and
    #: friends to put messages in the inbox.
    actor_inbox: ActorInbox

    #: The event loop this actor is bound to.
    _loop: asyncio.AbstractEventLoop

    #: Flag to ensure on_stop() is only called once.
    _on_stop_called: bool

    _actor_ref: ActorRef[Any]

    @property
    def actor_ref(self) -> ActorRef[Self]:
        """The actor's :class:`ActorRef` instance."""
        # This property only exists to improve the typing of the ActorRef.
        return self._actor_ref

    #: A :class:`AsyncioEvent` representing whether or not the actor should
    #: continue processing messages. Use :meth:`stop` to change it.
    actor_stopped: AsyncioEventType

    def __init__(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        """Create actor.

        Your are free to override :meth:`__init__`, but you must call your
        superclass' :meth:`__init__` to ensure that fields :attr:`actor_urn`,
        :attr:`actor_inbox`, and :attr:`actor_ref` are initialized.

        You can use :func:`super`::

            super().__init__()

        Or call you superclass directly::

            async_pykka.AsyncioActor.__init__(self)

        :meth:`__init__` is called before the actor is started and registered
        in :class:`ActorRegistry <async_pykka.ActorRegistry>`.
        """
        # Import here to avoid circular imports
        from async_pykka._event import AsyncioEvent
        from async_pykka._ref import ActorRef

        # Validate we're in a running event loop
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError as e:
            raise RuntimeError(
                'Actor must be created within a running event loop. '
                'Ensure you call this inside an async context (e.g., async function).'
            ) from e

        self.actor_urn = uuid.uuid4().urn
        self.actor_inbox = self._create_actor_inbox()
        self.actor_stopped = AsyncioEvent()
        self._on_stop_called = False

        self._actor_ref = ActorRef(self)

    def __str__(self) -> str:
        return f'{self.__class__.__name__} ({self.actor_urn})'

    async def stop(self) -> None:
        """Stop the actor.

        It's equivalent to calling :meth:`ActorRef.stop` without blocking.
        """
        self.actor_ref.tell(messages._ActorStop())

    async def _stop(self) -> None:
        """Stop the actor.

        Design points:
        - actor_stopped can be set multiple times (idempotent)
        - on_stop() is guaranteed to be called only once (via _on_stop_called)

        Call order: unregister -> set flag -> on_stop()
        """
        # Import here to avoid circular imports
        from async_pykka._registry import ActorRegistry

        # 1. Unregister from registry (idempotent)
        ActorRegistry.unregister(self.actor_ref)

        # 2. Set stopped flag (idempotent)
        self.actor_stopped.set()
        logger.debug(f'Stopped {self}')

        # 3. Call on_stop() only once
        if not self._on_stop_called:
            self._on_stop_called = True
            try:
                await self.on_stop()
            except Exception:
                await self._handle_failure(*sys.exc_info())

    async def _actor_loop(self) -> None:
        """Run the actor's core loop.

        Uses try/finally to ensure cleanup is always performed.
        """
        # Import here to avoid circular imports
        from async_pykka._registry import ActorRegistry

        fatal_error: BaseException | None = None
        failure_exc_info: tuple[Any, ...] | None = None

        try:
            await self._actor_loop_setup()
            await self._actor_loop_running()
        except asyncio.CancelledError:
            # External cancellation -> graceful stop, don't call on_failure
            logger.debug(f'{self} task cancelled')
        except Exception:
            # Normal exception from setup/running -> record and mark for on_failure
            failure_exc_info = sys.exc_info()
            await self._handle_failure(*failure_exc_info)
        except BaseException as e:
            # Fatal error (KeyboardInterrupt, SystemExit, etc.)
            fatal_error = e
            logger.debug(f'{fatal_error!r} in {self}. Will stop all actors.')
        finally:
            # Always ensure cleanup
            try:
                # If there was an exception, call on_failure first
                if failure_exc_info is not None:
                    try:
                        await self.on_failure(*failure_exc_info)
                    except Exception:
                        await self._handle_failure(*sys.exc_info())

                # Then call _stop() (which calls on_stop internally)
                await self._stop()
                await self._actor_loop_teardown()
            except Exception:
                # Teardown exceptions are only logged, don't trigger stop_all
                await self._handle_failure(*sys.exc_info())

        # Fatal error triggers stop_all (after cleanup is complete)
        if fatal_error is not None:
            await ActorRegistry.stop_all()

    async def _actor_loop_setup(self) -> None:
        """Execute on_start(), exceptions propagate up (not caught here)."""
        await self.on_start()

    async def _actor_loop_running(self) -> None:
        """Message processing loop."""
        while not self.actor_stopped.is_set():
            envelope: Envelope[Any] | None = None
            try:
                envelope = await self.actor_inbox.get()
                response = await self._handle_receive(envelope.message)
                if envelope.reply_to is not None:
                    envelope.reply_to.set(response)

            except asyncio.CancelledError:
                # Propagate up, handled by _actor_loop's finally
                raise

            except Exception:
                exc_info = sys.exc_info()
                if envelope is not None and envelope.reply_to is not None:
                    # Has caller waiting -> pass exception to caller, continue processing
                    logger.info(
                        f'Exception returned from {self} to caller:',
                        exc_info=exc_info,
                    )
                    envelope.reply_to.set_exception()
                else:
                    # No caller -> propagate up, _actor_loop handles on_failure + on_stop
                    raise

    async def _actor_loop_teardown(self) -> None:
        """Clean up unprocessed messages, notify waiters that actor is dead."""
        while True:
            try:
                envelope = self.actor_inbox.get_nowait()
            except asyncio.QueueEmpty:
                break

            if envelope.reply_to is not None:
                if isinstance(envelope.message, messages._ActorStop):
                    envelope.reply_to.set(None)
                else:
                    envelope.reply_to.set_exception(
                        exc_info=(
                            ActorDeadError,
                            ActorDeadError(f'{self.actor_ref} stopped before handling the message'),
                            None,
                        )
                    )

    async def on_start(self) -> None:  # noqa: B027
        """Run code at the beginning of the actor's life.

        Hook for doing any setup that should be done *after* the actor is
        started, but *before* it starts processing messages.

        For :class:`AsyncioActor`, this method is executed in the actor's own
        context, while :meth:`__init__` is executed in the context that created
        the actor.

        If an exception is raised by this method, :meth:`on_failure` will be
        called, then :meth:`on_stop`, and the actor will stop.
        """

    async def on_stop(self) -> None:  # noqa: B027
        """Run code at the end of the actor's life.

        Hook for doing any cleanup that should be done *after* the actor has
        processed the last message, and *before* the actor stops.

        This hook is called in all stop scenarios:
        - Normal stop (_ActorStop message)
        - Cancellation (CancelledError)
        - After on_failure() for exception stops

        For :class:`AsyncioActor` this method is executed in the actor's own
        context, immediately before exit.

        If an exception is raised by this method the stack trace will be
        logged, and the actor will stop.
        """

    async def _handle_failure(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Log error (does not modify state, state is managed by _stop())."""
        logger.error(
            f'Unhandled exception in {self}:',
            exc_info=(exception_type, exception_value, traceback),  # type: ignore[arg-type]
        )

    async def on_failure(  # noqa: B027
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Run code when an unhandled exception is raised.

        Hook for doing any cleanup *after* an unhandled exception is raised,
        and *before* :meth:`on_stop` is called.

        This includes exceptions from:
        - :meth:`on_start`
        - Message handling (when reply_to is None)

        For :class:`AsyncioActor` this method is executed in the actor's own
        context.

        The method's arguments are the relevant information from
        :func:`sys.exc_info`.

        If an exception is raised by this method the stack trace will be
        logged, and the actor will continue to stop (on_stop will be called).
        """

    async def _handle_receive(self, message: Any) -> Any:
        """Handle messages sent to the actor."""
        if isinstance(message, messages._ActorStop):
            return await self._stop()

        if isinstance(message, messages.ProxyCall):
            callee = get_attr_directly(self, message.attr_path)
            result = callee(*message.args, **message.kwargs)
            # Check if result is awaitable (handles coroutines, async generators, etc.)
            if inspect.isawaitable(result):
                return await result
            return result

        if isinstance(message, messages.ProxyGetAttr):
            attr = get_attr_directly(self, message.attr_path)
            return attr

        if isinstance(message, messages.ProxySetAttr):
            parent_attr = get_attr_directly(self, message.attr_path[:-1])
            attr_name = message.attr_path[-1]
            return setattr(parent_attr, attr_name, message.value)

        result = self.on_receive(message)
        if inspect.isawaitable(result):
            return await result
        return result

    async def on_receive(self, message: Any) -> Any:
        """May be implemented for the actor to handle regular non-proxy messages.

        :param message: the message to handle
        :type message: any

        :returns: anything that should be sent as a reply to the sender
        """
        logger.warning(f'Unexpected message received by {self}: {message}')


class AsyncioFuture(Future[T]):
    """Implementation of Future for use with async Python.

    Inherits from Future to provide filter(), join(), map(), reduce() methods.

    The future is implemented using a :class:`asyncio.Future`.

    The future does *not* make a copy of the object which is :meth:`set()`
    on it. It is the setter's responsibility to only pass immutable objects
    or make a copy of the object before setting it on the future.

    Must be created within a running event loop.
    """

    _loop: asyncio.AbstractEventLoop
    _future: asyncio.Future[T]

    def __init__(self) -> None:
        """Initialize the future.

        Raises:
            RuntimeError: If not called within a running event loop
        """
        super().__init__()  # Initialize Future base class (_get_hook, _get_hook_result)

        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError as e:
            raise RuntimeError(
                'AsyncioFuture must be created within a running event loop. '
                'Ensure you call this inside an async context (e.g., async function).'
            ) from e
        self._future = self._loop.create_future()

    def __repr__(self) -> str:
        return '<async_pykka.AsyncioFuture>'

    async def get(
        self,
        *,
        timeout: float | None = None,
    ) -> T:
        """Get the value encapsulated by the future (async method).

        If the encapsulated value is an exception, it is raised instead of
        returned.

        If ``timeout`` is :class:`None`, as default, the method will wait
        until it gets a reply, potentially forever. If ``timeout`` is an
        integer or float, the method will wait for a reply for ``timeout``
        seconds, and then raise :exc:`async_pykka.Timeout`.

        The encapsulated value can be retrieved multiple times.

        :param timeout: seconds to wait before timeout
        :type timeout: float or :class:`None`

        :raise: :exc:`async_pykka.Timeout` if timeout is reached
        :raise: encapsulated value if it is an exception
        :return: encapsulated value if it is not an exception
        """
        # Check for get_hook first (used by filter/map/reduce/join)
        if self._get_hook is not None:
            if self._get_hook_result is None:
                self._get_hook_result = await self._get_hook(timeout)
            return self._get_hook_result

        try:
            return await asyncio.wait_for(asyncio.shield(self._future), timeout)
        except TimeoutError:
            msg = f'{timeout} seconds'
            raise Timeout(msg) from None

    def set(
        self,
        value: T | None = None,
    ) -> None:
        """Set the encapsulated value.

        :param value: the encapsulated value or nothing
        :type value: any object or :class:`None`
        """
        self._future.set_result(value)  # type: ignore[arg-type]

    def set_exception(
        self,
        exc_info: OptExcInfo | None = None,
    ) -> None:
        """Set an exception as the encapsulated value.

        You can pass an ``exc_info`` three-tuple, as returned by
        :func:`sys.exc_info`. If you don't pass ``exc_info``,
        :func:`sys.exc_info` will be called and the value returned by it used.

        :param exc_info: the encapsulated exception
        :type exc_info: three-tuple of (exc_class, exc_instance, traceback)
        """
        assert exc_info is None or len(exc_info) == 3
        if exc_info is None:
            exc_info = sys.exc_info()
        _type, e, _traceback = exc_info
        assert e is not None
        self._future.set_exception(e)


class AsyncioActor(Actor):
    """Implementation of :class:`Actor` using Python asyncio.

    All operations must be performed within the same event loop.
    Cross-thread or cross-loop calls are NOT supported.
    """

    _task: asyncio.Task[None] | None

    @staticmethod
    def _create_actor_inbox() -> ActorInbox:
        """Create an asyncio-based inbox."""
        return AsyncioActorInbox()

    @staticmethod
    def _create_future() -> AsyncioFuture:
        """Create an asyncio-based future."""
        return AsyncioFuture()

    def _start_actor_loop(self) -> None:
        """Start the actor's message processing loop as an asyncio task."""
        self._task = asyncio.create_task(self._actor_loop(), name=self.__class__.__name__)
