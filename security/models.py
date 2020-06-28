from django.db import models
from typing import TypeVar

T = TypeVar('T', bound='Security')

class Security(models.Model):
    """ A stock or a bond"""

    # TODO: index by ticker
    ticker      = models.CharField(max_length=25, unique=True)
    isin        = models.CharField(max_length=25, unique=True, blank=False)
    name        = models.CharField(max_length=150)
    logo        = models.URLField(max_length=200, blank=True)
    currency    = models.CharField(max_length=3, blank=True)
    exchange    = models.CharField(max_length=6, blank=True) # MOEX, SPB, NASDAQ, NYSE
    stock       = models.BooleanField() # stock or bond
    foreign     = models.BooleanField()
    price       = models.FloatField(blank=True)
    _yield      = models.FloatField(blank=True)
    last_update = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{"s" if self.stock else "b"}:{self.ticker}'

    def get_type(self):
        return 'stock' if self.stock else 'bond'

    def matches_fields(self: T, other: T) -> bool:
        """ returns True if all the fields (except last_update & id) are equal) """
        return self.ticker == other.ticker and self.isin == other.isin\
                and self.name == other.name and self.logo == other.logo\
                and self.currency == other.currency and self.exchange == other.exchange\
                and self.stock == other.stock and self.foreign == other.foreign\
                and self.price == other.price and self._yield == other._yield

