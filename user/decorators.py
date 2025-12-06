from rest_framework_simplejwt.tokens import AccessToken
from django.shortcuts import redirect

def jwt_and_session_required(view_func):
    def wrapper(request, *args, **kwargs):

        # Validar sesión Django
        if not request.user.is_authenticated:
            return redirect("login_page")

        # Obtener JWT desde Cookie
        token = request.COOKIES.get("access_token")
        if not token:
            return redirect("login_page")

        try:
            AccessToken(token)
        except Exception:
            return redirect("login_page")

        return view_func(request, *args, **kwargs)

    return wrapper


