import re, requests, locale, aiohttp, asyncio, datetime, string, sys, traceback
from bs4 import BeautifulSoup       # type: ignore[import]
from collections import namedtuple, defaultdict
from dataclasses import dataclass, field
from django.core.cache import cache
from django.db.models import Q
from misc.services import fetch_async, Transliterator
from security.models import Security
from typing import Any, DefaultDict, Dict, Iterable, List, Optional, Set, Tuple, Union, cast

from .investfunds import Investfunds

locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')

transliterator = Transliterator('mappings')
russian_symbols = frozenset('абвгдеёжзийклмнопрстуфхцчшщыъьэюя')
english_symbols = frozenset(string.ascii_lowercase)


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


async def fetch_yield_price_fb(session: aiohttp.ClientSession, url: str) -> Tuple:
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


async def rusbonds_single_bond(session: aiohttp.ClientSession, tool: int) -> Security:
    d   = {key: None for key in (
        'ISIN код:', 'Наименование:', 'Номинал:', 'Данные госрегистрации:',
        'Цена срвзв. чистая, % от номинала:',
    )}
    async with session.get(f'https://www.rusbonds.ru/ank_obl.asp?tool={tool}') as r:
        if r.status != 200:
            return None
        r.encoding = 'cp1251'

        text = await r.text()
        soup = BeautifulSoup(text, 'html.parser')

        for tr in filter(
            lambda x: len(x) == 2,
            soup.find('table', {'class': 'tbl_data'}).find_all('tr', {'class': ''})):

            tds = tr.find_all('td')
            try:
                first = tds[0].text.strip()
            except Exception as e:
                print(e)
                print(tr.text)
                return
            if len(tds) == 2 and first in d:
                d[first] = tds[1].text.strip()

    async with session.get('https://www.rusbonds.ru/tooldistrib.asp?tool={tool}') as r:
        if r.status != 200:
            return None
        r.encoding = 'cp1251'

        text = await r.text()
        soup = BeautifulSoup(text, 'html.parser')
        try:
            # FIXME
            tds  = soup.find('table', {'class': 'tbl_data tbl_headgrid'}).find_all('td')
        except AttributeError as e:
            print(f'Fail 1: {tool}\n{e}')
            return None
        d['Торговая площадка'] = tds[1].text.strip()

    async with session.get('https://www.rusbonds.ru/tyield.asp?tool={tool}') as r:
        if r.status != 200:
            return None

        r.encoding = 'cp1251'
        text = await r.text()
        soup = BeautifulSoup(text, 'html.parser')
        trs  = soup.find('table', {'class': 'tbl_data'}).find_all('tr')
        tds  = trs[6].find_all('td')
        if decode(tds[0].text).strip() != 'Текущая дох-сть, % год.:':
            print('Wrong row in security parsing!')
            return None
        d['yield'] = float(tds[1].text.strip())


    security = Security(
        ticker  = d['ISIN код:'],
        name    = d['Наименование:'],
        price   = float(d['Номинал:'].split()[0]) * float(d['Цена срвзв. чистая, % от номинала:']),
        stock   = False,
        logo    = '',
        foreign = False, # TODO: check
        _yield  = d['yield'],
        exchange = 'MOEX' if d['Торговая площадка'] == 'МосБиржа' else 'SPBEX',
        currency = d['Номинал:'].split()[-1],
    )
    return security


# TODO: deal with pagination
def search_rusbonds(query: str, offset: int = None, limit: int = None) -> list:
    # exchanging
    r = requests.get(
        f'https://www.rusbonds.ru/srch_simple.asp',
        params={'go': 1, 'status': 'T', 'nick': query.encode('cp1251')}
    )
    if r.status_code != 200:
        return []
    r.encoding = 'cp1251'

    soup = BeautifulSoup(r.text, 'html.parser')
    tool_pattern = re.compile('(?<=tool=)(\d+)')
    try:
        tools_exchanging = [int(tool_pattern.search(tr.find('a')['href']).group())
                            for tr in soup.find('table', {'class': 'tbl_data tbl_headgrid'})\
                            .find('tbody').find_all('tr') if tr]
    except AttributeError as e:
        print(e)
        tools_exchanging = []

    # placed
    r = requests.get(
        f'https://www.rusbonds.ru/srch_simple.asp',
        params={'go': 1, 'status': 'W', 'nick': query.encode('cp1251')}
    )
    if r.status_code != 200:
        return []

    r.encoding = 'cp1251'
    soup = BeautifulSoup(r.text, 'html.parser')
    try:
        tools_placed = [int(tool_pattern.search(tr.find('a')['href']).group())
                        for tr in soup.find('table', {'class': 'tbl_data tbl_headgrid'})\
                        .find('tbody').find_all('tr') if tr]
    except AttributeError as e:
        print(e)
        tools_placed = []

    securities_exchanging   = fetch_async(tools_exchanging, rusbonds_single_bond)
    securities_placed       = fetch_async(tools_placed, rusbonds_single_bond)

    return securities_exchanging + securities_placed



