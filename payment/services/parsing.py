import datetime, requests, re
from bs4 import BeautifulSoup
from security.models import Security
from ..models import Payment

def parse_dohod(security: Security, start: datetime.date, end: datetime.date) -> list:
    if security is None:
        return None
    ticker = security.ticker

    r = requests.get(f"https://www.dohod.ru/ik/analytics/dividend/{ticker.lower()}")
    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, features='html.parser')
    yield_ = float(soup.find('tr', {'class': 'frow'}).find('td').text.strip()[:-1])
    if yield_ == 0:
        return None

    tables = soup.findAll("table", {"class": "content-table"})
    rows = tables[1].findChildren("tr")

    payments = []
    for row in rows:
        tds = [td.getText() for td in row.findChildren("td")
               if 'hidden' not in td.get('class', [])
               and td.get('style', '') != 'display: none;']
        if not tds:
            continue
        date = datetime.datetime.strptime(tds[0].strip().split()[0], '%d.%m.%Y').date()
        if not start < date < end:
            continue
        payments.append(Payment(
            security=security,
            date=date,
            dividends=float(tds[1]),
            forecast='forecast' in row.get('class', [])
        ))

    return payments


def parse_finanz(security: Security, start: datetime.date, end: datetime.date) -> list:
    if security is None:
        return None
    ticker = security.ticker

    pattern = re.compile(r'Инструмент успешно добавлен')
    r = requests.get(f'https://www.finanz.ru/resultaty-poiska?_type=anleihen&_search={ticker}')
    soup = BeautifulSoup(r.text, 'html.parser')
    # FIXME: always finds
    """
    if not pattern.search(soup.find('div', {'class': 'state_content'}).text):
        return None
    """

    d = {key: None for key in (
        'Валюта', 'Дата выпуска', 'Купон', 'Первая купонная выплата',
        'Номинал', 'Дата погашения', 'Периодичность выплат',
        'Количество выплат в год', 'Последняя купонная выплата'
    )}

    for row in soup.find_all('table')[-2].find_all('tr'):
        tds = row.find_all('td')
        if len(tds) == 2 and tds[0].text.strip() in d:
            d[tds[0].text.strip()] = tds[1].text.strip()

    currency        = d['Валюта']
    if currency not in {'RUB', 'USD', 'EUR'}:
        raise ValueError(f'Incorrect currency value: {currency}')
    first_coupon    = datetime.datetime.strptime(d['Первая купонная выплата'], '%d.%m.%Y').date()
    last_coupon     = datetime.datetime.strptime(d['Последняя купонная выплата'], '%d.%m.%Y').date()
    redemption_date = datetime.datetime.strptime(d['Дата погашения'], '%d.%m.%Y').date()
    nominal         = float(d['Номинал'].replace(',', '.'))
    coupon          = nominal * float(d['Купон'][:-1].replace(',', '.'))
    interval        = datetime.timedelta(float((d['Периодичность выплат'] or '0').replace(',', '.')) or 365 / float(d['Количество выплат в год'].replace(',', '.')))

    # ceiling trick (negated floor of negated)
    first = first_coupon if start <= first_coupon else \
        first_coupon - (-(start - first_coupon) // interval) * interval
    right_bound = min(end, last_coupon)
    dates  = (first + i * interval \
               for i in range(-(-max(right_bound - first, datetime.timedelta(0)) // interval)))

    payments = [Payment(
        security=security,
        date=date,
        dividends=coupon,
        forecast=date > datetime.datetime.now().date()
    ) for date in dates]

    if start <= redemption_date <= end:
        coupons.append(Payment(
            security=security,
            date=redemtion_date,
            dividends=nominal,
            forecast=redemption_date > datetime.datetime.now().date()
        ))

    return payments


def fetch_payments(tickers: list, start_date: str, end_date: str):
    start   = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
    end     = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
    data    = []
    for ticker in tickers:
        security = Security.objects.get(ticker=ticker)
        if not security.foreign and security.stock:
            data.extend(parse_dohod(security, start, end) or [])
        elif security.foreign and not security.stock:
            data.extend(parse_finanz(security, start, end) or [])
    return data
