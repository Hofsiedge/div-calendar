from time import sleep
from collections import namedtuple
from ..models import Security
from . import search_securities

SecurityInfo = namedtuple('SecurityInfo', ['ticker', 'stock', 'foreign'])

def reload_securities():
    securities = list(Security.objects.all())
    info = [SecurityInfo(s.ticker, s.stock, s.foreign) for s in securities]
    security_iter = iter(securities)
    for i in info:
        s = next(security_iter)
        s.delete()
        search_securities(
            i.ticker,
            'stock' if i.stock else 'bond',
            0,
            10,
            'foreign' if i.foreign else 'russian'
        )
