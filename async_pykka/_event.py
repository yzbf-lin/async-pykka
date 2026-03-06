"""AsyncioEvent - Enhanced asyncio.Event with timeout support.

This module provides an enhanced Event class that supports timeouts.
"""

from __future__ import annotations

import asyncio
from typing import Literal, Optional, overload

__all__ = ["AsyncioEvent"]


class AsyncioEvent(asyncio.Event):
    """Same as asyncio.Event but adds a `wait` with timeout.

    Usage::

        event = AsyncioEvent()

        # Wait indefinitely
        await event.wait()

        # Wait with timeout
        success = await event.wait(timeout=5.0)
        if not success:
            print("Timed out!")
    """

    @overload
    async def wait(self) -> Literal[True]: ...

    @overload
    async def wait(self, timeout: Optional[float]) -> bool: ...

    async def wait(self, timeout: Optional[float] = None) -> bool:
        """Wait for the event to be set.

        If timeout is None, wait indefinitely (always returns True).
        If timeout is specified, return True if the event was set,
        or False if the timeout elapsed.

        :param timeout: seconds to wait before timeout
        :type timeout: float or :class:`None`

        :return: True if event was set, False if timeout elapsed
        """
        try:
            await asyncio.wait_for(super().wait(), timeout=timeout)
        except asyncio.TimeoutError:
            return False
        else:
            return True
