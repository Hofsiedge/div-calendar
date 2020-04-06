import requests
import pandas as pd
from security.models import Security

LIMIT = 100

"""
def parse_single_tradingview(ticker: str) -> pd.DataFrame:
    df = pd.DataFrame(columns=columns, data=data)
    df = df[['secid', 'name', 'type']][df.type.str.match(r'.*(share|bond)')].reset_index(drop=True)
    df = df[:limit]
    df.rename(columns={'secid': 'ticker'}, inplace=True)
    df = df[df.ticket.str.contains(query, case=False)
            | df.name.str.contains(query, case=False)].reset_index(drop=True)
    df.type = df.type.apply(lambda x: x.split('_')[-1])
    df.fillna(value='', inplace=True)
    return df
"""

def fetch_yield_rus_stock(ticker: str):
    r = requests.get('https://www.dohod.ru/ik/analytics/dividend/{ticker.lower()}')
    if r.status != 200:
        return 0
    soup = BeautifulSoup(r.text)
    return float(soup.find('tr', {'class': 'frow'}).find('td').text[:-1])

def fetch_yield_foreign_stock(ticker: str):
    r = requests.get(f'https://www.streetinsider.com/dividend_history.php?q={ticker}')
    if r.status_code != 200:
        return 0
    soup = BeautifulSoup(r.text)
    soup.find('div', {'class': 'dividend-info'}).findAll('strong')


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
    # price, symbol.ticker, symbol.symbolType, symbol.currency,
    # symbol.showName, symbol.exchange, symbol.logoName, 
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
        logos.append(f'https://static.tinkoff.ru/brands/traiding/{symbol["logoName"]}')
        prices.append(i['price']['value'])
        yields.append(i.get('totalYield', 0))

    # TODO: yields for stocks

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
    return res.to_dict(orient='records')
