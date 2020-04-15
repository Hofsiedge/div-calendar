# payment/serializers.py
from rest_framework import serializers
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):

    currency    = serializers.CharField(source='security.currency', read_only=True)
    name        = serializers.CharField(source='security.ticker', read_only=True)
    logo        = serializers.CharField(source='security.logo', read_only=True)

    class Meta:
        model = Payment
        fields = ['date', 'forecast', 'dividends', 'currency', 'name', 'logo']
        read_only_fields = ['last_update', 'currency', 'name', 'logo']

