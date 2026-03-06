"""Debug helpers for async_pykka.

Provides utilities for debugging asyncio-based actors.
"""

import asyncio
import logging
import sys
import traceback
from typing import Any, Optional

__all__ = ["log_task_tracebacks", "log_actor_states"]


logger = logging.getLogger("pykka")


def log_task_tracebacks(*_args: Any, **_kwargs: Any) -> None:
    """Log a traceback for each running asyncio task at :attr:`logging.CRITICAL` level.

    This can be a convenient tool for debugging hangs or deadlocks in async code.

    The function accepts any arguments so that it can easily be used as e.g. a
    signal handler, but it does not use the arguments for anything.

    To use this function as a signal handler, setup logging with a
    :attr:`logging.CRITICAL` threshold or lower and make your main thread
    register this with the :mod:`signal` module::

        import logging
        import signal

        import async_pykka.debug

        logging.basicConfig(level=logging.DEBUG)
        signal.signal(signal.SIGUSR1, async_pykka.debug.log_task_tracebacks)

    If your application hangs, send the `SIGUSR1` signal to the process::

        kill -SIGUSR1 <pid of your process>

    Note: This function can be called from any context (sync or async).
    It will attempt to get all tasks from the running event loop.
    """
    try:
        loop = asyncio.get_running_loop()
        tasks = asyncio.all_tasks(loop)
    except RuntimeError:
        # No running event loop - try to get from default loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                tasks = asyncio.all_tasks(loop)
            else:
                logger.critical("No running event loop found")
                return
        except RuntimeError:
            logger.critical("No event loop available")
            return

    logger.critical(f"Found {len(tasks)} asyncio tasks:")

    for task in tasks:
        name = task.get_name()
        state = "running" if not task.done() else "done"
        coro = task.get_coro()

        # Get the current stack for running tasks
        frames = task.get_stack()
        if frames:
            stack = "".join(traceback.format_list(
                traceback.extract_stack(frames[-1])
            ))
        else:
            stack = "  <no stack available>"

        logger.critical(
            f"\nTask: {name} (state: {state})\n"
            f"  Coroutine: {coro}\n"
            f"  Stack:\n{stack}"
        )


async def log_actor_states() -> None:
    """Log the state of all registered actors at :attr:`logging.CRITICAL` level.

    This provides a snapshot of all actors in the registry, including:
    - Actor URN
    - Actor class name
    - Whether the actor is stopped
    - Inbox size (if available)

    Must be called from within a running event loop.

    Example::

        import async_pykka
        import async_pykka.debug

        async def debug_actors():
            await async_pykka.debug.log_actor_states()
    """
    from async_pykka._registry import ActorRegistry

    refs = ActorRegistry.get_all()
    logger.critical(f"Found {len(refs)} registered actors:")

    for ref in refs:
        is_stopped = ref.actor_stopped.is_set()
        inbox_empty = ref.actor_inbox.empty()

        logger.critical(
            f"\nActor: {ref.actor_class.__name__}\n"
            f"  URN: {ref.actor_urn}\n"
            f"  Stopped: {is_stopped}\n"
            f"  Inbox empty: {inbox_empty}"
        )


def get_actor_info() -> list[dict[str, Any]]:
    """Get information about all registered actors.

    Returns a list of dictionaries containing actor information.
    This can be useful for programmatic inspection of actor states.

    Returns:
        List of dicts with keys: 'urn', 'class_name', 'is_stopped', 'inbox_empty'
    """
    from async_pykka._registry import ActorRegistry

    refs = ActorRegistry.get_all()
    result = []

    for ref in refs:
        result.append({
            'urn': ref.actor_urn,
            'class_name': ref.actor_class.__name__,
            'is_stopped': ref.actor_stopped.is_set(),
            'inbox_empty': ref.actor_inbox.empty(),
        })

    return result
