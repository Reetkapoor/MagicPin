import asyncio

from app.store import StateStore


def test_suppression_reservation_is_atomic():
    store = StateStore()
    results = []

    async def reserve():
        results.append(store.reserve_suppression("k"))

    async def run():
        await asyncio.gather(*(reserve() for _ in range(20)))

    asyncio.run(run())
    assert sum(results) == 1
