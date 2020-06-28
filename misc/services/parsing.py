import requests, locale, aiohttp, asyncio
from typing import Any, Awaitable, Callable, Dict, Generic, Iterable, List, TypeVar
from typing_extensions import Protocol


def get_rate():
    # TODO: replace placeholder with caching
    placeholder = {'rubToUsd': 74, 'usdToRub': 0.013}
    r = requests.get('https://tinkoff.ru/api/v1/currency_rates/')
    if r.status_code != 200 or r.json()['resultCode'] != 'OK':
        return placeholder
    data = r.json()['payload']['rates'][6]
    try:
        ru, ur = data['buy'], 1 / data['sell']
        if type(ru) != float or type(ur) != float:
            raise TypeError(f'Tinkoff API failed. {ru}, {ur}')
    except Exception as e:
        # TODO: logging
        print(e)
        return placeholder
    return {'rubToUsd': ru, 'usdToRub': ur}


# TODO: check if T & V are required
T       = TypeVar('T')
V       = TypeVar('V')
InT     = TypeVar('InT',    contravariant=True)
OutT    = TypeVar('OutT',   covariant=True)


class CoroutineFunction(Protocol[InT, OutT]):
    def __call__(self, session: aiohttp.ClientSession, item: InT, *args: Any, **kwargs: Any) -> OutT: ...


async def async_map(items, coroutine: CoroutineFunction[T, Awaitable[V]], *args, **kwargs) -> List[V]:
    if items is None or len(items) == 0:
        return []
    conn = aiohttp.TCPConnector(limit=20)
    timeout = aiohttp.ClientTimeout(total=7)
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        futures: List[Awaitable[V]] = [coroutine(session, item, *args, **kwargs) for item in items]
        return await asyncio.gather(*futures)


def fetch_async(data: Iterable[T], coroutine: CoroutineFunction[T, Awaitable[V]], *args, **kwargs) -> List[V]:
    loop    = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result: List[V]  = loop.run_until_complete(
        async_map(data, coroutine, *args, **kwargs)
    )
    loop.run_until_complete(asyncio.sleep(0))
    loop.close()
    return result


