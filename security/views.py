from django.shortcuts import render
from django.http import JsonResponse
from parsing import search_securities

def search_web(request):
    if request.method == 'GET':
        try:
            if not {'q', 'type'} <= request.GET.keys():
                raise KeyError("Missing arguments")

            try:
                limit = int(request.GET['limit']) if 'limit' in request.GET else None
            except ValueError:
                raise TypeError("Incorrect argument format")
            q = request.GET['q']
            _type = request.GET['type']
            market = request.GET.get('market', 'all')

            if limit is not None and (type(limit) != int or limit < 1) \
            or type(q) != str or _type not in {'stock', 'bond'} \
            or market not in {'russian', 'foreign', 'all'}:
                raise TypeError("Incorrect argument format")

            currency = request.GET.get('currency', None)
            if currency is not None and currency not in {'RUB', 'USD'}:
                raise TypeError("Incorrect currency format")
            result = search_securities(q, _type, 0, limit, market, currency)
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
