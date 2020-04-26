release: python manage.py migrate && python manage.py test
web: daphne divcalendar.asgi:application  --port $PORT --bind 0.0.0.0 -v2
