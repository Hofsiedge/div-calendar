import json
from django.shortcuts import render
from django.http import JsonResponse
from .services import search_posts
from .serializers import PostSerializer

def get_posts(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            if not {'limit', 'offset', 'securities'} <= data.keys():
                raise KeyError(f"Missing arguments")

            limit = int(data['limit'])
            offset = int(data['offset'])
            securities = data['securities']
            if type(limit) != int or type(offset) != int\
            or not securities or type(securities) != list:
                raise TypeError("Incorrect argument format")

            for i in securities:
                if type(i) != str:
                    raise TypeError("Incorrect argument format")

            result = search_posts(securities, offset, limit)
            serializer = PostSerializer(result, many=True)
            return JsonResponse(serializer.data, safe=False, json_dumps_params={'ensure_ascii': False})

        except (TypeError, KeyError) as e:
            return JsonResponse({
                'status': 'false',
                'message': str(e),
            }, status=400)
    return JsonResponse({
        'status': 'false',
        'message': 'Method not allowed. Use POST'
    }, status=405)
