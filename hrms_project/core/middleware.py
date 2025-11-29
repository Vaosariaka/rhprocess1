import threading

_thread_locals = threading.local()


def get_current_user():
    return getattr(_thread_locals, 'user', None)


def set_current_user(user):
    _thread_locals.user = user


class CurrentUserMiddleware:
    """Middleware that stores request.user in threadlocal for use in signals.

    Add 'core.middleware.CurrentUserMiddleware' to MIDDLEWARE (near the top).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            _thread_locals.user = getattr(request, 'user', None)
        except Exception:
            _thread_locals.user = None
        response = self.get_response(request)
        try:
            _thread_locals.user = None
        except Exception:
            pass
        return response
