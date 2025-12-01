from smartfridge_backend import create_app

# Gunicorn looks for `app` as the callable.
app = create_app()
