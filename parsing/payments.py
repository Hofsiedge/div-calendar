import datetime, requests
import pandas as pd
from bs4 import BeautifulSoup

def parse_dohod(ticker: str, start: datetime.date, end: datetime.date) -> pd.DataFrame:
    r = requests.get(f"https://www.dohod.ru/ik/analytics/dividend/{ticker.lower()}")
    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, features='html.parser')
    tables = soup.findAll("table", {"class": "content-table"})
    rows = tables[1].findChildren("tr")

    df = pd.DataFrame(columns={'date', 'forecast', 'dividends', 'name', 'logo', 'currency'})
    dates, forecasts, dividends = [], [], []

    for row in rows:
        tds = [td.getText() for td in row.findChildren("td")
               if 'hidden' not in td.get('class', [])
               and td.get('style', '') != 'display: none;']
        if not tds:
            continue
        date = datetime.datetime.strptime(tds[0].strip().split()[0], '%d.%m.%Y').date()
        if not start < date < end:
            continue
        forecasts.append('forecast' in row.get('class', []))
        dates.append(date)
        dividends.append(float(tds[1]))

    df.date = dates
    df.forecast = forecasts
    df.dividends = dividends
    # TODO: replace with data from the DB
    df.name.fillna(ticker, inplace=True)
    df.logo.fillna("https://static.tinkoff.ru/brands/traiding/RU0009029540.png", inplace=True)
    df.currency.fillna("RUB", inplace=True)

    return df

def fetch_payments(securities: list, start_date: str, end_date: str):
    start   = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
    end     = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
    data = []
    for security in securities:
        res = parse_dohod(security, start, end)
        if res is not None:
            data.append(res)
    return pd.concat(data).to_dict(orient='records')
