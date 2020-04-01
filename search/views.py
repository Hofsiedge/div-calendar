from django.shortcuts import render
from django.http import JsonResponse
from parsing import search

def search_web(request):
    limit = int(request.GET.get('limit', 50))
    # result = search(request.GET.get('q', ''), int(request.GET.get('limit', 50)))
    # return JsonResponse(result, safe=False, json_dumps_params={'ensure_ascii': False})
    return JsonResponse([{
        "ticket": "SBER",
        "name": "Сбербанк ао",
        "type": "stock",
        "logo": "https://s3-symbol-logo.tradingview.com/sberbank--big.svg",
        "yield": 13.53,
        "income": 537.3,
        "exchange": "ММВБ",
    }] * limit, safe=False, json_dumps_params={'ensure_ascii': False})
