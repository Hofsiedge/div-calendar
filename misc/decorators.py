import json
from functools import wraps
from django import db

def cleanup_db_connections(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            r_val = func(*args, **kwargs)
        except db.OperationalError as e:
            db.close_old_connections()
            r_val = func(*args, **kwargs)
        finally:
            db.close_old_connections()

        return r_val

    return wrapper


def log_exceptions(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            request = args[0]
            print(f'Request failed: {request}')
            if request.method == 'POST':
                data = json.loads(request.body)
                print('-' * 80)
                print('JSON:')
                for key, value in data.items():
                    print(f'{key:>15}: {value}')
                print('-' * 80)
            raise e
        return result

    return wrapper
