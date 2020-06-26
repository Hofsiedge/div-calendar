import requests, locale, aiohttp, asyncio
from typing import List, Any


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


async def async_map(tickers, coroutine, *args, **kwargs):
    if tickers is None or len(tickers) == 0:
        return []
    conn = aiohttp.TCPConnector(limit=20)
    timeout = aiohttp.ClientTimeout(total=7)
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        futures = [coroutine(session, ticker, *args, **kwargs) for ticker in tickers]
        return await asyncio.gather(*futures)


# TODO: generic typing with typevar
def fetch_async(data, coroutine, *args, **kwargs) -> List[Any]:
    loop    = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result  = loop.run_until_complete(
        async_map(data, coroutine, *args, **kwargs)
    )
    loop.run_until_complete(asyncio.sleep(0))
    loop.close()
    return result