def search_tinkoff(query: str, type: str, offset: Optional[int] = None, limit: Optional[int] = None,
                   market: Optional[str] = None, currency: Optional[str] = None) -> List[Security]:
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
        print(r.status_code, r.text)
        return []

    data = r.json()['payload']['values']
    securities: List[Security] = []

    for i in data:
        try:
            symbol = i['symbol']
            logo_name = 'x160.'.join(symbol['logoName'].split('.'))
            securities.append(Security(
                ticker  = symbol['ticker'],
                isin    = symbol['isin'],
                name    = symbol['showName'],
                stock   = type.lower() == 'stock',
                currency = symbol['currency'],
                exchange = symbol['exchange'],
                logo    = f'https://static.tinkoff.ru/brands/traiding/{logo_name}',
                price   = i['price']['value'],
                _yield  = i.get('totalYield', 0),
                foreign = market.lower() == 'foreign',
            ))
        except Exception as e:
            print(f'Failed to parse security on "{query}"')
            traceback.print_exc(file=sys.stderr)
            continue

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
                name    = tds[0].text.strip(),
                ticker  = tds[4].text.strip(),
                isin    = tds[4].text.strip(),
                stock   = False,
                exchange= '',
                logo    = '',
                foreign = True
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
        result.append(security)

    return result


# TODO: update if contains outdated
def fetch_from_db(query: str, transliterated_query: Optional[str], type: str,
                  market: str, currency: Optional[str] = None):
    if transliterated_query is not None:
        return Security.objects.filter(
            Q(foreign = market.lower() == 'foreign'),
            Q(stock = type == 'stock'),
            Q(ticker__icontains=query) | Q(name__icontains=query) |
            Q(ticker__icontains=transliterated_query) | Q(name__icontains=transliterated_query))
    else:
        return Security.objects.filter(
            Q(foreign = market.lower() == 'foreign'),
            Q(stock = type == 'stock'),
            Q(ticker__icontains=query) | Q(name__icontains=query))


def search_securities(query: str, type: str, offset: Optional[int] = None, limit: Optional[int] = None,
                      market: Optional[str] = None, currency: Optional[str] = None) -> Iterable[Security]:
    if not query:
        return []

    query = query.lower()
    indices = cache.get(market[0] + type[0] + '_' + query)

    transliterated_query = None
    if not (set(query) & russian_symbols and set(query) & english_symbols):
        direction = ('ru', 'en') if set(query) & russian_symbols else ('en', 'ru')
        transliterated_query = transliterator.translit(query, *direction)

    if indices is not None:
        securities = Security.objects.filter(id__in=indices)

    else:
        if len(query) < 3:
            return fetch_from_db(query, transliterated_query, type, market)

        securities = []
        """
        if type == 'bond':
            if market.lower() == 'foreign':
                securities = search_fb(query)
            else:
                securities  = search_rusbonds(query)
                tickers     = {s.ticker for s in securities}
                securities2 = search_tinkoff(query, type, offset, limit, market, currency)
                # TODO: benchmark to compare with securities.extend([s for s in
                # securities2 if s.ticker not in tickers])
                securities.extend(filter(lambda s: s.ticker not in tickers, securities2))
        """
        if type == 'bond' and market.lower() == 'foreign':
            securities = search_fb(query)
        elif type == 'stock':
            securities  = Investfunds.search(query)
            if market.lower() == 'russian':
                securities_translit = Investfunds.search(transliterated_query)
                tickers = {s.ticker for s in securities}
                securities.extend(filter(lambda s: s.ticker not in tickers, securities_translit))
        else:   # russian bonds
            securities  = search_tinkoff(query, type, offset, limit, market, currency)
            if market.lower() == 'russian':
                if transliterated_query is not None:
                    securities_translit = search_tinkoff(transliterated_query,
                            type, offset, limit, market, currency)
                    securities_translit = Investfunds.search(transliterated_query)
                    tickers = {s.ticker for s in securities}
                    securities.extend(filter(lambda s: s.ticker not in tickers, securities_translit))

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

        if (len(missing) > 0 or outdated.exists()):
            source  = missing + list(outdated)
            if type == 'stock':
                """
                yields  = iter(fetch_async(
                    [s.ticker for s in source],
                    fetch_yield_fs if market.lower() == 'foreign' else fetch_yield_rs
                ))
                for s in source:
                    s._yield = yields.__next__()
                """
                pass
            for s in source:
                s.save()

        # by now missing is already included in present (present was not
        # evaluated yet)
        securities = list(present)

    securities = [s for s in securities
                  if query in s.ticker.lower() or query in s.name.lower()
                  or (transliterated_query is not None
                      and (transliterated_query in s.ticker.lower()
                           or transliterated_query in s.name.lower()))]
    if len(securities) == 0:
        securities = fetch_from_db(query, transliterated_query, type, market)

    # TODO: limits
    cache.set(market[0] + type[0] + '_' + query, tuple([s.id for s in securities]) if securities else tuple())

    return securities
