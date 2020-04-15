import requests, aiohttp, asyncio, datetime
import pandas as pd
from bs4 import BeautifulSoup
from django.core.cache import cache
from django.db.models import Q
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

async def fetch_yield_price_fb(session: aiohttp.ClientSession, url: str) -> tuple:
    async with session.get(url) as r:
        if r.status != 200:
            return None
        text = await r.text()
        soup = BeautifulSoup(text, 'html.parser')
        d = {'Валюта': None, 'Номинал': None}
        for row in soup.find_all('table')[-2].find_all('tr'):
            tds = row.find_all('td')
            if len(tds) == 2 and tds[0].text.strip() in d:
                d[tds[0].text.strip()] = tds[1].text.strip()
        if d['Валюта'] not in {'RUB', 'USD'}:
            return None
        tables  = soup.find_all('table')
        try:
            _yield  = float(tables[4].find_all('td')[3].text.replace(',', '.'))
            price   = float(d['Номинал'].replace(',', '.')) \
                * float(soup.find_all('table')[3].find_all('td')[7].text.replace(',', '.'))

            return d['Валюта'], price, _yield
        except:
            return None


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
    securities = []

    for i in data:
        symbol = i['symbol']
        logo_name = 'x160.'.join(symbol['logoName'].split('.'))
        securities.append(Security(
            ticker  = symbol['ticker'],
            name    = symbol['showName'],
            stock   = type.lower() == 'stock',
            currency = symbol['currency'],
            exchange = symbol['exchange'],
            logo    = f'https://static.tinkoff.ru/brands/traiding/{logo_name}',
            price   = i['price']['value'],
            _yield  = i.get('totalYield', 0),
            foreign =market.lower() == 'foreign',
        ))

    return securities


def search_fb(query: str):
    r = requests.get(f'https://www.finanz.ru/resultaty-poiska?_type=anleihen&_search={query}')
    soup = BeautifulSoup(r.text, 'html.parser')
    securities = []
    urls = []
    for row in soup.find_all('table')[1].find_all('tr'):
        tds     = row.find_all('td')
        try:
            urls.append('https://www.finanz.ru' + tds[0].find('a')['href'])
            securities.append(Security(
                name = tds[0].text.strip(),
                ticker  = tds[4].text.strip(),
                stock=False,
                exchange='',
                logo='',
                foreign=True
            ))
        except Exception as e:
            continue

    result = []
    values = iter(fetch_async(urls, fetch_yield_price_fb))
    for security in securities:
        value = next(values)
        if value is None:
            continue
        currency, price, _yield = value
        security.currency   = currency
        security.price      = price
        security._yield     = _yield
        security.save()
        result.append(security)

    return result


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
            return Security.objects.filter(
                Q(foreign = market.lower() == 'foreign'),
                Q(stock = type == 'stock'),
                Q(ticker__icontains=query) | Q(name__icontains=query))

        securities = []
        if type == 'bond' and market.lower() == 'foreign':
            print('FB')
            securities = search_fb(query)
        else:
            securities  = search_tinkoff(query, type, offset, limit, market, currency)
        # TODO: profile to check that set improves performance
        present = Security.objects.filter(ticker__in=set([s.ticker for s in securities]))

        present_tickers = {s.ticker for s in present.only('ticker')}
        missing = [s for s in securities if s.ticker not in present_tickers]

        yesterday   = datetime.datetime.now() - datetime.timedelta(1)
        outdated    = present.filter(last_update__lt=yesterday)

        s_dict = {s.ticker: s for s in securities}
        for security in outdated:
            source          = s_dict[security.ticker]
            security.price  = source.price
            security._yield = source._yield

        if type == 'stock' and (len(missing) > 0 or outdated.exists()):
            source  = missing + list(outdated)
            yields  = iter(fetch_async(
                [s.ticker for s in source],
                fetch_yield_fs if market.lower() == 'foreign' else fetch_yield_rs
            ))
            for s in source:
                s._yield = yields.__next__()
                s.save()

        # by now missing is already included in present (present was not
        # evaluated yet)
        securities = list(present)

    # TODO: limits
    cache.set(query, tuple([s.id for s in securities]) if securities else tuple())

    return securities
