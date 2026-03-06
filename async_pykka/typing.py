"""Type hint helpers."""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Concatenate,
    ParamSpec,
    Protocol,
    TypeVar,
)

from async_pykka._actor import Actor

if TYPE_CHECKING:
    from collections.abc import Callable

    from async_pykka._future import Future


__all__ = [
    'ActorMemberMixin',
    'proxy_field',
    'proxy_method',
]


T = TypeVar('T')
P = ParamSpec('P')
R_co = TypeVar('R_co', covariant=True)


class Method[**P, R_co](Protocol):
    def __get__(self, instance: Any, owner: type | None = None) -> Callable[P, R_co]: ...

    def __call__(self, obj: Any, *args: P.args, **kwargs: P.kwargs) -> R_co: ...


def proxy_field[T](field: T) -> Future[T]:
    """Type a field on an actor proxy.

    /// note | Version added: Pykka 4.0
    ///
    """
    return field  # type: ignore[return-value]


def proxy_method[**P, T](
    field: Callable[Concatenate[Any, P], T],
) -> Method[P, Future[T]]:
    """Type a method on an actor proxy.

    /// note | Version added: Pykka 4.0
    ///
    """
    return field  # type: ignore[return-value]


class ActorMemberMixin:
    """Mixin class for typing Actor methods which are accessible via proxy instances.

    /// note | Version added: Pykka 4.0
    ///
    """

    stop = proxy_method(Actor.stop)
    on_start = proxy_method(Actor.on_start)
    on_stop = proxy_method(Actor.on_stop)
    on_failure = proxy_method(Actor.on_failure)
    on_receive = proxy_method(Actor.on_receive)
