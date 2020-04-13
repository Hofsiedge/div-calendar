from django.db import models


class Security(models.Model):
    """ A stock or a bond"""

    # TODO: index by ticker
    ticker      = models.CharField(max_length=10)
    name        = models.CharField(max_length=150)
    logo        = models.URLField(max_length=200)
    currency    = models.CharField(max_length=3)
    exchange    = models.CharField(max_length=6) # MOEX, SPB, NASDAQ, NYSE
    stock       = models.BooleanField() # stock or bond
    foreign     = models.BooleanField()
    price       = models.FloatField()
    _yield      = models.FloatField()
    last_update = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{"s" if self.stock else "b"}:{self.ticker}'

    def get_type(self):
        return 'stock' if self.stock else 'bond'
