from django.shortcuts import render
from django.http import JsonResponse
import json

def get_payments(request):
    if request.method == 'POST':
        try:
            data        = json.loads(request.body)
            start_date  = data['start_date']
            end_date    = data['end_date']
            securities  = data['securities']
            return JsonResponse([{
                "date": "2020-03-09",
                "count": 10,
                "dividends": 12.3,
                "name": "НЛМК",
                "logo": "https://s3-symbol-logo.tradingview.com/sberbank--big.svg",
            }] * 20, safe=False, json_dumps_params={'ensure_ascii': False})
        except:
            return JsonResponse({
                'status': 'false',
                'message': 'Incorrect input format'
            }, status=400)
    return JsonResponse({
        'status': 'false',
        'message': 'Method not allowed. Use POST'
    }, status=405)
