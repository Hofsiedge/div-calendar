from django.shortcuts import render
from django.http import JsonResponse
from parsing import search

def search_web(request):
    if request.method == 'GET':
        try:
            if not {'q', 'limit', 'type', 'market'} <= request.GET.keys():
                raise KeyError("Missing arguments")

            try:
                limit = int(request.GET['limit'])
            except ValueError:
                raise TypeError("Incorrect argument format")
            q = request.GET['q']
            _type = request.GET['type']
            market = request.GET['market']

            if type(limit) != int or limit < 1 \
            or type(q) != str or _type not in {'stock', 'bond'} \
            or market not in {'russian', 'foreign', 'all'}:
                raise TypeError("Incorrect argument format")

            result = search(q, _type, 0, limit, market)
            return JsonResponse(result, safe=False, json_dumps_params={'ensure_ascii': False})

            """
            return JsonResponse([{
                "ticker": "SBER",
                "name": "Сбербанк ао",
                "type": "stock",
                "logo": "https://s3-symbol-logo.tradingview.com/sberbank--big.svg",
                "yield": 13.53,
                "income": 537.3,
                "exchange": "ММВБ",
            }] * limit, safe=False, json_dumps_params={'ensure_ascii': False})
            """

        except (TypeError, KeyError) as e:
            return JsonResponse(
                {'status': 'false', 'message': str(e)},
                status=400)

    return JsonResponse(
        {'status': 'false', 'message': 'Method not allowed. Use GET'},
        status=405)
