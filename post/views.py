import json
from django.shortcuts import render
from django.http import JsonResponse
from .services import search_posts

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
            return JsonResponse(result, safe=False, json_dumps_params={'ensure_ascii': False})
            """
            return JsonResponse([{
                    "title": "Заголовок",
                    "text": "Основной текст новости",
                    "poster": "https://bcs-express.ru/static/articlehead/5072.jpg",
                    "date": "2020-03-09'T'23:59:59",
                    "source": "БКС Экспресс",
                    "link": "https://bcs-express.ru/novosti-i-analitika/2020429427-koronovirus-b-et-po-severstali",
            }] * limit, safe=False, json_dumps_params={'ensure_ascii': False})
            """
        except (TypeError, KeyError) as e:
            return JsonResponse({
                'status': 'false',
                'message': str(e),
            }, status=400)
    return JsonResponse({
        'status': 'false',
        'message': 'Method not allowed. Use POST'
    }, status=405)
