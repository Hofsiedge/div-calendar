import datetime, requests
import pandas as pd
from bs4 import BeautifulSoup
from security.models import Security

def parse_dohod(ticker: str, start: datetime.date, end: datetime.date) -> pd.DataFrame:
    r = requests.get(f"https://www.dohod.ru/ik/analytics/dividend/{ticker.lower()}")
    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, features='html.parser')
    yield_ = float(soup.find('tr', {'class': 'frow'}).find('td').text.strip()[:-1])
    if yield_ == 0:
        return None

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
    df.name.fillna(ticker, inplace=True)
    security = Security.objects.get(ticker=ticker)
    df.logo.fillna(security.logo if security else "https://static.tinkoff.ru/brands/traiding/RU0009029540x160.png",
                   inplace=True)
    df.currency.fillna(entity.currency if entity else "", inplace=True)

    return df

def fetch_payments(securities: list, start_date: str, end_date: str):
    start   = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
    end     = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
    data = []
    for security in securities:
        res = parse_dohod(security, start, end)
        if res is not None:
            data.append(res)
    return pd.concat(data).to_dict(orient='records') if data else []
