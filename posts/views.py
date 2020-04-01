from django.shortcuts import render
from django.http import JsonResponse
import json

def get_posts(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            limit = int(data['limit'])
            offset = int(data['offset'])
            securities = data['securities']
            return JsonResponse([{
                    "title": "Заголовок",
                    "text": "Основной текст новости",
                    "poster": "https://bcs-express.ru/static/articlehead/5072.jpg",
                    "date": "2020-03-09'T'23:59:59",
                    "source": "БКС Экспресс",
                    "link": "https://bcs-express.ru/novosti-i-analitika/2020429427-koronovirus-b-et-po-severstali",
            }] * limit, safe=False, json_dumps_params={'ensure_ascii': False})
        except:
            return JsonResponse({
                'status': 'false',
                'message': 'Incorrect input format'
            }, status=400)
    return JsonResponse({
        'status': 'false',
        'message': 'Method not allowed. Use POST'
    }, status=405)
