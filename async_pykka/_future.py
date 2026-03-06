"""Future base class and get_all utility.

This module provides the base Future class for async result handling.
The concrete AsyncioFuture implementation is in _actor.py.
"""

from __future__ import annotations

import functools
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Generator,
    Generic,
    Iterable,
    Optional,
    TypeVar,
    cast,
)

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

    from async_pykka._types import OptExcInfo

__all__ = ["Future", "get_all"]


T = TypeVar("T")
J = TypeVar("J")  # For when T is Iterable[J]
M = TypeVar("M")  # Result of Future.map()
R = TypeVar("R")  # Result of Future.reduce()

GetHookFunc: TypeAlias = Callable[[Optional[float]], Awaitable[T]]


class Future(Generic[T]):
    """A handle to a value which is available now or in the future.

    Typically returned by calls to actor methods or accesses to actor fields.

    To get hold of the encapsulated value, call :meth:`Future.get` (async method)
    or ``await`` the future directly.

    This is the base class. Use :class:`AsyncioFuture` for the concrete
    asyncio-based implementation.
    """

    _get_hook: Optional[GetHookFunc[T]]
    _get_hook_result: Optional[T]

    def __init__(self) -> None:
        super().__init__()
        self._get_hook = None
        self._get_hook_result = None

    def __repr__(self) -> str:
        return "<async_pykka.Future>"

    async def get(
        self,
        *,
        timeout: Optional[float] = None,
    ) -> T:
        """Get the value encapsulated by the future (async method).

        If the encapsulated value is an exception, it is raised instead of
        returned.

        If ``timeout`` is :class:`None`, as default, the method will wait
        until it gets a reply, potentially forever. If ``timeout`` is an
        integer or float, the method will wait for a reply for ``timeout``
        seconds, and then raise :exc:`async_pykka.Timeout`.

        The encapsulated value can be retrieved multiple times. The future will
        only block the first time the value is accessed.

        :param timeout: seconds to wait before timeout
        :type timeout: float or :class:`None`

        :raise: :exc:`async_pykka.Timeout` if timeout is reached
        :raise: encapsulated value if it is an exception
        :return: encapsulated value if it is not an exception
        """
        if self._get_hook is not None:
            if self._get_hook_result is None:
                self._get_hook_result = await self._get_hook(timeout)
            return self._get_hook_result
        raise NotImplementedError

    def set(
        self,
        value: Optional[T] = None,
    ) -> None:
        """Set the encapsulated value.

        :param value: the encapsulated value or nothing
        :type value: any object or :class:`None`
        :raise: an exception if set is called multiple times
        """
        raise NotImplementedError

    def set_exception(
        self,
        exc_info: Optional[OptExcInfo] = None,
    ) -> None:
        """Set an exception as the encapsulated value.

        You can pass an ``exc_info`` three-tuple, as returned by
        :func:`sys.exc_info`. If you don't pass ``exc_info``,
        :func:`sys.exc_info` will be called and the value returned by it used.

        In other words, if you're calling :meth:`set_exception`, without any
        arguments, from an except block, the exception you're currently
        handling will automatically be set on the future.

        :param exc_info: the encapsulated exception
        :type exc_info: three-tuple of (exc_class, exc_instance, traceback)
        """
        raise NotImplementedError

    def set_get_hook(
        self,
        func: GetHookFunc[T],
    ) -> None:
        """Set a function to be executed when :meth:`get` is called.

        The function will be called when :meth:`get` is called, with the
        ``timeout`` value as the only argument. The function's return value
        will be returned from :meth:`get`.

        :param func: async function called to produce return value of :meth:`get`
        :type func: async function accepting a timeout value
        """
        self._get_hook = func

    def filter(
        self: Future[Iterable[J]],
        func: Callable[[J], bool],
    ) -> Future[Iterable[J]]:
        """Return a new future with only the items passing the predicate function.

        If the future's value is an iterable, :meth:`filter` will return a new
        future whose value is another iterable with only the items from the
        first iterable for which ``func(item)`` is true. If the future's value
        isn't an iterable, a :exc:`TypeError` will be raised when :meth:`get`
        is called.

        Example::

            >>> import async_pykka
            >>> f = async_pykka.AsyncioFuture()
            >>> g = f.filter(lambda x: x > 10)
            >>> g
            <async_pykka.AsyncioFuture at ...>
            >>> f.set(range(5, 15))
            >>> await f.get()
            [5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
            >>> await g.get()
            [11, 12, 13, 14]
        """

        async def _filter(timeout: Optional[float]) -> list[J]:
            return list(filter(func, await self.get(timeout=timeout)))

        future = self.__class__()
        future.set_get_hook(_filter)
        return future

    def join(
        self: Future[Any],
        *futures: Future[Any],
    ) -> Future[Iterable[Any]]:
        """Return a new future with a list of the result of multiple futures.

        One or more futures can be passed as arguments to :meth:`join`. The new
        future returns a list with the results from all the joined futures.

        Example::

            >>> import async_pykka
            >>> a = async_pykka.AsyncioFuture()
            >>> b = async_pykka.AsyncioFuture()
            >>> c = async_pykka.AsyncioFuture()
            >>> f = a.join(b, c)
            >>> a.set('def')
            >>> b.set(123)
            >>> c.set(False)
            >>> await f.get()
            ['def', 123, False]
        """

        async def _join(timeout: Optional[float]) -> list[Any]:
            return [await f.get(timeout=timeout) for f in [self, *futures]]

        future = cast(Future[Iterable[Any]], self.__class__())
        future.set_get_hook(_join)
        return future

    def map(
        self,
        func: Callable[[T], M],
    ) -> Future[M]:
        """Pass the result of the future through a function.

        Example::

            >>> import async_pykka
            >>> f = async_pykka.AsyncioFuture()
            >>> g = f.map(lambda x: x + 10)
            >>> f.set(30)
            >>> await g.get()
            40

            >>> f = async_pykka.AsyncioFuture()
            >>> g = f.map(lambda x: x['foo'])
            >>> f.set({'foo': 'bar'})
            >>> await g.get()
            'bar'
        """

        async def _map(timeout: Optional[float]) -> M:
            return func(await self.get(timeout=timeout))

        future = cast(Future[M], self.__class__())
        future.set_get_hook(_map)
        return future

    def reduce(
        self: Future[Iterable[J]],
        func: Callable[[R, J], R],
        *args: R,
    ) -> Future[R]:
        """Reduce a future's iterable result to a single value.

        The function of two arguments is applied cumulatively to the items of
        the iterable, from left to right. The result of the first function call
        is used as the first argument to the second function call, and so on,
        until the end of the iterable. If the future's value isn't an iterable,
        a :exc:`TypeError` is raised.

        :meth:`reduce` accepts an optional second argument, which will be used
        as an initial value in the first function call. If the iterable is
        empty, the initial value is returned.

        Example::

            >>> import async_pykka
            >>> f = async_pykka.AsyncioFuture()
            >>> g = f.reduce(lambda x, y: x + y)
            >>> f.set(['a', 'b', 'c'])
            >>> await g.get()
            'abc'

            >>> f = async_pykka.AsyncioFuture()
            >>> g = f.reduce(lambda x, y: x + y)
            >>> f.set([1, 2, 3])
            >>> (1 + 2) + 3
            6
            >>> await g.get()
            6

            >>> f = async_pykka.AsyncioFuture()
            >>> g = f.reduce(lambda x, y: x + y, 5)
            >>> f.set([1, 2, 3])
            >>> ((5 + 1) + 2) + 3
            11
            >>> await g.get()
            11

            >>> f = async_pykka.AsyncioFuture()
            >>> g = f.reduce(lambda x, y: x + y, 5)
            >>> f.set([])
            >>> await g.get()
            5
        """

        async def _reduce(timeout: Optional[float]) -> R:
            return functools.reduce(func, await self.get(timeout=timeout), *args)

        future = cast(Future[R], self.__class__())
        future.set_get_hook(_reduce)
        return future

    def __await__(self) -> Generator[None, None, T]:
        """Support direct await on the future."""
        return self.get().__await__()

    __iter__ = __await__


async def get_all(
    futures: Iterable[Future[T]],
    *,
    timeout: Optional[float] = None,
) -> list[T]:
    """Collect all values encapsulated in the list of futures (sequential).

    Processes futures sequentially. If a future raises an exception, it is
    propagated immediately; remaining futures continue running in the background
    (they are not cancelled).

    If ``timeout`` is not :class:`None`, it applies to each individual future's
    get() call, not the total operation time.

    Args:
        futures: futures for the results to collect
        timeout: seconds to wait for each future before timeout

    Returns:
        List of results in the same order as input futures

    Raises:
        async_pykka.Timeout: if any future times out
        Exception: if any future's result is an exception
    """
    return [await future.get(timeout=timeout) for future in futures]
