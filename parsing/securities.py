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


async def tickers_map(tickers, coroutine):
    if tickers is None or len(tickers) == 0:
        return []
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
    indices = cache.get(query)

    if indices is not None:
        securities = Security.objects.filter(id__in=indices)

    else:
        if len(query) == 1:
            return Securities.objects.filter(Q(ticker__icontains=query)
                                           | Q(name__icontains=query))

        yesterday   = datetime.datetime.now() - datetime.timedelta(1)
        df          = search_tinkoff(query, type, offset, limit, market, currency)
        tickers     = df.ticker
        securities  = []
        present     = Security.objects.filter(ticker__in=tickers)
        # assert present is not evaluated yet
        outdated    = present.filter(last_update__lt=yesterday)

        # TODO: check if present gets updated too
        for security in outdated:
            source = df[df.ticker == security.ticker]
            security.price = source['price']
            security._yield = source['yield']
            security.save()
        # assert present is updated
        securities.extend(list(present))

        present_tickers = {s.ticker for s in securities}
        outdated_tickers = {s.ticker for s in outdated}
        actual_tickers = present_tickers - outdated_tickers

        redundant_indices = df.ticker.isin(actual_tickers)
        if type == 'stock' and not redundant_indices.all():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            coroutine = fetch_yield_fs if market.lower() == 'foreign' else fetch_yield_rs
            yields = loop.run_until_complete(
                tickers_map( df.loc[~redundant_indices].ticker, coroutine)
            )
            loop.run_until_complete(asyncio.sleep(0))
            loop.close()
            df.loc[~redundant_indices, 'yield'] = yields

        for _, security in df[~df.ticker.isin(present_tickers)].iterrows():
            s = Security(
                ticker=security['ticker'],
                name=security['name'],
                logo=security['logo'],
                currency=security['currency'],
                exchange=security['exchange'],
                stock=security['type'] == 'stock',
                price=security['price'],
                _yield=security['yield'],
                foreign=market == 'foreign',
            )
            securities.append(s)

        for s in securities:
            if s.ticker not in actual_tickers:
                s.save()

    if securities is None:
        return []


    # TODO: limits
    cache.set(query, tuple([s.id for s in securities]) if securities else tuple())

    return securities
