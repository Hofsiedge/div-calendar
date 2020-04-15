import requests, aiohttp, asyncio, datetime
import pandas as pd
from bs4 import BeautifulSoup
from django.core.cache import cache
from security.models import Security


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


async def async_map(tickers, coroutine):
    if tickers is None or type(tickers) != len(tickers) == 0:
        return []
    conn = aiohttp.TCPConnector(limit=20)
    timeout = aiohttp.ClientTimeout(total=7)
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        futures = [coroutine(session, ticker) for ticker in tickers]
        return await asyncio.gather(*futures)

def fetch_async(data, coroutine) -> list:
    loop    = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result  = loop.run_until_complete(
        async_map(data, coroutine)
    )
    loop.run_until_complete(asyncio.sleep(0))
    loop.close()
    return result


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
        types.append(type)
        currencies.append(symbol['currency'])
        exchanges.append(symbol['exchange'])
        logo_name = 'x160.'.join(symbol['logoName'].split('.'))
        logos.append(f'https://static.tinkoff.ru/brands/traiding/{logo_name}')
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
    if not query:
        return []

    indices = cache.get(query)

    if indices is not None:
        securities = Security.objects.filter(id__in=indices)

    else:
        if len(query) == 1:
            # update if contains outdated
            return Securities.objects.filter(Q(ticker__icontains=query)
                                           | Q(name__icontains=query))

        df      = search_tinkoff(query, type, offset, limit, market, currency)
        # TODO: profile to check that set improves performance
        present = Security.objects.filter(ticker__in=set(df.ticker))

        present_tickers = {s.ticker for s in present.only('ticker')}
        missing = [
            Security(
                ticker   = s.ticker,
                name     = s.name,
                logo     = s.logo,
                currency = s.currency,
                exchange = s.exchange,
                stock    = s.type == 'stock',
                price    = s.price,
                _yield   = s['yield'],
                foreign  = market == 'foreign',
            ) for _, s in df[~df.ticker.isin(present_tickers)].iterrows()]

        yesterday   = datetime.datetime.now() - datetime.timedelta(1)
        outdated    = present.filter(last_update__lt=yesterday)

        for security in outdated:
            source          = df[df.ticker == security.ticker]
            security.price  = source['price']
            security._yield = source['yield']

        if type == 'stock' and (len(missing) > 0 or outdated.exists()):
            source  = missing + list(outdated)
            yields  = iter(fetch_async(
                [s.ticker for s in source],
                fetch_yield_fs if market.lower() == 'foreign' else fetch_yield_rs
            ))
            for s in source:
                s._yield = yields.__next__()
                s.save()

        securities = missing + list(present)

    # TODO: limits
    cache.set(query, tuple([s.id for s in securities]) if securities else tuple())

    return securities
