from django.db import models


class Post(models.Model):

    security    = models.ForeignKey('security.Security', on_delete=models.CASCADE)
    date        = models.DateTimeField()
    title       = models.CharField(max_length=200)
    text        = models.TextField()
    source      = models.CharField(max_length=50)
    poster      = models.URLField(max_length=200, blank=True)
    link        = models.URLField(max_length=200)


    def __str__(self):
        return f'Post on {self.security} {self.date}: {self.title[:50]}'

    def formatted_date(self) -> str:
        return self.date.isoformat()
