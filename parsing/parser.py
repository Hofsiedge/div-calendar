import requests
import pandas as pd

LIMIT = 100

def parse_moex(query: str, limit: int) -> pd.DataFrame:
    r = requests.get(f"https://www.moex.com//iss/securities.json?q={query}&limit={LIMIT}&lang=ru")
    if r.status_code != 200:
        return None
    columns = r.json()['securities']['columns']
    data = r.json()['securities']['data']
    df = pd.DataFrame(columns=columns, data=data)
    df = df[['secid', 'name', 'type']][df.type.str.match(r".*(share|bond)")].reset_index(drop=True)
    df = df[:limit]
    df.rename(columns={'secid': 'ticker'}, inplace=True)
    df = df[df.ticket.str.contains(query, case=False)
            | df.name.str.contains(query, case=False)].reset_index(drop=True)
    df.type = df.type.apply(lambda x: x.split('_')[-1])
    df.fillna(value="", inplace=True)
    return df

def search_tinkoff(query: str, type: str, offset: int, limit: int, market: str) -> pd.DataFrame:
    url = f"https://api.tinkoff.ru/trading/{'stocks' if type == 'stock' else 'bonds'}/list"
    # TODO: market
    r = requests.post(
        url, json = {
            "filter": query,
            "country": "All",
            "sortType": "ByName",
            "orderType": "Asc",
            "start": offset,
            "end": offset + limit,
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
        yields.append(i.get('totalYield', ''))

    # TODO: yields for stocks
    # r = requests.post("https://api.tinkoff.ru/trading/bonds/get",
    # json={"ticker": "RU000A100WF7"})

    df.ticker   = tickers
    df.name     = names
    df.type     = types
    df.logo     = logos
    df.price    = prices
    df.currency = currencies
    df.exchange  = exchanges
    df['yield'] = yields

    return df


def search(query: str, type: str, offset: int, limit: int, market: str):
    res = search_tinkoff(query, type, offset, limit, market)
    if res is None:
        return None
    return res.to_dict(orient='records')
