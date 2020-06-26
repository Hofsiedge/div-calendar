import aiohttp, asyncio, datetime, requests
from collections        import defaultdict
from dataclasses        import dataclass, field
from misc.services      import fetch_async
from security.models    import Security
from typing             import DefaultDict, Dict, List, Optional, Optional, Tuple, Union
from bs4                import BeautifulSoup        # type: ignore[import]

# TODO: abstract base class
class Source:
    pass


@dataclass(frozen=True)
class TradingGround:
    id:         str
    id_numeric: int
    name:       str
    ticker:     str

    def __post_init__(self):
        object.__setattr__(self, 'name', Investfunds.market_filter[self.name])

    @property
    def valid(self) -> bool:
        return self.name is not None


@dataclass(frozen=True)
class SearchStruct:
    id:                 str
    id_numeric:         int
    name:               str
    isin:               str
    url:                str
    trading_grounds:    List[TradingGround] = field(default_factory=list)

    def __post_init__(self):
        object.__setattr__(self, 'url', self.url.replace(r'\/', '/'))


# TODO: make common
@dataclass(frozen=True)
class Dividend:
    cutoff_date:            datetime.date
    registry_closing_date:  datetime.date
    payout:                 float
    forecast:               bool
    currency:               str


@dataclass(frozen=True)
class SingleStockFeatures:
    price:      float
    currency:   str
    yield_:     float
    foreign:    bool
    dividends:  List[Dividend] = field(default_factory=list)


class Investfunds(Source):

    market_filter: DefaultDict[str, Optional[str]] = defaultdict(lambda: None, {
        'Московская Биржа':                     'MOEX',
        'Московская Биржа. Внебиржевые сделки': 'MOEX',
        'Санкт-Петербургская биржа':            'SPBEX',
        'NASDAQ':                               'NASDAQ',
    })


    @staticmethod
    def search(query: str) -> List[Security]:
        r = requests.get(f'https://investfunds.ru/stocks/?searchString={query}')
        if r.status_code != 200:
            print(r.status_code, r.text)
            return []

        raw_data:   List[Dict[str, Union[str, int, List[Dict[str, Union[str, int]]]]]] = r.json()['currentResults']
        data:       List[SearchStruct] = []

        if len(raw_data) == 1 and "error" in raw_data[0].keys():
            # TODO: log -> raw_data[0]['error']
            return []

        for entry in raw_data:
            trading_grounds = [TradingGround(**{
                'id_numeric': raw_grounds.pop('id.numeric'),    # type: ignore[union-attr]
                **raw_grounds                                   # type: ignore[arg-type] 
            }) for raw_grounds in entry.pop('trading_grounds')] # type: ignore[union-attr]
            data.append(SearchStruct(**{                        # type: ignore[arg-type]
                'id_numeric':       entry.pop('id.numeric'),
                'trading_grounds':  [market for market in trading_grounds if market.valid],
                **entry,
            }))

        securities: List[Security] = fetch_async(data, Investfunds._construct_security)

        return securities


    @staticmethod
    async def _construct_security(session: aiohttp.ClientSession,
                                  search_struct: SearchStruct) -> Optional[Security]:
        """ construct a Security from a SearchStruct """
        urls = []
        for trading_ground in search_struct.trading_grounds:
            urls.append(f'https://investfunds.ru{search_struct.url}{trading_ground.id}/#tab_1')

        data: List[SingleStockFeatures] = filter(
            None,
            [await Investfunds._fetch_single_stock(session, url) for url in urls],
        )

        # TODO: support multiple exchanges for single security.

        securities = [Security(
            ticker  = trading_ground.ticker,
            isin    = search_struct.isin,
            name    = search_struct.name,
            stock   = True,
            currency = values.currency,
            exchange = trading_ground.name,
            logo    = '',
            price   = values.price,
            _yield  = values.yield_,
            foreign = values.foreign,
        ) for trading_ground, values in zip(search_struct.trading_grounds, data)]

        if len(securities) == 0:
            return None
        # TODO: return all
        return securities[0]


    @staticmethod
    async def _fetch_single_stock(session: aiohttp.ClientSession, url: str) \
            -> Optional[SingleStockFeatures]:
        """ fetch & parse (price, currency, yield, foreign, dividends) """
        async with session.get(url) as r:
            if r.status != 200:
                # TODO: log
                return None
            text = await r.text()
            soup = BeautifulSoup(text, 'html.parser')

            # price & currency
            try:
                price       = float(soup.find('div', class_='price').text)
                widget      = soup.find('div', class_='widget_price left widget_price_bond')
                currency    = widget.find('div', class_='value').text
            except AttributeError as e:
                # TODO: log
                return None

            # yield
            try:
                yield_str = soup.find('ul', {'class': 'param_list'})\
                        .find('span', text='Дивидендная доходность (за 4 квартала)')\
                        .find_next('div', {'class': 'value'}).text
                yield_ = float(yield_str[:-1])
            except AttributeError as e:
                # TODO: log that yield could not be parsed
                yield_ = 0.0

            # foreign
            temp = soup.find_all('div', class_='inner_ttl')
            if len(temp) != 1:
                # TODO: log: invalid HTML layout
                pass
            *branch, country = temp[0].text.split(',')
            foreign = country.strip() != 'Россия'

            # dividends
            div_rows = soup.find('div', text='Сумма выплаты')\
                    .findParent('table').find('tbody').find_all('tr')

            dividends: List[Dividend] = []
            for tr in div_rows:
                values              = (div.text.strip() for div in tr('div'))
                cutoff              = datetime.datetime.strptime(next(values), '%d.%m.%Y').date()
                registry_closing    = datetime.datetime.strptime(next(values), '%d.%m.%Y').date()
                payout_str, currency = next(values).split()
                payout              = float(payout_str)
                dividends.append(Dividend(cutoff, registry_closing, payout, False, currency))

            return SingleStockFeatures(price, currency, yield_, foreign, dividends)
