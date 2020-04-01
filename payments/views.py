from django.shortcuts import render
from django.http import JsonResponse
import json
import re

date_pattern = re.compile(r'^(\d{2}-){2}\d{4}$')

def get_payments(request):
    if request.method == 'POST':
        try:
            data        = json.loads(request.body)
            if not {'start_date', 'end_date', 'securities'} <= data.keys():
                raise KeyError("Missing arguments")

            start_date  = data['start_date']
            end_date    = data['end_date']
            securities  = data['securities']
            if not date_pattern.match(start_date)\
            or not date_pattern.match(end_date)\
            or not securities or type(securities) != list:
                raise TypeError("Incorrect argument format")
            for i in securities:
                if type(i) != str:
                    raise TypeError("Incorrect argument format")

            return JsonResponse([{
                "date": "2020-03-09",
                "count": 10,
                "dividends": 12.3,
                "name": "НЛМК",
                "logo": "https://s3-symbol-logo.tradingview.com/sberbank--big.svg",
            }] * 20, safe=False, json_dumps_params={'ensure_ascii': False})

        except (TypeError, KeyError) as e:
            return JsonResponse({
                'status': 'false',
                'message': str(e),
            }, status=400)

    return JsonResponse({
        'status': 'false',
        'message': 'Method not allowed. Use POST'
    }, status=405)
