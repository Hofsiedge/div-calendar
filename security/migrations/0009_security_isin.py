# Generated by Django 3.0.4 on 2020-04-22 08:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('security', '0008_auto_20200418_2204'),
    ]

    operations = [
        migrations.AddField(
            model_name='security',
            name='isin',
            field=models.CharField(blank=True, max_length=25, unique=False),
        ),
    ]
