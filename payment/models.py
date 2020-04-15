from django.db import models

# TODO: add currency. Sometimes currencies are changed over the period
class Payment(models.Model):
    """ Dividend payment or bond redemption """

    security    = models.ForeignKey('security.Security', on_delete=models.CASCADE)
    date        = models.DateField()
    dividends   = models.FloatField()
    forecast    = models.BooleanField()    # needs updating
    last_update = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Payment {self.security} {self.date}: {self.dividends}'\
               f'{" (forecast)" if self.forecast else ""}'
