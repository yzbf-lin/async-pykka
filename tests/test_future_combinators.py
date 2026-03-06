from __future__ import annotations

import async_pykka


async def test_get_all_collects_results_in_order() -> None:
    a = async_pykka.AsyncioFuture[int]()
    b = async_pykka.AsyncioFuture[int]()
    c = async_pykka.AsyncioFuture[int]()

    a.set(1)
    b.set(2)
    c.set(3)

    assert await async_pykka.get_all([a, b, c]) == [1, 2, 3]


async def test_future_join_map_filter_reduce_and_await() -> None:
    values = async_pykka.AsyncioFuture[list[int]]()
    others = async_pykka.AsyncioFuture[list[int]]()

    mapped = values.map(lambda xs: [x * 2 for x in xs])
    filtered = values.filter(lambda x: x % 2 == 1)
    reduced = values.reduce(lambda x, y: x + y, 0)
    joined = values.join(others)

    values.set([1, 2, 3])
    others.set([4, 5])

    assert await mapped == [2, 4, 6]
    assert list(await filtered) == [1, 3]
    assert await reduced == 6
    assert await joined == [[1, 2, 3], [4, 5]]
