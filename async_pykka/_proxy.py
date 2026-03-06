"""ActorProxy - Proxy for accessing actor attributes and methods.

This module provides ActorProxy and CallableProxy for convenient actor interaction.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Generic, Optional, TypeVar

from async_pykka._exceptions import ActorDeadError
from async_pykka._introspection import AttrInfo, introspect_attrs, get_attr_directly
from async_pykka import messages

if TYPE_CHECKING:
    from async_pykka._types import AttrPath
    from async_pykka._actor import Actor
    from async_pykka._ref import ActorRef
    from async_pykka._future import Future

__all__ = ["ActorProxy", "CallableProxy", "traversable"]


logger = logging.getLogger("pykka")


T = TypeVar("T")
A = TypeVar("A", bound="Actor")


class ActorProxy(Generic[A]):
    """An :class:`ActorProxy` wraps an :class:`ActorRef` instance.

    The proxy allows the referenced actor to be used through regular
    method calls and field access.

    You can create an :class:`ActorProxy` from any :class:`ActorRef`::

        actor_ref = MyActor.start()
        actor_proxy = ActorProxy(actor_ref=actor_ref)

    You can also get an :class:`ActorProxy` by using :meth:`proxy()`::

        actor_proxy = MyActor.start().proxy()

    **Attributes and method calls**

    When reading an attribute or getting a return value from a method,
    you get a :class:`Future` object back. To get the enclosed value
    from the future, you must await the returned future::

        print(await actor_proxy.string_attribute)
        print(await actor_proxy.count())

    If you call a method just for its side effects and do not care
    about the return value, you can fire-and-forget::

        actor_proxy.method_with_side_effect()

    To block until the method completes::

        await actor_proxy.method_with_side_effect()

    **Setting attributes**

    To set an attribute on the actor, use the :meth:`set` method::

        await proxy.set('counter', 10)

    Direct attribute assignment (proxy.counter = 10) is NOT supported
    and will raise AttributeError.

    **Proxy to itself**

    An actor can use a proxy to itself to schedule work for itself::

        def __init__(self):
            self._in_future = self.actor_ref.proxy()

        def do_work(self):
            self._in_future.do_more_work()

    To avoid infinite loops during proxy introspection, proxies to self
    should be kept as private instance attributes (prefixed with ``_``).

    :param actor_ref: reference to the actor to proxy
    :type actor_ref: :class:`async_pykka.ActorRef`

    :raise: :exc:`async_pykka.ActorDeadError` if actor is not available
    """

    # Internal attributes that should be set directly on the proxy
    _INTERNAL_ATTRS = frozenset({
        "actor_ref", "_actor", "_attr_path",
        "_known_attrs", "_actor_proxies", "_callable_proxies"
    })

    #: The actor's :class:`async_pykka.ActorRef` instance.
    actor_ref: ActorRef[A]

    _actor: A
    _attr_path: AttrPath
    _known_attrs: dict[AttrPath, AttrInfo]
    _actor_proxies: dict[AttrPath, ActorProxy[A]]
    _callable_proxies: dict[AttrPath, CallableProxy[A]]

    def __init__(
        self,
        *,
        actor_ref: ActorRef[A],
        attr_path: Optional[AttrPath] = None,
    ) -> None:
        if not actor_ref.is_alive():
            msg = f"{actor_ref} not found"
            raise ActorDeadError(msg)

        # Use object.__setattr__ to bypass our __setattr__ override
        object.__setattr__(self, "actor_ref", actor_ref)
        object.__setattr__(self, "_actor", actor_ref._actor)  # noqa: SLF001
        object.__setattr__(self, "_attr_path", attr_path or ())
        object.__setattr__(
            self, "_known_attrs",
            introspect_attrs(root=actor_ref._actor, proxy=self)  # noqa: SLF001
        )
        object.__setattr__(self, "_actor_proxies", {})
        object.__setattr__(self, "_callable_proxies", {})

    def __setattr__(self, name: str, value: Any) -> None:
        """Intercept attribute assignment and raise an error.

        Direct attribute assignment on ActorProxy is not supported.
        Use the set() method instead.

        Raises:
            AttributeError: Always, with instructions to use set()
        """
        if name in self._INTERNAL_ATTRS:
            return object.__setattr__(self, name, value)

        raise AttributeError(
            f"Cannot set attribute {name!r} directly on ActorProxy. "
            f"Use 'await proxy.set({name!r}, value)' to modify the actor's attribute."
        )

    def __eq__(
        self,
        other: object,
    ) -> bool:
        if not isinstance(other, ActorProxy):
            return False
        if self._actor != other._actor:  # pyright: ignore[reportUnknownMemberType]
            return False
        return self._attr_path == other._attr_path

    def __hash__(self) -> int:
        return hash((self._actor, self._attr_path))

    def __repr__(self) -> str:
        return f"<ActorProxy for {self.actor_ref}, attr_path={self._attr_path!r}>"

    def __dir__(self) -> list[str]:
        result = ["__class__"]
        result += list(self.__class__.__dict__.keys())
        result += list(self.__dict__.keys())
        result += [attr_path[0] for attr_path in list(self._known_attrs.keys())]
        return sorted(result)

    def __getattr__(self, name: str) -> Any:
        """Get a field or callable from the actor."""
        attr_path: AttrPath = (*self._attr_path, name)

        if attr_path not in self._known_attrs:
            self._known_attrs = introspect_attrs(root=self._actor, proxy=self)

        attr_info = self._known_attrs.get(attr_path)
        if attr_info is None:
            msg = f"{self} has no attribute {name!r}"
            raise AttributeError(msg)

        if attr_info.callable:
            if attr_path not in self._callable_proxies:
                self._callable_proxies[attr_path] = CallableProxy(
                    actor_ref=self.actor_ref,
                    attr_path=attr_path,
                )
            return self._callable_proxies[attr_path]

        if attr_info.traversable:
            if attr_path not in self._actor_proxies:
                self._actor_proxies[attr_path] = ActorProxy(
                    actor_ref=self.actor_ref,
                    attr_path=attr_path,
                )
            return self._actor_proxies[attr_path]

        message = messages.ProxyGetAttr(attr_path=attr_path)
        return self.actor_ref.ask(message)

    def set(self, name: str, value: Any) -> Future[None]:
        """Set a field on the actor.

        Returns a future that resolves when the field is set.

        Usage::

            await proxy.set('counter', 10)

        :param name: the attribute name to set
        :param value: the value to set
        :return: Future that resolves to None when complete
        """
        attr_path = (*self._attr_path, name)
        message = messages.ProxySetAttr(attr_path=attr_path, value=value)
        return self.actor_ref.ask(message)


class CallableProxy(Generic[A]):
    """Proxy to a single method.

    :class:`CallableProxy` instances are returned when accessing methods on a
    :class:`ActorProxy` without calling them.

    Example::

        proxy = AnActor.start().proxy()

        # Ask semantics returns a future. See `__call__()` docs.
        future = proxy.do_work()

        # Tell semantics are fire and forget. See `defer()` docs.
        proxy.do_work.defer()
    """

    actor_ref: ActorRef[A]
    _attr_path: AttrPath

    def __init__(
        self,
        *,
        actor_ref: ActorRef[A],
        attr_path: AttrPath,
    ) -> None:
        self.actor_ref = actor_ref
        self._attr_path = attr_path

    def __call__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Future[Any]:
        """Call with ask semantics.

        Returns a future which will yield the called method's return value.

        If the call raises an exception, it is set on the future and will be
        reraised by :meth:`Future.get`. If the future is left unused,
        the exception will not be reraised. Either way, the exception will
        also be logged.

        Usage::

            result = await proxy.method(arg1, arg2)
        """
        message = messages.ProxyCall(
            attr_path=self._attr_path, args=args, kwargs=kwargs
        )
        return self.actor_ref.ask(message)

    def defer(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Call with tell semantics (fire-and-forget).

        Does not create or return a future.

        If the call raises an exception, there is no future to set the
        exception on. Thus, the actor's :meth:`on_failure` hook
        is called instead.
        """
        message = messages.ProxyCall(
            attr_path=self._attr_path, args=args, kwargs=kwargs
        )
        self.actor_ref.tell(message)


def traversable(obj: T) -> T:
    """Mark an actor attribute as traversable.

    The traversable marker makes the actor attribute's own methods and
    attributes available to users of the actor through an
    :class:`ActorProxy`.

    Used as a function to mark a single attribute::

        class AnActor(async_pykka.AsyncioActor):
            playback = async_pykka.traversable(Playback())

        class Playback:
            def play(self):
                return True

    This function can also be used as a class decorator::

        class AnActor(async_pykka.AsyncioActor):
            playback = Playback()

        @async_pykka.traversable
        class Playback:
            def play(self):
                return True

    The third alternative is to manually mark a class as traversable::

        class AnActor(async_pykka.AsyncioActor):
            playback = Playback()

        class Playback:
            pykka_traversable = True

            def play(self):
                return True

    When the attribute is marked as traversable, its methods can be executed
    in the context of the actor through an actor proxy::

        proxy = AnActor.start().proxy()
        assert await proxy.playback.play() is True
    """
    if hasattr(obj, "__slots__"):
        msg = (
            "async_pykka.traversable() cannot be used to mark "
            "an object using slots as traversable."
        )
        raise ValueError(msg)
    obj._pykka_traversable = True  # type: ignore[attr-defined]  # noqa: SLF001
    return obj
