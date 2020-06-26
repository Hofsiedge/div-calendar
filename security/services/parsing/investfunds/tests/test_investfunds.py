import datetime, pickle, random, requests
from contextlib         import asynccontextmanager
from dataclasses        import dataclass
from django.core.cache  import cache
from django.test        import TestCase
from security.models    import Security
from typing             import Any, Optional
from unittest.mock      import AsyncMock, MagicMock, Mock, patch

from ..investfunds      import Dividend, Investfunds, SingleStockFeatures
from misc.services      import fetch_async


HIMCP_search_sample = {
    "total": 1,
    "currentCount": 1,
    "currentResults": [{
        "id":"544",
        "id.numeric": 544,
        "name": "Химпром, акция прив.",
        "isin":"RU0009099006",
        "url":"\/stocks\/Himprom-pref\/",
        "trading_grounds": [{
                "id": "1",
                "id.numeric": 1,
                "name": "Московская Биржа",
                "ticker": "HIMCP"
            }, {
                "id": "455",
                "id.numeric": 455,
                "name": "Московская Биржа. Внебиржевые сделки",
                "ticker": "HIMCP"
            }
        ]
    }],
    "verifyHash": "",
}

CWD         = 'security/services/parsing/investfunds/tests'
MOEX1_path  = f'{CWD}/moex1.html.bin'
MOEX2_path  = f'{CWD}/moex2.html.bin'


@dataclass
class AsyncResponseMock:
    status: int
    _text:  str

    async def text(self):
        return self._text


@asynccontextmanager
async def  mock_async_getter(session, url):
    path: Optional[str] = None
    if url.startswith('https://investfunds.ru/stocks/Himprom-pref/1/'):
        path = MOEX1_path
    elif url.startswith('https://investfunds.ru/stocks/Himprom-pref/455/'):
        path = MOEX2_path
    if path is None:
        raise ValueError(f'Wrong URL for async get: {url}')

    with open(path, 'rb') as f:
        yield AsyncResponseMock(status=200, _text=pickle.load(f))


# TODO: test edge cases
class InvestfundsTestCase(TestCase):

    def test_investfunds_search_available(self):
        """ Investfunds stock search is responding with 200 OK """
        if cache.get('test_investfunds_search_available') is not None:
            return
        stock   = random.choice(('apple', 'tesla', 'gaz', 'micro', 'tech', 'euro'))
        r       = requests.get(f'https://investfunds.ru/stocks/?searchString={stock}')
        self.assertTrue(r.ok)
        # check once an hour or less frequently
        cache.set('test_investfunds_search_available', True, 60 * 60)


    @patch('security.services.parsing.investfunds.investfunds.requests.get')
    def test_investfunds_stock_not_found(self, mock_get: MagicMock) -> None:
        mock_get.return_value.ok            = True
        mock_get.return_value.status_code   = 200
        mock_get.return_value.json          = lambda: {
            "total": 0,
            "currentCount": 1,
            "currentResults": [{
                "error": u"Количество совпадений: 0",
            }],
            "verifyHash":"",
        }
        self.assertEqual(Investfunds.search('himp'), [])


    @patch('misc.services.parsing.aiohttp.ClientSession.get', new=mock_async_getter)
    def test_investfunds_single_stock_features(self):
        features = fetch_async(
            ['https://investfunds.ru/stocks/Himprom-pref/1/'],
            Investfunds._fetch_single_stock,
        )
        self.assertEqual(len(features), 1)
        self.assertEqual(features[0].yield_, 2.99)
        self.assertEqual(features[0].price, 5.88)
        self.assertFalse(features[0].foreign)
        self.assertEqual(len(features[0].dividends), 10)
        self.assertEqual(features[0].dividends[0].cutoff_date, datetime.date(2019, 12, 6))
        self.assertEqual(features[0].dividends[4].registry_closing_date, datetime.date(2018, 12, 11))
        self.assertEqual(features[0].dividends[6].payout, 0.202)
        self.assertEqual(features[0].dividends[8].currency, 'RUB')


    @patch('misc.services.parsing.aiohttp.ClientSession.get', new=mock_async_getter)
    @patch('security.services.parsing.investfunds.investfunds.requests.get')
    def test_investfunds_stock_parsing(self, mock_get: MagicMock):
        mock_get.return_value.ok            = True
        mock_get.return_value.status_code   = 200
        mock_get.return_value.json          = lambda: HIMCP_search_sample

        res = Investfunds.search('himcp')
        self.assertEqual(len(res), 1)

        security = Security(
            ticker      = 'HIMCP',
            isin        = 'RU0009099006',
            name        = 'Химпром, акция прив.',
            logo        = '',
            currency    = 'RUB',
            exchange    = 'MOEX',
            stock       = True,
            foreign     = False,
            price       = 5.88,
            _yield      = 2.99,
        )
        self.assertTrue(res[0].matches_fields(security))
