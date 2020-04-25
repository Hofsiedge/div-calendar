from time import sleep
from collections import namedtuple
from ..models import Security
from . import search_securities

SecurityInfo = namedtuple('SecurityInfo', ['ticker', 'stock', 'foreign'])

def reload_securities():
    info = [SecurityInfo(s.ticker, s.stock, s.foreign) for s in Security.objects.all()]
    for i in info:
        search_securities(
            i.ticker,
            'stock' if i.stock else 'bond',
            0,
            10,
            'foreign' if i.foreign else 'russian'
        )
