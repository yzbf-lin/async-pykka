"""async_pykka - Pure async actor framework for Python.

This library requires all operations to be performed within the same
event loop. Cross-thread or cross-loop calls are NOT supported.

Usage:
    import asyncio
    import async_pykka

    class MyActor(async_pykka.AsyncioActor):
        def __init__(self, name):
            super().__init__()
            self.name = name

        async def greet(self):
            return f"Hello from {self.name}"

    async def main():
        ref = MyActor.start("World")
        proxy = ref.proxy()

        result = await proxy.greet()
        print(result)  # "Hello from World"

        await ref.stop()

    asyncio.run(main())
"""

import importlib.metadata as _importlib_metadata
import logging as _logging

from async_pykka._exceptions import ActorDeadError, Timeout
from async_pykka._future import Future, get_all
from async_pykka._proxy import ActorProxy, CallableProxy, traversable
from async_pykka._ref import ActorRef
from async_pykka._registry import ActorRegistry
from async_pykka._event import AsyncioEvent
from async_pykka._inbox import ActorInbox, AsyncioActorInbox
from async_pykka._actor import Actor, AsyncioActor, AsyncioFuture

__all__ = [
    "Actor",
    "ActorDeadError",
    "ActorInbox",
    "ActorProxy",
    "ActorRef",
    "ActorRegistry",
    "AsyncioActor",
    "AsyncioActorInbox",
    "AsyncioEvent",
    "AsyncioFuture",
    "CallableProxy",
    "Future",
    "Timeout",
    "get_all",
    "traversable",
]


#: async_pykka's :pep:`396` and :pep:`440` compatible version number
__version__: str
try:
    __version__ = _importlib_metadata.version(__name__)
except _importlib_metadata.PackageNotFoundError:
    __version__ = "unknown"


_logging.getLogger(__name__).addHandler(_logging.NullHandler())
