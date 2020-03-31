from django.shortcuts import render
from django.http import JsonResponse
from parsing import search

def search_web(request):
    result = search(request.GET.get('q', ''), int(request.GET.get('limit', 50)))
    return JsonResponse(result, safe=False, json_dumps_params={'ensure_ascii': False})
