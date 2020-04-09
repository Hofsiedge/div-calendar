import requests, aiohttp, asyncio
import pandas as pd
from security.models import Security
from bs4 import BeautifulSoup


async def fetch_yield_rs(session: aiohttp.ClientSession, ticker: str):
    async with session.get(f'https://www.dohod.ru/ik/analytics/dividend/{ticker.lower()}') as r:
        if r.status != 200:
            return 0
        text = await r.text()
        soup = BeautifulSoup(text, 'html.parser')
        try:
            return float(soup.find('tr', {'class': 'frow'}).find('td').text[:-1])
        except Exception as e:
            print(e)
            return 0


async def fetch_yield_fs(session: aiohttp.ClientSession, ticker: str):
    async with session.get(f'https://ycharts.com/companies/{ticker.upper()}/dividend_yield') as r:
        if r.status != 200:
            return 0
        text = await r.text()
        soup = BeautifulSoup(text, 'html.parser')
        try:
            return float(soup.find('span', {'id': 'pgNameVal'}).text.split()[0][:-1])
        except Exception as e:
            print(e)
            return 0


async def tickers_map(tickers, coroutine):
    conn = aiohttp.TCPConnector(limit=20)
    timeout = aiohttp.ClientTimeout(total=7)
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        futures = [coroutine(session, ticker) for ticker in tickers]
        return await asyncio.gather(*futures)


def search_tinkoff(query: str, type: str, offset: int = None, limit: int = None,
                   market: str = None, currency: str = None) -> pd.DataFrame:
    url = f'https://api.tinkoff.ru/trading/{"stocks" if type == "stock" else "bonds"}/list'
    if currency == 'RUB':
        market = 'Russian'
    if market is None:
        market = 'All'
    r = requests.post(
        url, json = {
            'filter': query,
            'country': market.capitalize(),
            'sortType': 'ByName',
            'orderType': 'Asc',
            'start': offset or 0,
            'end': (offset or 0) + (limit or 100),
        }
    )

    if r.status_code != 200:
        return None
    data = r.json()['payload']['values']
    df = pd.DataFrame(columns=['ticker', 'name', 'type', 'logo', 'price',
                               'currency', 'exchange', 'yield'])
    tickers, names, types, logos, prices = [], [], [], [], []
    currencies, exchanges, yields = [], [], []
    for i in data:
        symbol = i['symbol']
        tickers.append(symbol['ticker'])
        names.append(symbol['showName'])
        types.append('stock' if symbol['symbolType'] == 'stock' else 'bond')
        currencies.append(symbol['currency'])
        exchanges.append(symbol['exchange'])
        logos.append(f'https://static.tinkoff.ru/brands/traiding/{symbol["logoName"].split(".")[0]}x160.png')
        prices.append(i['price']['value'])
        yields.append(i.get('totalYield', 0))


    df.ticker   = tickers
    df.name     = names
    df.type     = types
    df.logo     = logos
    df.price    = prices
    df.currency = currencies
    df.exchange = exchanges
    df['yield'] = yields
    if currency:
        df = df[df.currency == currency]

    return df


def search_securities(query: str, type: str, offset: int = None, limit: int = None,
                      market: str = None, currency: str = None):
    # TODO: if len(query) == 1: fetch from DB (tinkoff won't search)
    res = search_tinkoff(query, type, offset, limit, market, currency)
    if res is None:
        return None

    if type == 'stock':
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        coroutine = fetch_yield_fs if market.lower() == 'foreign' else fetch_yield_rs
        yields = loop.run_until_complete(tickers_map(res.ticker, coroutine))
        loop.run_until_complete(asyncio.sleep(0))
        loop.close()
        res['yield'] = yields

    return res.to_dict(orient='records')
