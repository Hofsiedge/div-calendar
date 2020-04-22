# security/serializers.py
from rest_framework import serializers
from .models import Security


class SecuritySerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='get_type', read_only=True)
    class Meta:
        model = Security
        fields = ['ticker', 'isin', 'name', 'logo', 'currency',
                  'exchange', 'price', 'yield', 'type']
        read_only_fields = ['last_update']
        extra_kwargs = {
            'foreign': {'write_only': True},
            '_yield': {'view_name': 'yield'},
        }

    def create(self, validated_data):
        security = Security(
            ticker=validated_data['ticker'],
            isin=validated_data['isin'],
            name=validated_data['name'],
            logo=validated_data['logo'],
            currency=validated_data['currency'],
            exchange=validated_data['exchange'],
            stock=validated_data['stock'],
            foreign=validated_data['foreign'],
            price=validated_data['price'],
            _yield=validated_data['yield'],
        )
        message.save()
        return message

SecuritySerializer._declared_fields['yield'] = serializers.CharField(source='_yield')
