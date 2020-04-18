# post/serializers.py
from rest_framework import serializers
from .models import Post


class PostSerializer(serializers.ModelSerializer):

    date        = serializers.CharField(source='formatted_date', read_only=True)
    ticker      = serializers.CharField(source='security.ticker', read_only=True)
    logo        = serializers.CharField(source='security.logo', read_only=True)

    class Meta:
        model = Post
        fields = ['date', 'ticker', 'logo', 'title', 'text', 'source', 'poster', 'link']
        read_only_fields = ['date', 'ticker']

