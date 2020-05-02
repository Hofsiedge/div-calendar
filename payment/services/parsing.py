import datetime, requests, re, traceback, sys
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
            forecast='forecast' in row.get('class', []) and row.find('img') is None,
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
    interval        = datetime.timedelta(float((d['Периодичность выплат'] or '0').replace(',', '.'))\
            or 365 / float(d['Количество выплат в год'].replace(',', '.')))

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


def parse_ycharts(security: Security, start: datetime.date, end: datetime.date) -> list:
    r = requests.get(f'https://ycharts.com/companies/{security.ticker}/dividend')
    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, 'html.parser')
    payments = []
    last_payments = []
    for tr in soup.find('table', {'class': 'histDividendDataTable'}).find('tbody').find_all('tr')[1:]:

        try:

            date = datetime.datetime.strptime(tr.find('td', {'class': 'col3'}).text, '%m/%d/%Y').date()
            if len(last_payments) == 2 and not start <= date <= end:
                continue

            payment = Payment(
                security = security,
                date     = date,
                dividends= float(tr.find('td', {'class': 'col6'}).text),
                forecast = False,
            )
            if len(last_payments) < 2:
                last_payments.append(payment)
            if start <= date <= end:
                payments.append(payment)

        except Exception as e:
            print('<BUG: fb_payments>\nException occured during fetching '
                    f'payments for {security}, {start}, {end}:', e)
            continue

    if len(last_payments) == 2:
        last_div    = last_payments[0].dividends
        last_date   = last_payments[0].date
        interval    = last_date - last_payments[1].date
        # TODO: switch to Python 3.9 and refactor with the Walrus operator
        # TODO: but that would require to deploy with Docker containers as Heroku doesn't support Python 3.6+
        last_date   += interval
        while (last_date <= end):
            payments.append(Payment(
                security = security,
                date     = last_date,
                dividends= last_div,
                forecast = True,
            ))
            last_date += interval

    return payments


def parse_tinkoff(security: Security, start: datetime.date, end: datetime.date) -> list:

    url = f'https://api.tinkoff.ru/trading/bonds/list'
    r = requests.post(
        url, json = {
            'filter':       security.ticker,
            'country':      'Russian',
            'sortType':     'ByName',
            'orderType':    'Asc',
            'start':        0,
            'end':          20,
        }
    )

    if r.status_code != 200:
        print(r.status_code, r.text)
        return None

    data = r.json()['payload']['values']
    p = re.compile(r'(?<=Номинал: )(?P<nominal>\d+)(?:.*)'
                    '(?<=Текущий купон \(всего\):)(?: \d+ \()'
                    '(?P<coupons>\d+)', re.DOTALL)


    def get_coupons(nominal: float, coupon: float, coupons: int, period: datetime.timedelta,
                    start: datetime.date, end: datetime.date, redemption: datetime.date):
        # Assuming that the last coupon is paid the day before redemption
        last_coupon     = redemption - datetime.timedelta(1)

        current_date = last_coupon
        dates = []
        while current_date >= start:
            dates.append(current_date)
            current_date -= period

        payments = [Payment(
            security=security,
            date=date,
            dividends=coupon,
            forecast=date > datetime.datetime.now().date()
        ) for date in dates]

        if start <= redemption <= end:
            payments.append(Payment(
                security=security,
                date=end,
                dividends=nominal,
                forecast=redemption > datetime.datetime.now().date()
            ))

        return payments

    coupons = []
    for i in data:
        try:
            symbol = i['symbol']
            if symbol['ticker'] != security.ticker:
                continue

            match   = next(p.finditer(symbol['fullDescription'])).groupdict()
            period  = i['couponPeriodDays']
            coupon  = i['couponValue']
            redemption = datetime.datetime.strptime(i['endDate'], '%Y-%m-%dT%H:%M:%SZ').date()
            floating = i['floatingCoupon']

            # TODO: filter by amortization as well
            if not floating:
                coupons.extend(get_coupons(match['nominal'], coupon, match['coupons'],
                               datetime.timedelta(period), start, end, redemption))

        except StopIteration:
            print(f"Couldn't obtain payments basis of {security}")
            continue

        except KeyError as e:
            if e.args[0] != 'symbol':
                print(f'Failed to parse some fields ({e.args[0]}...) for {security}')
            continue

        except Exception as e:
            print(f'Failed to parse payments on "{security.ticker}"')
            traceback.print_exc(file=sys.stdout)
            continue

    return coupons


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
        elif security.foreign and security.stock:
            data.extend(parse_ycharts(security, start, end) or [])
        else:
            data.extend(parse_tinkoff(security, start, end) or [])

    return data
