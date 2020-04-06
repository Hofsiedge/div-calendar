from django.http import JsonResponse
from parsing import get_rate

# TODO: add caching
def usd_rub_rate(request):
    if request.method == 'GET':
        try:
            result = get_rate()
            return JsonResponse(result, safe=True, json_dumps_params={'ensure_ascii': False})

        except (TypeError, KeyError) as e:
            return JsonResponse(
                {'status': 'false', 'message': str(e)},
                status=400)

    return JsonResponse(
        {'status': 'false', 'message': 'Method not allowed. Use GET'},
        status=405)
