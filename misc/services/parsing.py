import requests

def get_rate():
    # TODO: replace placeholder with caching
    placeholder = {'rubToUsd': 74, 'usdToRub': 0.013}
    r = requests.get('https://tinkoff.ru/api/v1/currency_rates/')
    if r.status_code != 200 or r.json()['resultCode'] != 'OK':
        return placehoder
    data = r.json()['payload']['rates'][6]
    try:
        ru, ur = data['buy'], 1 / data['sell']
        if type(ru) != float or type(ur) != float:
            raise TypeError(f'Tinkoff API failed. {ru}, {ur}')
    except Exception as e:
        # TODO: logging
        print(e)
        return placeholder
    return {'rubToUsd': ru, 'usdToRub': ur}
