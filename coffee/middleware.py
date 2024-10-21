
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser, User

from coffee.views import session_storage


class GuestAccessMiddleware(MiddlewareMixin):
    def process_request(self, request):

        session_id = request.COOKIES.get("session_id")


        if session_id:
            user_id = session_storage.get(session_id)
            if user_id:
                request.user = User.objects.get(id=user_id)
            else:
                request.user = AnonymousUser()
        else:
            request.user = AnonymousUser()