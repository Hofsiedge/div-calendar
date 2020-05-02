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
